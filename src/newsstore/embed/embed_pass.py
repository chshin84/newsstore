"""수집 후 임베딩 패스 — 대기 큐를 cap까지 임베딩(스펙 2026-07-16).

cap 근거: collector Cloud Run 잡은 task-timeout 600초·5분 주기라, 상한 없이 백필
백로그를 물면 타임아웃 반복(thrash)에 빠진다. 잔여분은 다음 런(또는 백필 drain
루프)이 이어받는다. store는 Protocol 주입(모듈 경계 — embed는 store를 import 안 함).
"""
from __future__ import annotations
import logging

from .embedder import embed_items

log = logging.getLogger("newsstore.embed")

DEFAULT_CAP = 500


def embed_pass(store, client, cap: int = DEFAULT_CAP) -> dict:
    """반환: {"pending": 이번에 읽은 대기 수, "embedded": 저장 수,
    "permanent": 영구 실패(플래그 처분) 수, "retryable": 재시도 예정 수}."""
    pending = store.get_pending_embed_items(limit=cap)
    if not pending:
        return {"pending": 0, "embedded": 0, "permanent": 0, "retryable": 0}
    expire_by_id = {p["item_id"]: p["expire_at"] for p in pending}
    results = embed_items(pending, client)
    entries = [{"item_id": r.item_id, "vector": r.vector,
                "expire_at": expire_by_id[r.item_id]}
               for r in results if r.outcome == "ok"]
    permanent = [r for r in results if r.outcome == "permanent"]
    retryable = [r for r in results if r.outcome == "retryable"]
    embedded = store.save_vectors(entries)
    if permanent:
        store.clear_embed_pending([r.item_id for r in permanent])
        for r in permanent:
            log.error("embed permanent failure %s: %s (pending cleared, no vector)",
                      r.item_id, r.reason)
    for r in retryable:
        log.warning("embed retryable failure %s: %s (retried next run)",
                    r.item_id, r.reason)
    return {"pending": len(pending), "embedded": embedded,
            "permanent": len(permanent), "retryable": len(retryable)}
