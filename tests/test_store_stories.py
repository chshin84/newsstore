from datetime import datetime, timezone, timedelta
from mockfirestore import MockFirestore
from newsstore.store.sqlite_store import SqliteStore
from newsstore.store.firestore_store import FirestoreStore

NOW = datetime(2026, 6, 13, 7, 0, tzinfo=timezone.utc)

def _sql(tmp_path): return SqliteStore(tmp_path / "db.sqlite")
def _fs(): return FirestoreStore(MockFirestore())

def _check_create_append(s):
    s.create_story("st1", title="Iran deal", vec=[2.0, 0.0], member_id="a",
                   entities=["geopolitics"], now=NOW)
    s.append_to_story("st1", vec=[0.0, 2.0], member_id="b",
                      entities=["oil"], now=NOW)
    open_now = s.get_open_stories(cutoff=NOW)
    st = [x for x in open_now if x["id"] == "st1"][0]
    assert st["centroid"] == [1.0, 1.0]

def test_sqlite_create_append(tmp_path):
    _check_create_append(_sql(tmp_path))

def test_firestore_create_append():
    _check_create_append(_fs())

def _check_close(s):
    s.create_story("old", title="t", vec=[1.0], member_id="a", entities=[], now=NOW)
    s.create_story("new", title="t", vec=[1.0], member_id="b", entities=[],
                   now=NOW + timedelta(hours=30))
    closed = s.close_stale_stories(cutoff=NOW + timedelta(hours=24))
    assert closed == 1
    open_ids = {x["id"] for x in s.get_open_stories(cutoff=NOW - timedelta(hours=1))}
    assert open_ids == {"new"}

def test_sqlite_close_stale(tmp_path):
    _check_close(_sql(tmp_path))

def test_firestore_close_stale():
    _check_close(_fs())
