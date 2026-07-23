from __future__ import annotations
import argparse
import logging
import os
from ..collect.feeds import load_feeds, distinct_sources, source_tiers
from ..collect.ssl_config import make_client
from ..store.factory import make_store
from ..collect.collector import collect_once
from ._health import job_health

log = logging.getLogger("newsstore")

# 런의 성공/실패 ≠ 개별 피드의 건강. 런은 '시스템 장애'(프록시·인증·네트워크 다운으로 평소 멀쩡하던
# 피드 다수가 갑자기 실패)에서만 exit 1. 한두 개·만성 죽은 피드가 죽어도 런은 성공(exit 0)이고,
# 그건 로그·대시보드로 surface한다. 아래 두 문턱이 오판(특히 소수 배치)을 막는다.
FAIL_RATE_ALERT = 0.5
CHRONIC_DEAD_STREAK = 5       # 연속 실패 이상이면 '만성 죽음' — 시스템 장애 판정에서 제외(이미 아는 죽음)
MIN_ATTEMPTED_FOR_ALERT = 10  # 정상 피드 시도가 이 수 미만이면 실패율 알람 없음(소수 배치 우연 전멸 오판 방지)

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="newsstore collector (one pass)")
    ap.add_argument("--feeds", default="config/feeds.yaml")
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=os.environ.get("NEWSSTORE_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    feeds = load_feeds(args.feeds)
    client = make_client()
    embed_failed = False
    with make_store() as store, job_health(store, "collector") as h:   # Firestore(에뮬레이터 or 실)
        # SSOT: 사이트 소스 목록·tier를 feeds.yaml에서 도출해 기록 (하드코딩 X). tier 전파 #17.
        store.set_meta("sources", {"sources": distinct_sources(feeds),
                                   "tiers": source_tiers(feeds)})
        try:
            summary = collect_once(client, store, feeds)
        finally:
            client.close()

        total_new = sum(v for v in summary.values() if v > 0)
        failed = [k for k, v in summary.items() if v == -1]
        attempted = len(summary)      # 이제 모든 피드가 매번 시도되므로 attempted == len(feeds)
        # 만성 죽은 피드(연속실패 ≥ CHRONIC_DEAD_STREAK)는 시스템 장애 판정에서 제외한다.
        # (collect_once가 이번 실패로 연속실패를 이미 올려둠 — store 열린 여기서 읽는다.)
        chronic = {k for k in failed
                   if (store.get_feed_state(k).get("consecutive_failures") or 0) >= CHRONIC_DEAD_STREAK}
        new_failed = sorted(k for k in failed if k not in chronic)
        healthy_attempted = attempted - len(chronic)
        log.info("collected %d new item(s); store total = %d", total_new, store.count())
        for fid, n in sorted(summary.items()):
            log.info("  %s: %s", fid, "FAIL" if n == -1 else n)

        # ── 임베딩 패스(스펙 2026-07-16) — 수집과 격리: 여기 실패해도 수집분은 이미 저장됨.
        # 키 부재 fail-loud는 '대기분 실재'로 좁힌다(키 없는 로컬 수집 스모크 보존).
        api_key = os.environ.get("GEMINI_API_KEY")
        try:
            if api_key:
                from ..embed.gemini import GeminiEmbedClient
                from ..embed.embed_pass import embed_pass
                es = embed_pass(store, GeminiEmbedClient(api_key))
                log.info("embed pass: pending=%d embedded=%d permanent=%d retryable=%d",
                         es["pending"], es["embedded"], es["permanent"], es["retryable"])
            elif store.get_pending_embed_items(limit=1):
                log.error("GEMINI_API_KEY missing but embed_pending items exist "
                          "(embedding stalled — set the secret)")
                embed_failed = True
            else:
                log.warning("GEMINI_API_KEY not set; no pending embeds — skipping embed pass")
        except Exception:
            log.exception("embed pass failed (collection results preserved)")
            embed_failed = True

        h["detail"] = (f"new={total_new} failed={len(new_failed)} "
                       f"chronic={len(chronic)} embed={'fail' if embed_failed else 'ok'}")

    # 시스템 장애만 런을 실패시킨다: 정상 피드가 최소 시도 이상에서 다수 실패할 때.
    if healthy_attempted >= MIN_ATTEMPTED_FOR_ALERT and \
            len(new_failed) / healthy_attempted >= FAIL_RATE_ALERT:
        log.error("run FAILED (systemic): %d/%d 정상 피드 실패: %s",
                  len(new_failed), healthy_attempted, ", ".join(new_failed))
        return 1
    if new_failed:
        log.warning("%d feed(s) failed (isolated): %s", len(new_failed), ", ".join(new_failed))
    if chronic:
        log.warning("만성 죽은 피드 %d개(런 실패 아님 — 정리 대상): %s",
                    len(chronic), ", ".join(sorted(chronic)))
    return 1 if embed_failed else 0

if __name__ == "__main__":
    raise SystemExit(main())
