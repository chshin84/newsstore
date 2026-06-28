from datetime import datetime, timezone
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


def test_get_unprocessed_and_mark_processed(store):
    store.upsert_items([_item("a"), _item("b"), _item("c")])
    assert {i.id for i in store.get_unprocessed()} == {"a", "b", "c"}
    assert len(store.get_unprocessed(limit=2)) == 2
    one = store.get_unprocessed(limit=1)[0]                 # round-trips to a RawItem
    assert one.fetched_at == NOW and one.feed_id == "f1"
    assert store.mark_processed(["a", "b"], processed_at=NOW) == 2
    assert {i.id for i in store.get_unprocessed()} == {"c"}
    assert store.mark_processed([]) == 0


def test_upsert_preserves_processed_on_resee(store):
    store.upsert_items([_item("a")])
    assert store.mark_processed(["a"], processed_at=NOW) == 1
    assert store.upsert_items([_item("a")]) == 0            # re-seen, not re-written
    assert store.get_unprocessed() == []                    # still processed


def test_filter_new_ids_returns_only_unstored(store):
    from datetime import datetime, timezone
    from newsstore.contracts.models import RawItem
    now = datetime(2026, 6, 12, 7, 0, tzinfo=timezone.utc)
    stored = RawItem(id="aaa", feed_id="f", source="S", url="https://e/a", title="t", fetched_at=now)
    store.upsert_items([stored])
    out = store.filter_new_ids(["aaa", "bbb", "ccc"])
    assert out == ["bbb", "ccc"]          # 저장된 aaa 제외, 순서 보존
    assert store.filter_new_ids([]) == []
