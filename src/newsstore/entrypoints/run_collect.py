from __future__ import annotations
import argparse
import logging
import os
from ..collect.feeds import load_feeds, distinct_sources
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
    with make_store() as store:                  # Firestore(에뮬레이터 or 실)
        # SSOT: 사이트 소스 드롭다운 목록을 feeds.yaml에서 도출해 기록 (하드코딩 X)
        store.set_meta("sources", {"sources": distinct_sources(feeds)})
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

    if attempted and len(failed) / attempted >= FAIL_RATE_ALERT:
        log.error("run FAILED: %d/%d feeds failed (>= %.0f%%): %s",
                  len(failed), attempted, FAIL_RATE_ALERT * 100, ", ".join(sorted(failed)))
        return 1
    if failed:
        log.warning("%d feed(s) failed (isolated): %s", len(failed), ", ".join(sorted(failed)))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
