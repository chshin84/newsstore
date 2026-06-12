from __future__ import annotations
import time
from datetime import datetime, timezone
import feedparser
from bs4 import BeautifulSoup
from .models import FeedConfig, RawItem, make_id

def _clean(html: str) -> str:
    text = BeautifulSoup(html or "", "lxml").get_text(" ", strip=True)
    return " ".join(text.split())

def _published(entry) -> datetime | None:
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    if not t:
        return None
    return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc)

def parse_feed(raw: bytes, feed: FeedConfig, fetched_at: datetime) -> list[RawItem]:
    fp = feedparser.parse(raw)
    items: list[RawItem] = []
    for e in fp.entries:
        link = (e.get("link") or "").strip()
        title = (e.get("title") or "").strip()
        body_html = e["content"][0]["value"] if e.get("content") else e.get("summary", "")
        items.append(RawItem(
            id=make_id(link, fallback=title),
            feed_id=feed.feed_id, source=feed.source, asset_hint=feed.asset_hint,
            language=feed.language, url=link, title=title,
            body=_clean(body_html), published_at=_published(e), fetched_at=fetched_at,
        ))
    return items
