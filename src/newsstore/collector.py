from __future__ import annotations
from datetime import datetime, timezone, timedelta
import httpx
from .models import FeedConfig
from .store.base import Store
from .fetcher import fetch_feed
from .parser import parse_feed

def is_due(state: dict, poll_minutes: int, now: datetime) -> bool:
    last = state.get("last_fetched")
    if not last:
        return True
    return (now - last) >= timedelta(minutes=poll_minutes)

def collect_once(client: httpx.Client, store: Store, feeds: list[FeedConfig],
                 now: datetime | None = None, force: bool = False) -> dict:
    now = now or datetime.now(timezone.utc)
    summary: dict[str, int] = {}
    for feed in feeds:
        state = store.get_feed_state(feed.feed_id)
        if not force and not is_due(state, feed.poll_minutes, now):
            continue
        res = fetch_feed(client, feed, state.get("etag"), state.get("last_modified"))
        if res.status == 304:
            store.set_feed_state(feed.feed_id, last_fetched=now)
            summary[feed.feed_id] = 0
            continue
        if res.status != 200:
            summary[feed.feed_id] = -1     # transient failure; retried next pass
            continue
        items = parse_feed(res.content, feed, fetched_at=now)
        new = store.upsert_items(items)
        store.set_feed_state(feed.feed_id, etag=res.etag,
                             last_modified=res.last_modified, last_fetched=now)
        summary[feed.feed_id] = new
    return summary
