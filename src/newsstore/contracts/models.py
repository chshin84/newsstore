from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel


class RawItem(BaseModel):
    id: str
    feed_id: str
    source: str
    asset_hint: str = ""
    language: str = "en"
    url: str
    title: str
    body: str = ""
    symbol: str = ""          # FMP 티커 태깅 보존(RSS는 빈 문자열, 하위호환)
    published_at: datetime | None = None
    fetched_at: datetime
