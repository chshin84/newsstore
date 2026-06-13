from datetime import datetime, timezone
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
