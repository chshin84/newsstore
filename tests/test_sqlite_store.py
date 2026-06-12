import sqlite3
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

def test_get_unprocessed_and_mark_processed(tmp_path):
    s = SqliteStore(tmp_path / "db.sqlite")
    s.upsert_items([_item("a"), _item("b"), _item("c")])
    # everything starts unprocessed
    assert {i.id for i in s.get_unprocessed()} == {"a", "b", "c"}
    # limit is honored
    assert len(s.get_unprocessed(limit=2)) == 2
    # round-trip reconstructs a usable RawItem
    one = s.get_unprocessed(limit=1)[0]
    assert one.fetched_at == NOW and one.feed_id == "f1"
    # mark two; they drop out of the unprocessed queue
    assert s.mark_processed(["a", "b"], processed_at=NOW) == 2
    assert {i.id for i in s.get_unprocessed()} == {"c"}
    # re-marking is idempotent (already processed -> 0 rows changed)
    assert s.mark_processed(["a", "b"]) == 0
    assert s.mark_processed([]) == 0

def test_migration_upgrades_legacy_db(tmp_path):
    # a DB created before the processed/ user_version columns existed
    p = tmp_path / "legacy.sqlite"
    raw = sqlite3.connect(str(p))
    raw.executescript(
        "CREATE TABLE raw_items (id TEXT PRIMARY KEY, feed_id TEXT, source TEXT,"
        " asset_hint TEXT, language TEXT, url TEXT, title TEXT, body TEXT,"
        " published_at TEXT, fetched_at TEXT);")
    raw.execute("INSERT INTO raw_items (id,feed_id,source,url,title,body,fetched_at)"
                " VALUES ('old','f1','S','https://e/old','t','b',?)", (NOW.isoformat(),))
    raw.commit(); raw.close()
    assert sqlite3.connect(str(p)).execute("PRAGMA user_version").fetchone()[0] == 0

    s = SqliteStore(p)   # opening must migrate in place, not lose the legacy row
    assert s.conn.execute("PRAGMA user_version").fetchone()[0] == 1
    items = s.get_unprocessed()
    assert [i.id for i in items] == ["old"]          # legacy row defaults to unprocessed
    assert s.mark_processed(["old"]) == 1
