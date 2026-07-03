from datetime import datetime, timezone, timedelta
from newsstore.contracts.models import RawItem
from newsstore.enrich.embedder import EMBED_DIM
from newsstore.enrich.processor import process_once

NOW = datetime(2026, 6, 14, 12, 0, tzinfo=timezone.utc)
TAX = {"entities": ["Fed"], "topics": ["rates"]}


def _item(i, title, body="default substantive article body, enough chars to embed"):
    return RawItem(id=i, feed_id="f", source="S", url=f"https://e/{i}",
                   title=title, body=body, fetched_at=NOW)


def _unit(idx):
    v = [0.0] * EMBED_DIM
    v[idx] = 1.0
    return v


def _rows(store):
    return {d.id: d.to_dict() for d in store.db.collection("items").stream()}


class _FakeClient:
    """generate_json: 모든 항목에 동일 태그. embed: 제목 키워드로 벡터 매핑(클러스터 제어)."""
    def __init__(self, embed_map):
        self.embed_map = embed_map
    def generate_json(self, prompt, *, timeout=30.0):
        return {"results": [{"tickers": [], "entities": ["Fed"], "topics": ["rates"]}
                            for _ in range(10)]}
    def embed(self, text, *, timeout=30.0):
        for key, vec in self.embed_map.items():
            if key in text:
                return list(vec)
        return [0.0] * EMBED_DIM
    def complete(self, prompt, *, timeout=30.0):
        return "DIFFERENT"        # gray-band 기본: 미합류(직교 벡터 테스트는 호출 안 됨)


def test_run_cluster_rereads_open_stories_each_batch(store, monkeypatch):
    # 회귀 가드: open_stories를 실행 시작 시 1회만 읽으면 앞 배치 합류로 커진
    # centroid_sum을 뒤 배치가 못 봐(다배치 백필) 중복 스토리가 생긴다.
    # processor 주석의 '다음 배치 재읽기' 계약이 실제 배선에서 지켜지는지 고정한다.
    from newsstore.entrypoints import run_enrich as re_mod
    from newsstore.entrypoints.run_enrich import _run_cluster

    calls = {"n": 0}
    orig = store.get_open_stories

    def counting(cutoff):
        calls["n"] += 1
        return orig(cutoff)

    monkeypatch.setattr(store, "get_open_stories", counting)
    monkeypatch.setattr(re_mod, "MAX_BATCHES", 10)
    store.upsert_items([_item("a", "Fed raises rates"), _item("b", "Oil surges today")])
    _run_cluster(store, _FakeClient({"Fed raises": _unit(0), "Oil surges": _unit(1)}),
                 TAX, noncluster=frozenset(), batch=1, concurrency=1)
    # 배치당 1회 재읽기(2 아이템 배치 + 종료 판정 배치) — 1회 고정 공유였다면 n==1
    assert calls["n"] >= 2


def test_spam_and_digest_excluded_from_embedding(store):
    store.upsert_items([
        _item("a", "Fed raises rates"),
        _item("b", "ROSEN LAW reminds investors of class action deadline"),
        _item("c", "Markets Wrap, More"),
    ])
    process_once(store, _FakeClient({"Fed raises": _unit(0)}), TAX, now=NOW)

    rows = _rows(store)
    assert rows["a"]["kind"] == "story" and rows["a"]["embedding"] is not None
    assert rows["b"]["kind"] == "spam" and rows["b"]["embedding"] is None
    assert rows["c"]["kind"] == "digest" and rows["c"]["embedding"] is None
    assert all(rows[i]["processed"] is True for i in ("a", "b", "c"))   # 비파괴
    assert rows["b"]["story_id"] is None and rows["c"]["story_id"] is None


def test_similar_stories_cluster_distinct_stay_separate(store):
    store.upsert_items([
        _item("a", "Fed raises rates sharply"),
        _item("b", "Fed raises rates again"),     # a와 동일 벡터 → 합류
        _item("c", "Oil prices jump"),            # 직교 벡터 → 새 스토리
    ])
    process_once(store, _FakeClient({"Fed raises": _unit(0), "Oil prices": _unit(1)}),
                 TAX, now=NOW)

    sid = {i: r["story_id"] for i, r in _rows(store).items()}
    assert sid["a"] == sid["b"]          # 클러스터 합류
    assert sid["c"] != sid["a"]          # 별도 스토리
    stories = list(store.get_open_stories(cutoff=NOW - timedelta(hours=1)))
    assert len(stories) == 2


def test_returns_stats(store):
    store.upsert_items([_item("a", "Fed raises rates")])
    stats = process_once(store, _FakeClient({"Fed raises": _unit(0)}), TAX, now=NOW)
    assert stats["processed"] == 1
    assert stats["stories_created"] == 1
    assert stats["stories_joined"] == 0


def test_empty_queue_is_noop(store):
    stats = process_once(store, _FakeClient({}), TAX, now=NOW)
    assert stats["processed"] == 0


def test_cluster_pass_no_tagging(store):
    # tag=False: 태깅 생략, 클러스터만(어댑터 기본 경로 — index 주입 제거)
    store.upsert_items([_item("a", "Fed raises rates sharply today"),
                        _item("b", "Fed raises rates again right now")])
    process_once(store, _FakeClient({"Fed raises": _unit(0)}), TAX, now=NOW, tag=False)
    rows = _rows(store)
    assert rows["a"]["tags"] == []                         # 태깅 생략
    assert rows["a"]["embedding"] is not None
    assert rows["a"]["story_id"] == rows["b"]["story_id"]  # 합류


def test_noncluster_source_tagged_not_clustered(store):
    # TruthSocial 등 비내러티브 소스는 텍스트가 충분해도 클러스터 제외(보일러플레이트 오병합 방지).
    a = _item("a", "Fed raises rates sharply today")
    ts = RawItem(id="ts", feed_id="f", source="TruthSocial",
                 url="https://e/ts", title="RT @realDonaldTrump",
                 body="a retweet with enough characters to pass the thin guard easily",
                 fetched_at=NOW)
    store.upsert_items([a, ts])
    process_once(store, _FakeClient({"Fed raises": _unit(0)}), TAX, now=NOW,
                 noncluster_sources={"TruthSocial"})
    rows = _rows(store)
    assert rows["ts"]["kind"] == "story"
    assert rows["ts"]["embedding"] is None and rows["ts"]["story_id"] is None
    assert rows["a"]["embedding"] is not None


def test_same_batch_second_article_joins_first(store):
    # 같은 배치에서 첫 기사가 연 스토리에 둘째가 합류(배치 내 open_stories 갱신 불변식)
    store.upsert_items([_item("a", "Fed raises rates sharply today"),
                        _item("b", "Fed raises rates again right now")])   # 동일 벡터
    process_once(store, _FakeClient({"Fed raises": _unit(0)}), TAX, now=NOW)
    sid = {i: r["story_id"] for i, r in _rows(store).items()}
    assert sid["a"] == sid["b"]            # 한 배치 안에서 합류(중복 스토리 X)


def test_gray_band_same_merges(store):
    # gray-band(lo<cos<hi)에서 LLM=SAME → 합류. 벡터를 cos≈0.64로 구성.
    class _Gray(_FakeClient):
        def complete(self, prompt, *, timeout=30.0):
            return "SAME"
    def _vec(a, b):
        v = [0.0] * EMBED_DIM; v[0] = a; v[1] = b; return v
    store.upsert_items([_item("a", "Alpha event one"), _item("b", "Beta event two")])
    process_once(store, _Gray({"Alpha": _vec(1.0, 0.0), "Beta": _vec(0.83, 1.0)}),
                 TAX, now=NOW)
    sid = {i: r["story_id"] for i, r in _rows(store).items()}
    assert sid["a"] == sid["b"]            # gray-band SAME → 합류


def test_thin_story_item_not_embedded_or_clustered(store):
    # 텍스트가 너무 얇은 story 아이템은 임베딩/클러스터에서 제외(노이즈 방지). kind=story·processed지만 standalone.
    store.upsert_items([_item("a", "Fed raises rates sharply today"), _item("t", "Hi", body="")])
    process_once(store, _FakeClient({"Fed raises": _unit(0)}), TAX, now=NOW)
    rows = _rows(store)
    assert rows["a"]["kind"] == "story" and rows["a"]["embedding"] is not None
    assert rows["t"]["kind"] == "story"
    assert rows["t"]["embedding"] is None and rows["t"]["story_id"] is None
    assert rows["t"]["processed"] is True


def test_env_hours_default_and_override(monkeypatch):
    # #9: 스토리 시간창 env 오버라이드 — 미설정=기본, 설정=그 값, 잘못된 값=FAIL-LOUD
    from newsstore.enrich.processor import env_hours
    monkeypatch.delenv("NEWSSTORE_OPEN_WINDOW_HOURS", raising=False)
    assert env_hours("NEWSSTORE_OPEN_WINDOW_HOURS", 48) == timedelta(hours=48)
    monkeypatch.setenv("NEWSSTORE_OPEN_WINDOW_HOURS", "12")
    assert env_hours("NEWSSTORE_OPEN_WINDOW_HOURS", 48) == timedelta(hours=12)
    monkeypatch.setenv("NEWSSTORE_OPEN_WINDOW_HOURS", "not-a-number")
    import pytest
    with pytest.raises(ValueError):
        env_hours("NEWSSTORE_OPEN_WINDOW_HOURS", 48)
