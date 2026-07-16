"""embed_pass 통합 테스트 — 에뮬레이터 store + fake 클라이언트."""
from datetime import datetime, timezone
from newsstore.contracts.models import RawItem
from newsstore.embed.gemini import LLMError, PermanentEmbedError

NOW = datetime(2026, 7, 16, 7, 0, tzinfo=timezone.utc)


def _story(i, title):
    return RawItem(id=i, feed_id="f", source="S", url=f"https://e/{i}",
                   title=title, body="b", fetched_at=NOW)


class FakeEmbed:
    def __init__(self, script):
        self.script = dict(script)
    def embed(self, text, *, timeout=30.0):
        for key, r in self.script.items():
            if key in text:
                if isinstance(r, BaseException):
                    raise r
                return r
        return [0.5] * 768


def test_embed_pass_mixed_outcomes(store):
    from newsstore.embed.embed_pass import embed_pass
    store.upsert_items([_story("ok1", "Fed alpha"), _story("re1", "Fed beta"),
                        _story("pe1", "Fed gamma")])
    fake = FakeEmbed({"alpha": [0.1] * 768,
                      "beta": LLMError("exhausted"),
                      "gamma": PermanentEmbedError("bad", code=400)})
    s = embed_pass(store, fake)
    assert s == {"pending": 3, "embedded": 1, "permanent": 1, "retryable": 1}
    assert store.db.collection("item_vectors").document("ok1").get().exists
    items = store.db.collection("items")
    assert "embed_pending" not in items.document("ok1").get().to_dict()   # 성공 → 해제
    assert items.document("re1").get().to_dict()["embed_pending"] is True # 재시도 → 잔존
    assert "embed_pending" not in items.document("pe1").get().to_dict()   # 영구 → 처분
    assert not store.db.collection("item_vectors").document("pe1").get().exists


def test_embed_pass_respects_cap(store):
    from newsstore.embed.embed_pass import embed_pass
    store.upsert_items([_story(f"c{i}", f"Fed {i}") for i in range(5)])
    s = embed_pass(store, FakeEmbed({}), cap=3)
    assert s["pending"] == 3 and s["embedded"] == 3
    assert len(store.get_pending_embed_items(limit=10)) == 2   # 잔여분은 다음 런 몫


def test_embed_pass_empty_queue_noop(store):
    from newsstore.embed.embed_pass import embed_pass
    s = embed_pass(store, FakeEmbed({}))
    assert s == {"pending": 0, "embedded": 0, "permanent": 0, "retryable": 0}
