from datetime import datetime, timezone
from mockfirestore import MockFirestore
from newsstore.models import RawItem
from newsstore.store.firestore_store import FirestoreStore

NOW = datetime(2026, 6, 12, 7, 0, tzinfo=timezone.utc)

def _item(i):
    return RawItem(id=i, feed_id="f1", source="S", url=f"https://e/{i}",
                   title=f"t{i}", body="b", fetched_at=NOW)

def _store():
    return FirestoreStore(MockFirestore())

def test_upsert_dedups_by_id():
    s = _store()
    assert s.upsert_items([_item("a"), _item("b")]) == 2
    assert s.upsert_items([_item("a"), _item("c")]) == 1   # only "c" is new
    assert s.count() == 3

def test_context_manager_yields_store():
    with _store() as s:
        assert s.upsert_items([_item("a")]) == 1

def test_feed_state_roundtrip():
    s = _store()
    assert s.get_feed_state("f1") == {}
    s.set_feed_state("f1", etag='W/"x"', last_modified="Mon", last_fetched=NOW)
    st = s.get_feed_state("f1")
    assert st["etag"] == 'W/"x"' and st["last_fetched"] == NOW

def test_set_feed_state_merges_existing_fields():
    s = _store()
    s.set_feed_state("f1", etag="e1", last_fetched=NOW)
    s.set_feed_state("f1", last_modified="Tue")   # must not wipe etag
    st = s.get_feed_state("f1")
    assert st["etag"] == "e1" and st["last_modified"] == "Tue"
