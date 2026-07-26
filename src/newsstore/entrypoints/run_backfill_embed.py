"""일회성 백필(스펙 2026-07-16): 레거시 story 기사에 embed_pending을 마킹하고,
정규 embed_pass를 반복 호출(drain)해 즉시 소진한다 — 임베딩 경로는 한 벌(SSOT).

로컬(Docker)에서 실행한다: Cloud Run task-timeout 제약이 없다.
  MSYS_NO_PATHCONV=1 docker compose run --rm collect \
    python -m newsstore.entrypoints.run_backfill_embed
멱등: 현행 계약(모델·task_type)으로 만든 벡터가 이미 있거나 마킹된 기사는 건너뛴다. 재실행 안전.
계약이 바뀌면 옛 벡터는 좌표계가 달라 '없음'으로 취급되어 재임베딩 대상이 된다 — 그래서
모델이나 task_type을 바꾼 뒤 이 스크립트를 돌리는 것이 전량 재임베딩 경로다.
"""
from __future__ import annotations
import argparse
import logging
import os
from datetime import datetime, timezone, timedelta

from ..contracts.embedding import EMBED_MODEL, EMBED_TASK_TYPE
from ..embed.embed_pass import embed_pass, DEFAULT_CAP
from ..store.factory import make_store

log = logging.getLogger("newsstore.backfill_embed")

MIN_LIFE = timedelta(days=2)     # 잔여 수명 2일 미만은 제외 — 곧 만료될 벡터에 쿼터 낭비 방지
_MARK_CHUNK = 250                # Firestore batch 500 op 한도 내(update 1op씩)


def _is_current_contract(vec: dict) -> bool:
    """현재 계약(모델·task_type)으로 만든 벡터인가.

    계약이 바뀌면 옛 벡터는 좌표계가 달라 같은 공간에서 비교할 수 없다. 그래서 '벡터 있음'이
    아니라 '없음'으로 취급해 재임베딩 대상에 넣는다 — 이 판정이 없으면 계약을 바꿔도
    멱등 가드에 걸려 재임베딩이 영영 일어나지 않는다.
    """
    return (vec.get("embed_model") == EMBED_MODEL
            and vec.get("embed_task_type") == EMBED_TASK_TYPE)


def mark_pending(store, *, min_life: timedelta = MIN_LIFE) -> int:
    """kind==story ∧ 현행 계약 벡터 없음 ∧ 미마킹 ∧ 잔여 수명 ≥ min_life 에 embed_pending 마킹.
    select 프로젝션으로 본문 다운로드를 피한다(일회성이지만 read 페이로드 절약)."""
    now = datetime.now(timezone.utc)
    db = store.db
    snaps = list(db.collection("items").where("kind", "==", "story")
                 .select(["expire_at", "embed_pending"]).stream())
    marked = 0
    for i in range(0, len(snaps), _MARK_CHUNK):
        chunk = snaps[i:i + _MARK_CHUNK]
        refs = [db.collection("item_vectors").document(s.id) for s in chunk]
        # 계약 필드만 투영한다 — 768차원 본문까지 받으면 19만 건에서 페이로드가 GB 단위다.
        have_vector = {r.id for r in db.get_all(
            refs, field_paths=["embed_model", "embed_task_type"])
            if r.exists and _is_current_contract(r.to_dict() or {})}
        batch = db.batch()
        pending_ops = 0
        for s in chunk:
            d = s.to_dict() or {}
            if s.id in have_vector or d.get("embed_pending"):
                continue
            exp = d.get("expire_at")
            if exp is None or exp - now < min_life:
                continue
            batch.update(s.reference, {"embed_pending": True})
            pending_ops += 1
        if pending_ops:
            batch.commit()
            marked += pending_ops
    return marked


def drain(store, client, *, cap: int = DEFAULT_CAP) -> dict:
    """embed_pass를 대기분 0까지 반복. 무진전(저장·처분 0) 2회 연속이면 중단하고
    totals["stalled"]=True로 알린다 — 잔여분은 정규 스케줄 런이 이어받는다.
    주의: 재시도 가능 실패 항목은 라운드마다 다시 임베딩을 시도하므로(항목당
    call_with_retry 3회 × 최대 2라운드) 지속 장애 시 쿼터를 추가 소모한다 —
    무진전 2회 가드가 그 상한이다."""
    totals = {"embedded": 0, "permanent": 0, "stalled": False}
    stall = 0
    while True:
        s = embed_pass(store, client, cap=cap)
        totals["embedded"] += s["embedded"]
        totals["permanent"] += s["permanent"]
        if s["pending"] == 0:
            break
        if s["embedded"] + s["permanent"] == 0:
            stall += 1
            if stall >= 2:
                totals["stalled"] = True
                log.error("drain: no progress after 2 rounds; %d pending remain "
                          "(regular runs will retry)", s["pending"])
                break
        else:
            stall = 0
        log.info("drain round: embedded=%d permanent=%d retryable=%d",
                 s["embedded"], s["permanent"], s["retryable"])
    return totals


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="backfill embed_pending + drain (one-off)")
    ap.add_argument("--cap", type=int, default=DEFAULT_CAP, help="embed_pass 라운드당 상한")
    args = ap.parse_args(argv)
    logging.basicConfig(level=os.environ.get("NEWSSTORE_LOG_LEVEL", "INFO"),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        log.error("GEMINI_API_KEY required for backfill")
        return 1
    from ..embed.gemini import GeminiEmbedClient   # lazy — genai 설치 환경에서만
    with make_store() as store:
        marked = mark_pending(store)
        log.info("marked %d legacy story item(s) for embedding", marked)
        totals = drain(store, GeminiEmbedClient(api_key), cap=args.cap)
        if totals["stalled"]:
            log.error("backfill stalled: embedded=%d permanent=%d (regular runs will retry the rest)",
                      totals["embedded"], totals["permanent"])
            return 1
        log.info("backfill done: embedded=%d permanent=%d", totals["embedded"], totals["permanent"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
