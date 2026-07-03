from __future__ import annotations
import logging
from dataclasses import dataclass
import httpx
from .feeds import FeedConfig

log = logging.getLogger(__name__)

# 요청용 브라우저 UA(SSOT). 다른 모듈(ssl_config 등)은 복제하지 말고 여기서 import.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
DEFAULT_HEADERS = {"User-Agent": USER_AGENT}

@dataclass
class FetchResult:
    status: int
    content: bytes
    etag: str | None
    last_modified: str | None

def fetch_feed(client: httpx.Client, feed: FeedConfig,
               etag: str | None = None, last_modified: str | None = None) -> FetchResult:
    headers = dict(DEFAULT_HEADERS)
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    try:
        r = client.get(feed.url, headers=headers)
    except httpx.HTTPError as exc:
        # 원인(DNS/TLS/타임아웃)을 남긴다 — 하류 로그는 'HTTP -1'뿐이라 이게 유일한 단서.
        log.warning("feed %s: fetch failed: %r", feed.feed_id, exc)
        return FetchResult(status=-1, content=b"", etag=None, last_modified=None)
    content = b"" if r.status_code == 304 else r.content
    return FetchResult(status=r.status_code, content=content,
                       etag=r.headers.get("ETag"), last_modified=r.headers.get("Last-Modified"))
