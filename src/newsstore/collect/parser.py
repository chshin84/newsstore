from __future__ import annotations
import calendar
import logging
from datetime import datetime, timezone, timedelta
import feedparser
from bs4 import BeautifulSoup
from .feeds import FeedConfig, make_id
from ..contracts.models import RawItem

log = logging.getLogger(__name__)

class FeedParseError(Exception):
    """응답이 피드가 아님(WAF 차단·챌린지·오류 페이지가 HTTP 200으로 온 경우)."""

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
    # HTTP 200이어도 차단·오류 페이지면 feedparser는 예외 없이 entries=0을 준다.
    # 이를 '0건 성공'으로 삼키면 피드가 조용히 영구 무수집이 된다(fail-loud).
    # 인식된 피드 포맷(version)의 빈 피드만 합법 — 정상형 XML 차단 페이지는
    # bozo=0이라 version 부재도 함께 본다. 빈 본문(0바이트) 응답에서는 version
    # 키가 아예 없어 속성 접근이 AttributeError를 낸다 — 가드가 스스로 죽지 않게
    # 반드시 .get()으로 읽는다(부재도 '포맷 미인식'으로 같이 처리).
    version = fp.get("version")
    if not fp.entries and (fp.bozo or not version):
        raise FeedParseError(
            f"not a parseable feed (bozo={bool(fp.bozo)}, version={version!r})")
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
