from __future__ import annotations
import argparse
import os
from .config import load_feeds
from .ssl_config import make_client
from .store.sqlite_store import SqliteStore
from .collector import collect_once

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="newsstore collector (one pass)")
    ap.add_argument("--feeds", default="config/feeds.yaml")
    ap.add_argument("--db", default=os.environ.get("NEWSSTORE_DB", "data/newsstore.db"))
    ap.add_argument("--force", action="store_true", help="ignore poll intervals (fetch all)")
    args = ap.parse_args(argv)

    os.makedirs(os.path.dirname(args.db) or ".", exist_ok=True)
    feeds = load_feeds(args.feeds)
    store = SqliteStore(args.db)
    client = make_client()
    try:
        summary = collect_once(client, store, feeds, force=args.force)
    finally:
        client.close()

    total_new = sum(v for v in summary.values() if v > 0)
    failed = [k for k, v in summary.items() if v == -1]
    print(f"collected {total_new} new item(s); store total = {store.count()}")
    for fid, n in sorted(summary.items()):
        print(f"  {fid}: {'FAIL' if n == -1 else n}")
    if failed:
        print(f"failed feeds: {', '.join(failed)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
