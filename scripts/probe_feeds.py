"""신규 피드 라이브 프로빙. Docker(KR IP) 1회 실행, 저장 없음.
사용: python scripts/probe_feeds.py <feed_id> [...]  (인자 없으면 전체)"""
from __future__ import annotations
import sys
from datetime import datetime, timezone
import httpx
from newsstore.collect.feeds import load_feeds
from newsstore.collect.fetcher import fetch_feed   # collector.py와 동일 fetch
from newsstore.collect.parser import parse_feed    # parse_feed(raw, feed, fetched_at)

def main(ids: list[str]) -> int:
    feeds = {f.feed_id: f for f in load_feeds("config/feeds.yaml")}
    targets = ids or list(feeds)
    now = datetime.now(timezone.utc)
    bad = 0
    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        for fid in targets:
            f = feeds.get(fid)
            if not f:
                print(f"{fid:18} MISSING"); bad += 1; continue
            try:
                res = fetch_feed(client, f, None, None)   # (client, feed, etag, last_modified)
                if res.status != 200:
                    print(f"{fid:18} HTTP {res.status}"); bad += 1; continue
                items = parse_feed(res.content, f, fetched_at=now)
                n = len(items)
                has_body = any((it.body or "").strip() for it in items)
                print(f"{fid:18} entries={n:3} has_body={has_body}")
                if n == 0:
                    bad += 1
            except Exception as e:
                print(f"{fid:18} ERROR {type(e).__name__}: {e}"); bad += 1
    print(f"\n{bad} feed(s) need attention")
    return 0 if bad == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
