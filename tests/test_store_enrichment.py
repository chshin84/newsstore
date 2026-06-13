import json
from datetime import datetime, timezone
from mockfirestore import MockFirestore
from newsstore.models import RawItem
from newsstore.store.sqlite_store import SqliteStore
from newsstore.store.firestore_store import FirestoreStore

NOW = datetime(2026, 6, 13, 7, 0, tzinfo=timezone.utc)

def _item(i="a"):
    return RawItem(id=i, feed_id="f1", source="S", url=f"https://e/{i}", title="t", body="b", fetched_at=NOW)

def test_sqlite_save_enrichment(tmp_path):
    s = SqliteStore(tmp_path / "db.sqlite")
    s.upsert_items([_item("a")])
    s.save_enrichment("a", kind="story", tags=["NVDA", "rates"], embedding=[0.1, 0.2], story_id="st1")
    row = s.conn.execute(
        "SELECT kind,tags,embedding,story_id FROM raw_items WHERE id='a'").fetchone()
    assert row["kind"] == "story"
    assert json.loads(row["tags"]) == ["NVDA", "rates"]
    assert json.loads(row["embedding"]) == [0.1, 0.2]
    assert row["story_id"] == "st1"

def test_sqlite_save_enrichment_none_embedding(tmp_path):
    s = SqliteStore(tmp_path / "db.sqlite")
    s.upsert_items([_item("b")])
    s.save_enrichment("b", kind="digest", tags=[], embedding=None, story_id=None)
    row = s.conn.execute("SELECT kind,embedding,story_id FROM raw_items WHERE id='b'").fetchone()
    assert row["kind"] == "digest"
    assert row["embedding"] is None      # None → SQL NULL
    assert row["story_id"] is None

def test_firestore_save_enrichment_preserves_fields():
    s = FirestoreStore(MockFirestore())
    s.upsert_items([_item("a")])
    s.save_enrichment("a", kind="spam", tags=[], embedding=None, story_id=None)
    d = s.db.collection("items").document("a").get().to_dict()
    assert d["kind"] == "spam" and d["title"] == "t"
