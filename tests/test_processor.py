from datetime import datetime, timezone, timedelta
from newsstore.contracts.models import RawItem
from newsstore.store.sqlite_store import SqliteStore
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


def _store(tmp_path):
    return SqliteStore(tmp_path / "db.sqlite")


def test_spam_and_digest_excluded_from_embedding(tmp_path):
    s = _store(tmp_path)
    s.upsert_items([
        _item("a", "Fed raises rates"),
        _item("b", "ROSEN LAW reminds investors of class action deadline"),
        _item("c", "Markets Wrap, More"),
    ])
    client = _FakeClient({"Fed raises": _unit(0)})
    process_once(s, client, TAX, now=NOW)

    rows = {r["id"]: r for r in s.conn.execute(
        "SELECT id,kind,embedding,story_id,processed FROM raw_items")}
    assert rows["a"]["kind"] == "story" and rows["a"]["embedding"] is not None
    assert rows["b"]["kind"] == "spam" and rows["b"]["embedding"] is None
    assert rows["c"]["kind"] == "digest" and rows["c"]["embedding"] is None
    # 전부 processed 처리(비파괴 — 저장은 보존, kind만 분류)
    assert all(rows[i]["processed"] == 1 for i in ("a", "b", "c"))
    # spam/digest는 스토리에 안 들어감
    assert rows["b"]["story_id"] is None and rows["c"]["story_id"] is None


def test_similar_stories_cluster_distinct_stay_separate(tmp_path):
    s = _store(tmp_path)
    s.upsert_items([
        _item("a", "Fed raises rates sharply"),
        _item("b", "Fed raises rates again"),     # a와 동일 벡터 → 합류
        _item("c", "Oil prices jump"),            # 직교 벡터 → 새 스토리
    ])
    client = _FakeClient({"Fed raises": _unit(0), "Oil prices": _unit(1)})
    process_once(s, client, TAX, now=NOW)

    sid = {r["id"]: r["story_id"] for r in s.conn.execute(
        "SELECT id,story_id FROM raw_items")}
    assert sid["a"] == sid["b"]          # 클러스터 합류
    assert sid["c"] != sid["a"]          # 별도 스토리
    # 스토리 2개, 'a' 스토리는 멤버 2
    stories = list(s.get_open_stories(cutoff=NOW - timedelta(hours=1)))
    assert len(stories) == 2


def test_returns_stats(tmp_path):
    s = _store(tmp_path)
    s.upsert_items([_item("a", "Fed raises rates")])
    stats = process_once(s, _FakeClient({"Fed raises": _unit(0)}), TAX, now=NOW)
    assert stats["processed"] == 1
    assert stats["stories_created"] == 1
    assert stats["stories_joined"] == 0


def test_empty_queue_is_noop(tmp_path):
    s = _store(tmp_path)
    stats = process_once(s, _FakeClient({}), TAX, now=NOW)
    assert stats["processed"] == 0


def test_cluster_pass_cache_no_tagging(tmp_path):
    # tag=False + in-memory candidates: 태깅 생략, Firestore 재조회 없이 캐시로 클러스터
    import json
    s = _store(tmp_path)
    s.upsert_items([_item("a", "Fed raises rates sharply today"),
                    _item("b", "Fed raises rates again right now")])
    cache: list = []
    process_once(s, _FakeClient({"Fed raises": _unit(0)}), TAX, now=NOW,
                 tag=False, candidates=cache)
    rows = {r["id"]: r for r in s.conn.execute(
        "SELECT id,tags,story_id,embedding FROM raw_items")}
    assert json.loads(rows["a"]["tags"]) == []           # 태깅 생략
    assert rows["a"]["embedding"] is not None
    assert rows["a"]["story_id"] == rows["b"]["story_id"]  # 캐시로 합류
    assert len(cache) == 1 and cache[0]["count"] == 2     # 캐시 in-place 갱신


def test_noncluster_source_tagged_not_clustered(tmp_path):
    # TruthSocial 등 비내러티브 소스는 텍스트가 충분해도 클러스터 제외(보일러플레이트 오병합 방지).
    s = _store(tmp_path)
    a = _item("a", "Fed raises rates sharply today")
    ts = RawItem(id="ts", feed_id="f", source="TruthSocial",
                 url="https://e/ts", title="RT @realDonaldTrump",
                 body="a retweet with enough characters to pass the thin guard easily",
                 fetched_at=NOW)
    s.upsert_items([a, ts])
    process_once(s, _FakeClient({"Fed raises": _unit(0)}), TAX, now=NOW,
                 noncluster_sources={"TruthSocial"})
    rows = {r["id"]: r for r in s.conn.execute(
        "SELECT id,kind,embedding,story_id FROM raw_items")}
    assert rows["ts"]["kind"] == "story"
    assert rows["ts"]["embedding"] is None and rows["ts"]["story_id"] is None
    assert rows["a"]["embedding"] is not None


def test_thin_story_item_not_embedded_or_clustered(tmp_path):
    # 텍스트가 너무 얇은 story 아이템은 임베딩/클러스터에서 제외(노이즈 클러스터 방지).
    # 여전히 kind=story·processed지만 embedding/story_id 없음(=standalone).
    s = _store(tmp_path)
    s.upsert_items([_item("a", "Fed raises rates sharply today"), _item("t", "Hi", body="")])
    process_once(s, _FakeClient({"Fed raises": _unit(0)}), TAX, now=NOW)
    rows = {r["id"]: r for r in s.conn.execute(
        "SELECT id,kind,embedding,story_id,processed FROM raw_items")}
    assert rows["a"]["kind"] == "story" and rows["a"]["embedding"] is not None
    assert rows["t"]["kind"] == "story"
    assert rows["t"]["embedding"] is None and rows["t"]["story_id"] is None
    assert rows["t"]["processed"] == 1
