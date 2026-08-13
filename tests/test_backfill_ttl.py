"""run_backfill_ttl: 기존 expire_at을 현행 TTL 계약으로 재계산하는 일회성 백필.

기간은 여기서도 store 상수를 import하지 않고 따로 박는다 — import하면 상수를 바꿀 때
테스트가 함께 움직여 계약이 조용히 흘러간다(test_firestore_store와 같은 이유).
"""
from datetime import datetime, timezone, timedelta

from newsstore.entrypoints.run_backfill_ttl import backfill_ttl

NOW = datetime(2026, 6, 12, 7, 0, tzinfo=timezone.utc)
TTL = timedelta(days=365)          # 계약을 못 박는 두 번째 못
OLD_TTL = timedelta(days=60)       # 백필 이전에 쓰인 옛 기간


def _put_item(db, doc_id, *, fetched_at=NOW, expire_at=None, with_vector=False):
    """옛 계약으로 저장된 문서를 흉내낸다(expire_at 기본값 = fetched_at + 60일)."""
    exp = (fetched_at + OLD_TTL) if expire_at is None else expire_at
    db.collection("items").document(doc_id).set(
        {"feed_id": "f1", "source": "S", "url": f"https://e/{doc_id}",
         "title": f"t{doc_id}", "body": "b", "kind": "story",
         "fetched_at": fetched_at, "expire_at": exp})
    if with_vector:
        db.collection("item_vectors").document(doc_id).set(
            {"vector": [0.1] * 768, "embed_model": "gemini-embedding-001",
             "embed_task_type": "RETRIEVAL_DOCUMENT", "embedded_at": fetched_at,
             "expire_at": exp})


def _expire_of(db, col, doc_id):
    return (db.collection(col).document(doc_id).get().to_dict() or {}).get("expire_at")


def test_recomputes_expire_at_from_fetched_at(store):
    _put_item(store.db, "a")
    stats = backfill_ttl(store)
    assert stats["items_updated"] == 1
    assert _expire_of(store.db, "items", "a") == NOW + TTL


def test_vector_mirrors_the_same_expire_at(store):
    _put_item(store.db, "v", with_vector=True)
    stats = backfill_ttl(store)
    assert stats["vectors_updated"] == 1
    # 벡터가 원본보다 먼저 만료되면 계약이 깨진다 — 두 값이 같아야 한다.
    assert _expire_of(store.db, "item_vectors", "v") == NOW + TTL
    assert _expire_of(store.db, "items", "v") == _expire_of(store.db, "item_vectors", "v")


def test_item_without_vector_does_not_break_the_batch(store):
    # 비-story는 벡터가 없다. batch.update가 없는 문서를 만나면 배치 전체가 죽으므로,
    # 벡터 있는 항목과 없는 항목이 한 배치에 섞인 상태를 재현한다.
    _put_item(store.db, "n1")
    _put_item(store.db, "n2", with_vector=True)
    _put_item(store.db, "n3")
    stats = backfill_ttl(store)
    assert stats["items_updated"] == 3 and stats["vectors_updated"] == 1
    for doc_id in ("n1", "n2", "n3"):
        assert _expire_of(store.db, "items", doc_id) == NOW + TTL
    # 없던 벡터를 새로 만들어내지 않는다(유령 문서 금지).
    assert not store.db.collection("item_vectors").document("n1").get().exists


def test_rerun_is_idempotent(store):
    _put_item(store.db, "i", with_vector=True)
    first = backfill_ttl(store)
    second = backfill_ttl(store)
    assert first["items_updated"] == 1
    # 두 번째는 아무것도 고치지 않는다 — 더하기였다면 여기서 값이 또 밀린다.
    assert second["items_updated"] == 0 and second["already_ok"] == 1
    assert _expire_of(store.db, "items", "i") == NOW + TTL
    assert _expire_of(store.db, "item_vectors", "i") == NOW + TTL


def test_paginates_past_the_page_size(store):
    for n in range(7):
        _put_item(store.db, f"p{n}")
    stats = backfill_ttl(store, page=2)     # 4페이지에 걸친다
    assert stats["scanned"] == 7 and stats["items_updated"] == 7
    for n in range(7):
        assert _expire_of(store.db, "items", f"p{n}") == NOW + TTL


def test_dry_run_reports_without_writing(store):
    _put_item(store.db, "d", with_vector=True)
    stats = backfill_ttl(store, dry_run=True)
    assert stats["items_updated"] == 1 and stats["vectors_updated"] == 1
    # 보고만 하고 문서는 옛 값 그대로여야 한다.
    assert _expire_of(store.db, "items", "d") == NOW + OLD_TTL
    assert _expire_of(store.db, "item_vectors", "d") == NOW + OLD_TTL


def test_missing_fetched_at_is_counted_not_swallowed(store):
    store.db.collection("items").document("bad").set(
        {"source": "S", "title": "t", "expire_at": NOW + OLD_TTL})    # fetched_at 없음
    _put_item(store.db, "good")
    stats = backfill_ttl(store)
    assert stats["no_fetched_at"] == 1
    assert stats["items_updated"] == 1                    # good만 고친다
    assert _expire_of(store.db, "items", "bad") == NOW + OLD_TTL      # 손대지 않는다


def test_reports_oldest_fetched_at(store):
    oldest = NOW - timedelta(days=40)
    _put_item(store.db, "old", fetched_at=oldest)
    _put_item(store.db, "new", fetched_at=NOW)
    stats = backfill_ttl(store)
    assert stats["oldest_fetched_at"] == oldest
