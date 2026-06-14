from datetime import datetime, timezone
from newsstore.contracts.models import RawItem

NOW = datetime(2026, 6, 13, 7, 0, tzinfo=timezone.utc)


def _item(i="a"):
    return RawItem(id=i, feed_id="f1", source="S", url=f"https://e/{i}",
                   title="t", body="b", fetched_at=NOW)


def test_save_enrichment(store):
    store.upsert_items([_item("a")])
    store.save_enrichment("a", kind="story", tags=["NVDA", "rates"],
                          embedding=[0.1, 0.2], story_id="st1")
    d = store.db.collection("items").document("a").get().to_dict()
    assert d["kind"] == "story"
    assert d["tags"] == ["NVDA", "rates"]
    assert d["embedding"] == [0.1, 0.2]
    assert d["story_id"] == "st1"


def test_save_enrichment_none_embedding(store):
    store.upsert_items([_item("b")])
    store.save_enrichment("b", kind="digest", tags=[], embedding=None, story_id=None)
    d = store.db.collection("items").document("b").get().to_dict()
    assert d["kind"] == "digest"
    assert d["embedding"] is None
    assert d["story_id"] is None


def test_save_enrichment_preserves_fields(store):
    store.upsert_items([_item("a")])
    store.save_enrichment("a", kind="spam", tags=[], embedding=None, story_id=None)
    d = store.db.collection("items").document("a").get().to_dict()
    assert d["kind"] == "spam" and d["title"] == "t"   # 기존 필드 보존
