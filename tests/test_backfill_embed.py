"""백필 — 레거시(플래그 없는) story 문서 마킹 + drain 루프(무진전 가드)."""
from datetime import datetime, timezone, timedelta

NOW = datetime.now(timezone.utc)


def _legacy_doc(db, i, *, kind="story", life=timedelta(days=20)):
    """배포 전 저장된(embed_pending 없는) 문서를 직접 기록해 레거시를 시뮬레이션."""
    db.collection("items").document(i).set({
        "title": f"t{i}", "body": "b", "kind": kind,
        "fetched_at": NOW, "expire_at": NOW + life,
    })


def test_mark_pending_selects_unembedded_fresh_stories(store):
    from newsstore.entrypoints.run_backfill_embed import mark_pending
    db = store.db
    _legacy_doc(db, "L1")                                     # 대상
    _legacy_doc(db, "L2", kind="spam")                        # 비-story → 제외
    _legacy_doc(db, "L3")                                     # 벡터 이미 있음 → 제외
    db.collection("item_vectors").document("L3").set({"vector": [0.1] * 768})
    _legacy_doc(db, "L4", life=timedelta(days=1))             # 잔여 수명 <2일 → 제외
    assert mark_pending(store) == 1
    assert db.collection("items").document("L1").get().to_dict()["embed_pending"] is True
    for i in ("L2", "L3", "L4"):
        assert "embed_pending" not in db.collection("items").document(i).get().to_dict()


def test_mark_pending_is_idempotent(store):
    from newsstore.entrypoints.run_backfill_embed import mark_pending
    _legacy_doc(store.db, "L5")
    assert mark_pending(store) == 1
    assert mark_pending(store) == 0        # 재실행 — 이미 마킹된 것은 추가 마킹 없음


class AlwaysRetryable:
    def embed(self, text, *, timeout=30.0):
        from newsstore.embed.gemini import LLMError
        raise LLMError("persistent transient")


def test_drain_stops_after_no_progress(store):
    """재시도 가능 실패만 계속 나오면 무한 루프 대신 무진전 2회에서 멈춘다."""
    from newsstore.entrypoints.run_backfill_embed import drain
    from newsstore.contracts.models import RawItem
    store.upsert_items([RawItem(id="d1", feed_id="f", source="S", url="https://e/d1",
                                title="Fed", body="b", fetched_at=NOW)])
    totals = drain(store, AlwaysRetryable(), cap=10)
    assert totals["embedded"] == 0
    assert len(store.get_pending_embed_items(limit=10)) == 1   # 플래그는 남아 정규 런 몫


def test_drain_drains_to_zero(store):
    from newsstore.entrypoints.run_backfill_embed import drain
    from newsstore.contracts.models import RawItem

    class OkEmbed:
        def embed(self, text, *, timeout=30.0):
            return [0.1] * 768

    store.upsert_items([RawItem(id=f"d{i}", feed_id="f", source="S", url=f"https://e/d{i}",
                                title=f"Fed {i}", body="b", fetched_at=NOW) for i in range(5)])
    totals = drain(store, OkEmbed(), cap=2)          # cap<대기 — 여러 라운드에 걸쳐 소진
    assert totals["embedded"] == 5
    assert store.get_pending_embed_items(limit=10) == []
