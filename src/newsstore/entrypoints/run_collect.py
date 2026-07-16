from __future__ import annotations
import argparse
import logging
import os
from ..collect.feeds import load_feeds, distinct_sources, source_tiers
from ..collect.ssl_config import make_client
from ..store.factory import make_store
from ..collect.collector import collect_once

log = logging.getLogger("newsstore")

# Exit non-zero when at least this fraction of *attempted* feeds failed, so an
# external scheduler (cron / Cloud Scheduler) treats a systemic outage (proxy
# down, cert expired, network gone) as a failed run instead of a silent success.
# Isolated transient feed flakiness stays below the bar and exits 0.
FAIL_RATE_ALERT = 0.5

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="newsstore collector (one pass)")
    ap.add_argument("--feeds", default="config/feeds.yaml")
    ap.add_argument("--force", action="store_true", help="ignore poll intervals (fetch all)")
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=os.environ.get("NEWSSTORE_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    feeds = load_feeds(args.feeds)
    client = make_client()
    embed_failed = False
    with make_store() as store:                  # Firestore(에뮬레이터 or 실)
        # SSOT: 사이트 소스 목록·tier를 feeds.yaml에서 도출해 기록 (하드코딩 X). tier 전파 #17.
        store.set_meta("sources", {"sources": distinct_sources(feeds),
                                   "tiers": source_tiers(feeds)})
        try:
            summary = collect_once(client, store, feeds, force=args.force)
        finally:
            client.close()

        total_new = sum(v for v in summary.values() if v > 0)
        failed = [k for k, v in summary.items() if v == -1]
        attempted = len(summary)      # skipped (not-due) feeds are absent from summary
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

    if attempted and len(failed) / attempted >= FAIL_RATE_ALERT:
        log.error("run FAILED: %d/%d feeds failed (>= %.0f%%): %s",
                  len(failed), attempted, FAIL_RATE_ALERT * 100, ", ".join(sorted(failed)))
        return 1
    if failed:
        log.warning("%d feed(s) failed (isolated): %s", len(failed), ", ".join(sorted(failed)))
    return 1 if embed_failed else 0

if __name__ == "__main__":
    raise SystemExit(main())
