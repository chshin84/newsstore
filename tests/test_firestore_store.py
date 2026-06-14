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

def test_get_unprocessed_and_mark_processed():
    s = _store()
    s.upsert_items([_item("a"), _item("b"), _item("c")])
    assert {i.id for i in s.get_unprocessed()} == {"a", "b", "c"}
    assert len(s.get_unprocessed(limit=2)) == 2
    one = s.get_unprocessed(limit=1)[0]                 # round-trips to a RawItem
    assert one.fetched_at == NOW and one.feed_id == "f1"
    assert s.mark_processed(["a", "b"], processed_at=NOW) == 2
    assert {i.id for i in s.get_unprocessed()} == {"c"}
    assert s.mark_processed(["a", "b"]) == 0            # idempotent
    assert s.mark_processed([]) == 0

def test_upsert_preserves_processed_on_resee():
    s = _store()
    s.upsert_items([_item("a")])
    assert s.mark_processed(["a"], processed_at=NOW) == 1
    assert s.upsert_items([_item("a")]) == 0            # re-seen, not re-written
    assert s.get_unprocessed() == []                    # still processed


# 실 google client는 빈 문서에 exists=True여도 to_dict()=None을 준다 (MockFirestore는 못 잡는 gotcha).
class _NoneSnap:
    exists = True
    def to_dict(self):
        return None
class _NoneRef:
    def get(self):
        return _NoneSnap()
    def set(self, d):
        raise AssertionError("빈 문서엔 write하면 안 됨")
class _NoneCol:
    def document(self, _id):
        return _NoneRef()
class _NoneDB:
    def collection(self, _name):
        return _NoneCol()

def test_mark_processed_guards_none_document():
    # to_dict()=None인 빈 문서를 만나도 AttributeError로 터지지 않고 조용히 건너뛴다 (or {} 가드).
    s = FirestoreStore(_NoneDB())
    assert s.mark_processed(["a"]) == 0
