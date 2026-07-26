import threading
from datetime import datetime, timezone, timedelta
from newsstore.contracts.models import RawItem
from newsstore.store.firestore_store import FirestoreStore, _to_doc
from newsstore.collect.feeds import make_id

NOW = datetime(2026, 6, 12, 7, 0, tzinfo=timezone.utc)


def _item(i):
    return RawItem(id=i, feed_id="f1", source="S", url=f"https://e/{i}",
                   title=f"t{i}", body="b", fetched_at=NOW)


def test_upsert_dedups_by_id(store):
    assert store.upsert_items([_item("a"), _item("b")]) == 2
    assert store.upsert_items([_item("a"), _item("c")]) == 1   # only "c" is new
    assert store.count() == 3


def test_context_manager_yields_store(store):
    with store as s:
        assert s.upsert_items([_item("a")]) == 1


def test_feed_state_roundtrip(store):
    assert store.get_feed_state("f1") == {}
    store.set_feed_state("f1", etag='W/"x"', last_modified="Mon", last_fetched=NOW)
    st = store.get_feed_state("f1")
    assert st["etag"] == 'W/"x"' and st["last_fetched"] == NOW


def test_set_feed_state_merges_existing_fields(store):
    store.set_feed_state("f1", etag="e1", last_fetched=NOW)
    store.set_feed_state("f1", last_modified="Tue")   # must not wipe etag
    st = store.get_feed_state("f1")
    assert st["etag"] == "e1" and st["last_modified"] == "Tue"


def test_filter_new_ids_returns_only_unstored(store):
    stored = RawItem(id="aaa", feed_id="f", source="S", url="https://e/a", title="t", fetched_at=NOW)
    store.upsert_items([stored])
    out = store.filter_new_ids(["aaa", "bbb", "ccc"])
    assert out == ["bbb", "ccc"]          # 저장된 aaa 제외, 순서 보존
    assert store.filter_new_ids([]) == []


# --- kind triage(§3 규칙 필터 보존): 수집 시점에 classify_kind가 stamp되는가 ---

def test_upsert_stamps_kind_at_collect_time(store):
    junk = RawItem(id="j", feed_id="f", source="S", url="https://e/j",
                   title="Rosen Law reminds investors of class action deadline",
                   body="b", fetched_at=NOW)
    good = RawItem(id="g", feed_id="f", source="S", url="https://e/g",
                   title="Fed holds rates steady", body="b", fetched_at=NOW)
    store.upsert_items([junk, good])
    dj = store.db.collection("items").document("j").get().to_dict()
    dg = store.db.collection("items").document("g").get().to_dict()
    assert dj["kind"] == "spam"          # 스팸 신호(집단소송 PR) → 숨김 kind
    assert dg["kind"] == "story"


# --- TTL(60일): content 컬렉션은 expire_at, feed_state는 절대 없음 ---

def test_upsert_stamps_expire_at_from_fetched_at(store):
    store.upsert_items([_item("a")])
    d = store.db.collection("items").document("a").get().to_dict()
    assert d["expire_at"] == NOW + timedelta(days=60)
    # enrich 전용 필드는 제거됐다(소비자 없음).
    assert "processed" not in d and "processed_at" not in d and "tags" not in d


def test_feed_state_has_no_expire_at(store):
    store.set_feed_state("f1", etag="e1", last_fetched=NOW)
    d = store.db.collection("feed_state").document("f1").get().to_dict()
    assert "expire_at" not in d          # 커서 유실 방지 — feed_state엔 TTL 금지


# --- 임베딩 대기 플래그(spec 2026-07-16): story에만 embed_pending이 박히는가 ---

def test_to_doc_stamps_embed_pending_for_story_only(store):
    junk = RawItem(id="j2", feed_id="f", source="S", url="https://e/j2",
                   title="Rosen Law reminds investors of class action deadline",
                   body="b", fetched_at=NOW)
    good = RawItem(id="g2", feed_id="f", source="S", url="https://e/g2",
                   title="Fed holds rates steady", body="b", fetched_at=NOW)
    store.upsert_items([junk, good])
    dj = store.db.collection("items").document("j2").get().to_dict()
    dg = store.db.collection("items").document("g2").get().to_dict()
    assert dg["embed_pending"] is True           # story → 대기 플래그
    assert "embed_pending" not in dj             # 비-story → 필드 자체가 없어야 함


# --- 임베딩 벡터 표면(spec 2026-07-16): pending 큐 조회 + 벡터 저장 + 플래그 처분 ---

def _story(i):
    return RawItem(id=i, feed_id="f", source="S", url=f"https://e/{i}",
                   title=f"Fed news {i}", body="b", fetched_at=NOW)


def test_get_pending_embed_items_returns_queue_with_limit(store):
    store.upsert_items([_story("p1"), _story("p2"), _story("p3")])
    got = store.get_pending_embed_items(limit=2)
    assert len(got) == 2
    one = got[0]
    assert set(one) == {"item_id", "title", "body", "expire_at"}
    assert one["expire_at"] is not None          # TTL 미러링 원천


def test_save_vectors_writes_vector_and_clears_flag(store):
    store.upsert_items([_story("v1")])
    [p] = store.get_pending_embed_items(limit=10)
    n = store.save_vectors([{"item_id": "v1", "vector": [0.1] * 768,
                             "expire_at": p["expire_at"]}])
    assert n == 1
    vec = store.db.collection("item_vectors").document("v1").get().to_dict()
    assert len(vec["vector"]) == 768
    assert vec["embed_model"] == "gemini-embedding-001"   # store가 SSOT에서 주입
    # task_type도 벡터의 좌표계를 가르는 계약이라 함께 기록한다 — 모델만으로는
    # 타입이 바뀐 낡은 벡터를 구분할 수 없어 재임베딩 대상을 못 고른다.
    from newsstore.contracts.embedding import EMBED_TASK_TYPE
    assert vec["embed_task_type"] == EMBED_TASK_TYPE
    assert vec["embedded_at"] is not None
    assert vec["expire_at"] == p["expire_at"]             # 원본 TTL 미러링
    item = store.db.collection("items").document("v1").get().to_dict()
    assert "embed_pending" not in item                    # 같은 batch로 플래그 해제
    assert store.get_pending_embed_items(limit=10) == []


def test_save_vectors_no_duplicate_writes_across_chunk_boundary(store):
    """청크 경계(50건)를 넘는 배치에서 겹쳐 쓰기 회귀 방지. range(0,len,50)에 슬라이스가
    [i:i+250]로 남아있으면(과거 버그) 같은 항목이 여러 청크에 겹쳐 들어가 n이 entries 수보다
    커진다 — 실제 Firestore 쓰기도 중복 커밋돼 비용·지연이 배로 든다."""
    n_entries = 60
    items = [_story(f"c{i}") for i in range(n_entries)]
    store.upsert_items(items)
    pending = store.get_pending_embed_items(limit=100)
    assert len(pending) == n_entries
    entries = [{"item_id": p["item_id"], "vector": [0.1] * 768, "expire_at": p["expire_at"]}
               for p in pending]
    n = store.save_vectors(entries)
    assert n == n_entries


def test_save_vectors_skips_missing_item_and_keeps_rest(store):
    """만료 경합 격리: 원본이 사라진 항목이 나머지 벡터 저장을 막지 않는다."""
    store.upsert_items([_story("m1"), _story("m2")])
    exp = store.get_pending_embed_items(limit=10)[0]["expire_at"]
    store.db.collection("items").document("m1").delete()   # TTL 삭제 시뮬레이션
    n = store.save_vectors([
        {"item_id": "m1", "vector": [0.1] * 768, "expire_at": exp},
        {"item_id": "m2", "vector": [0.2] * 768, "expire_at": exp},
    ])
    assert n == 1                                          # m1은 스킵, m2는 저장
    assert not store.db.collection("item_vectors").document("m1").get().exists
    assert store.db.collection("item_vectors").document("m2").get().exists


def test_save_vectors_is_idempotent(store):
    store.upsert_items([_story("i1")])
    exp = store.get_pending_embed_items(limit=10)[0]["expire_at"]
    entry = {"item_id": "i1", "vector": [0.3] * 768, "expire_at": exp}
    store.save_vectors([entry])
    store.save_vectors([entry])                            # 재실행(플래그 이미 없음)
    assert store.db.collection("item_vectors").document("i1").get().exists


def test_clear_embed_pending_removes_flag_without_vector(store):
    store.upsert_items([_story("c1x")])
    store.clear_embed_pending(["c1x", "ghost-없는-id"])     # 없는 id도 조용히 스킵
    item = store.db.collection("items").document("c1x").get().to_dict()
    assert "embed_pending" not in item
    assert not store.db.collection("item_vectors").document("c1x").get().exists


# --- symbol 필드(FMP 티커 태깅 보존) ---

def test_rawitem_symbol_defaults_empty():
    it = RawItem(id="a", feed_id="fmp:stock-latest", source="X",
                 url="http://x/1", title="t", fetched_at=datetime.now(timezone.utc))
    assert it.symbol == ""


def test_to_doc_persists_symbol():
    it = RawItem(id="a", feed_id="fmp:stock-latest", source="X", symbol="AAPL",
                 url="http://x/1", title="t", fetched_at=datetime.now(timezone.utc))
    assert _to_doc(it)["symbol"] == "AAPL"


# --- upsert_items_batched(청크 배치 upsert, 비용 통제) ---

def test_upsert_items_batched_dedups_and_is_idempotent(store):
    now = datetime.now(timezone.utc)
    def mk(u): return RawItem(id=make_id(u), feed_id="fmp:stock-latest", source="X",
                              url=u, title="t", fetched_at=now)
    items = [mk("http://x/1"), mk("http://x/2"), mk("http://x/1")]   # 배치 내 중복 1건
    assert store.upsert_items_batched(items) == 2      # 고유 2건만
    assert store.upsert_items_batched(items) == 0      # 멱등 재-pull(불변식: 재저장 0)


def test_concurrent_threads_share_one_store_safely(store):
    """run_collect_all 설계의 핵심 전제 검증: 3개 스레드가 같은 FirestoreStore(같은
    firestore.Client)로 서로 다른 컬렉션에 동시에 upsert_items/set_feed_state를 해도
    예외 없이 전부 반영되는지. 실패하면 스펙의 '대안'(스레드별 독립 클라이언트)으로 전환한다."""
    errors = []

    def write_items(prefix, n):
        try:
            items = [_story(f"{prefix}{i}") for i in range(n)]
            store.upsert_items(items)
        except Exception as e:
            errors.append(e)

    def write_feed_state(feed_id, n):
        try:
            for i in range(n):
                store.set_feed_state(feed_id, last_fetched=NOW, consecutive_failures=i)
        except Exception as e:
            errors.append(e)

    threads = [
        threading.Thread(target=write_items, args=("ca", 10)),
        threading.Thread(target=write_items, args=("cb", 10)),
        threading.Thread(target=write_feed_state, args=("naver:x", 10)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert store.count() == 20
    assert store.get_feed_state("naver:x")["consecutive_failures"] == 9
