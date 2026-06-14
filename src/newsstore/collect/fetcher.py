from __future__ import annotations
from dataclasses import dataclass
import httpx
from .feeds import FeedConfig

@dataclass
class FetchResult:
    status: int
    content: bytes
    etag: str | None
    last_modified: str | None

def fetch_feed(client: httpx.Client, feed: FeedConfig,
               etag: str | None = None, last_modified: str | None = None) -> FetchResult:
    headers = {}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    try:
        r = client.get(feed.url, headers=headers)
    except httpx.HTTPError:
        return FetchResult(status=-1, content=b"", etag=None, last_modified=None)
    content = b"" if r.status_code == 304 else r.content
    return FetchResult(status=r.status_code, content=content,
                       etag=r.headers.get("ETag"), last_modified=r.headers.get("Last-Modified"))
