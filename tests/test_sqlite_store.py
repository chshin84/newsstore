from datetime import datetime, timezone
from newsstore.models import RawItem
from newsstore.store.sqlite_store import SqliteStore

NOW = datetime(2026, 6, 12, 7, 0, tzinfo=timezone.utc)

def _item(i):
    return RawItem(id=i, feed_id="f1", source="S", url=f"https://e/{i}",
                   title=f"t{i}", body="b", fetched_at=NOW)

def test_upsert_dedups_by_id(tmp_path):
    s = SqliteStore(tmp_path / "db.sqlite")
    assert s.upsert_items([_item("a"), _item("b")]) == 2
    assert s.upsert_items([_item("a"), _item("c")]) == 1   # only "c" is new
    assert s.count() == 3

def test_feed_state_roundtrip(tmp_path):
    s = SqliteStore(tmp_path / "db.sqlite")
    assert s.get_feed_state("f1") == {}
    s.set_feed_state("f1", etag="W/\"x\"", last_modified="Mon", last_fetched=NOW)
    st = s.get_feed_state("f1")
    assert st["etag"] == "W/\"x\"" and st["last_fetched"] == NOW
