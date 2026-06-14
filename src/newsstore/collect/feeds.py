from __future__ import annotations
import hashlib
from pathlib import Path
import yaml
from pydantic import BaseModel, ConfigDict


def make_id(link: str, fallback: str = "") -> str:
    basis = (link or fallback).strip()
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()


class FeedConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")   # typo'd registry keys fail loudly
    feed_id: str
    url: str
    source: str
    asset_hint: str = ""
    language: str = "en"
    poll_minutes: int = 60
    body_mode: str = "summary"   # full | summary | headline | calendar
    tz_offset: float | None = None   # hours; set for feeds emitting naive local time (infomax KST=9)


def load_feeds(path) -> list[FeedConfig]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    feeds = [FeedConfig(**entry) for entry in data["feeds"]]
    ids = [f.feed_id for f in feeds]
    dups = sorted({i for i in ids if ids.count(i) > 1})
    if dups:
        raise ValueError(f"duplicate feed_id in registry: {dups}")
    return feeds


def distinct_sources(feeds: list[FeedConfig]) -> list[str]:
    """Unique source labels in feeds.yaml order — SSOT for the site's source list."""
    seen: list[str] = []
    for f in feeds:
        if f.source not in seen:
            seen.append(f.source)
    return seen
