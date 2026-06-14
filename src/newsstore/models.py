from __future__ import annotations
import hashlib
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
