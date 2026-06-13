import json
from mockfirestore import MockFirestore
from newsstore.store.sqlite_store import SqliteStore
from newsstore.store.firestore_store import FirestoreStore


def test_sqlite_set_meta_upserts(tmp_path):
    s = SqliteStore(tmp_path / "db.sqlite")
    s.set_meta("sources", {"sources": ["A", "B"]})
    row = s.conn.execute("SELECT value FROM meta WHERE key='sources'").fetchone()
    assert json.loads(row[0]) == {"sources": ["A", "B"]}
    s.set_meta("sources", {"sources": ["C"]})   # 같은 키 덮어쓰기
    row = s.conn.execute("SELECT value FROM meta WHERE key='sources'").fetchone()
    assert json.loads(row[0]) == {"sources": ["C"]}


def test_firestore_set_meta():
    s = FirestoreStore(MockFirestore())
    s.set_meta("sources", {"sources": ["A", "B"]})
    d = s.db.collection("meta").document("sources").get().to_dict()
    assert d == {"sources": ["A", "B"]}
