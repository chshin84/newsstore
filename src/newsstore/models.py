from __future__ import annotations
import hashlib
from datetime import datetime
from pydantic import BaseModel

def make_id(link: str, fallback: str = "") -> str:
    basis = (link or fallback).strip()
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()

class FeedConfig(BaseModel):
    feed_id: str
    url: str
    source: str
    asset_hint: str = ""
    language: str = "en"
    poll_minutes: int = 60
    body_mode: str = "summary"   # full | summary | headline | calendar

class RawItem(BaseModel):
    id: str
    feed_id: str
    source: str
    asset_hint: str = ""
    language: str = "en"
    url: str
    title: str
    body: str = ""
    published_at: datetime | None = None
    fetched_at: datetime
