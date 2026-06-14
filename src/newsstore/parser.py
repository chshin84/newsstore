from __future__ import annotations
import calendar
import logging
from datetime import datetime, timezone, timedelta
import feedparser
from bs4 import BeautifulSoup
from .models import FeedConfig, make_id
from .contracts.models import RawItem

log = logging.getLogger(__name__)

def _clean(html: str) -> str:
    text = BeautifulSoup(html or "", "lxml").get_text(" ", strip=True)
    return " ".join(text.split())

def _body_for_mode(entry, body_mode: str) -> str:
    """Honor the feed's body_mode knob (drives Step-2 card/body cost).
    headline -> no body; summary -> the <description>; full -> content:encoded
    when present, else summary. Unknown modes fall back to summary."""
    if body_mode == "headline":
        return ""
    summary = entry.get("summary", "")
    if body_mode == "full" and entry.get("content"):
        return entry["content"][0]["value"]
    return summary

def _published(entry, tz_offset: float | None = None) -> datetime | None:
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    if not t:
        return None
    if tz_offset is not None:
        # Feed emits naive local wall-clock with no offset (e.g. infomax KST);
        # feedparser assumed UTC, so reinterpret those numbers at the real offset.
        naive = datetime(*t[:6])
        return naive.replace(tzinfo=timezone(timedelta(hours=tz_offset))).astimezone(timezone.utc)
    # feedparser yields *_parsed as a UTC struct_time; timegm interprets it as
    # UTC (host-TZ independent). time.mktime() would treat it as local time and
    # corrupt every published_at by the host offset.
    return datetime.fromtimestamp(calendar.timegm(t), tz=timezone.utc)

def parse_feed(raw: bytes, feed: FeedConfig, fetched_at: datetime) -> list[RawItem]:
    fp = feedparser.parse(raw)
    items: list[RawItem] = []
    skipped = 0
    for e in fp.entries:
        link = (e.get("link") or "").strip()
        guid = (e.get("id") or "").strip()
        title = (e.get("title") or "").strip()
        # Global url-based dedup basis: prefer link, then <guid>, then title.
        # An entry with none of the three would collapse onto sha1("") and
        # silently overwrite an unrelated item — drop it instead.
        basis = link or guid or title
        if not basis:
            skipped += 1
            continue
        body_html = _body_for_mode(e, feed.body_mode)
        items.append(RawItem(
            id=make_id(basis),
            feed_id=feed.feed_id, source=feed.source, asset_hint=feed.asset_hint,
            language=feed.language, url=link, title=title,
            body=_clean(body_html), published_at=_published(e, feed.tz_offset), fetched_at=fetched_at,
        ))
    if skipped:
        log.warning("feed %s: skipped %d entr(ies) with no link/guid/title",
                    feed.feed_id, skipped)
    return items
