from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta
import httpx
from .feeds import FeedConfig
from ..contracts.ports import Store
from .fetcher import fetch_feed
from .parser import parse_feed, FeedParseError
from .body_fetch import enrich_bodies

log = logging.getLogger(__name__)

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
        # 한 피드의 실패(파싱/저장 예외 포함)가 다른 피드 수집을 막지 않도록 격리한다.
        try:
            state = store.get_feed_state(feed.feed_id)
            if not force and not is_due(state, feed.poll_minutes, now):
                continue
            res = fetch_feed(client, feed, state.get("etag"), state.get("last_modified"))
            if res.status == 304:
                store.set_feed_state(feed.feed_id, last_fetched=now)
                summary[feed.feed_id] = 0
                continue
            if res.status != 200:
                log.warning("feed %s: HTTP %s (transient; retried next pass)",
                            feed.feed_id, res.status)
                summary[feed.feed_id] = -1     # transient failure; retried next pass
                continue
            try:
                items = parse_feed(res.content, feed, fetched_at=now)
            except FeedParseError as exc:
                # 차단/오류 페이지: 이 응답의 ETag·last_fetched를 저장하면 차단
                # 페이지에 304를 받아 무수집이 고착된다 — 상태 미갱신, 실패 집계.
                log.warning("feed %s: %s (state not updated)", feed.feed_id, exc)
                summary[feed.feed_id] = -1
                continue
            items = enrich_bodies(client, store, items)
            new = store.upsert_items(items)
            store.set_feed_state(feed.feed_id, etag=res.etag,
                                 last_modified=res.last_modified, last_fetched=now)
            summary[feed.feed_id] = new
        except Exception:
            # 격리: 이 피드만 실패 처리, 다음 패스에 재시도. 트레이스백은 남긴다.
            log.exception("feed %s: parse/store error (isolated)", feed.feed_id)
            summary[feed.feed_id] = -1
    return summary
