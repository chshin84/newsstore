from datetime import datetime, timezone, timedelta
from newsstore.contracts.models import RawItem
from newsstore.store.firestore_store import FirestoreStore

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


# --- TTL(1개월): content 컬렉션은 expire_at, feed_state는 절대 없음 ---

def test_upsert_stamps_expire_at_from_fetched_at(store):
    store.upsert_items([_item("a")])
    d = store.db.collection("items").document("a").get().to_dict()
    assert d["expire_at"] == NOW + timedelta(days=30)
    # enrich 전용 필드는 제거됐다(소비자 없음).
    assert "processed" not in d and "processed_at" not in d and "tags" not in d


def test_feed_state_has_no_expire_at(store):
    store.set_feed_state("f1", etag="e1", last_fetched=NOW)
    d = store.db.collection("feed_state").document("f1").get().to_dict()
    assert "expire_at" not in d          # 커서 유실 방지 — feed_state엔 TTL 금지


def test_save_price_roundtrip_and_ttl(store):
    store.save_price("sp500", {"close": 5000.0, "percent_change": 0.5})
    got = store.get_price("sp500")
    assert got["close"] == 5000.0 and got["percent_change"] == 0.5
    assert "expire_at" in got            # store가 호출자 무관하게 TTL 주입
    assert store.get_price("missing") == {}


# --- 팩터·펀더멘털 계약: 제네릭 컬렉션 적재(save_docs/filter_new_ids_in/save_snapshot) ---

def test_save_docs_batch_and_ttl_and_get(store):
    store.save_docs("income", [{"id": "AAPL__20250927", "symbol": "AAPL", "revenue": 391},
                               {"id": "AAPL__20240928", "symbol": "AAPL", "revenue": 383}])
    got = store.get_docs("income", field="symbol", value="AAPL")
    assert {d["revenue"] for d in got} == {391, 383}
    d = store.db.collection("income").document("AAPL__20250927").get().to_dict()
    assert "expire_at" in d and "id" not in d          # store가 TTL 주입, id는 문서키라 필드로 안 남김
    assert store.save_docs("income", []) == 0


def test_filter_new_ids_in_returns_only_unstored(store):
    store.save_docs("c1", [{"id": "x", "v": 1}])
    assert store.filter_new_ids_in("c1", ["x", "y", "z"]) == ["y", "z"]   # 저장된 x 제외, 순서 보존
    assert store.filter_new_ids_in("c1", []) == []


def test_save_docs_is_idempotent_on_same_id(store):
    store.save_docs("income", [{"id": "AAPL__20250927", "symbol": "AAPL", "revenue": 391}])
    store.save_docs("income", [{"id": "AAPL__20250927", "symbol": "AAPL", "revenue": 391}])
    assert len(store.get_docs("income", field="symbol", value="AAPL")) == 1   # 중복 문서 안 쌓임


def test_save_snapshot_overwrites_and_ttl(store):
    store.save_snapshot("profiles", "AAPL", {"sector": "Technology"})
    store.save_snapshot("profiles", "AAPL", {"sector": "Tech2"})            # 덮어쓰기
    got = store.get_snapshot("profiles", "AAPL")
    assert got["sector"] == "Tech2" and "expire_at" in got
    assert store.get_snapshot("profiles", "MSFT") == {}


# --- price_bars(5분봉 완전 스트림): 적재·dedup·조회·바 날짜 기준 TTL ---

def _bar(bid, key, dt, close):
    return {"id": bid, "key": key, "symbol": "^GSPC", "source": "fmp",
            "datetime": dt, "close": close}


def test_save_bars_and_get_bars_sorted(store):
    store.save_bars([_bar("sp500__20260710101000", "sp500", "2026-07-10 10:10:00", 102.0),
                     _bar("sp500__20260710100000", "sp500", "2026-07-10 10:00:00", 100.0)])
    got = store.get_bars("sp500")
    assert [b["close"] for b in got] == [100.0, 102.0]        # datetime 오름차순
    assert store.get_bars("other") == []


def test_save_bars_expire_at_from_bar_date(store):
    store.save_bars([_bar("sp500__20260710101000", "sp500", "2026-07-10 10:10:00", 1.0)])
    d = store.db.collection("price_bars").document("sp500__20260710101000").get().to_dict()
    # TTL = 바 날짜(2026-07-10) + 30일. 시·분은 만료에 무의미.
    assert d["expire_at"] == datetime(2026, 8, 9, tzinfo=timezone.utc)


def test_filter_new_bar_ids_returns_only_unstored(store):
    store.save_bars([_bar("k__1", "k", "2026-07-10 10:00:00", 1.0)])
    assert store.filter_new_bar_ids(["k__1", "k__2", "k__3"]) == ["k__2", "k__3"]
    assert store.filter_new_bar_ids([]) == []


def test_save_bars_is_idempotent_on_same_id(store):
    b = _bar("k__1", "k", "2026-07-10 10:00:00", 1.0)
    store.save_bars([b])
    store.save_bars([b])                 # 같은 id 재적재 — 중복 문서 안 쌓임
    assert len(store.get_bars("k")) == 1


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
