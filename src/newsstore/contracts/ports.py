from __future__ import annotations
from datetime import datetime
from typing import Protocol, TypedDict
from .models import RawItem


# ── Store 반환 shape 계약(EXPLICIT) — 산문 docstring 대신 타입으로 박는다 ──────────
# (from __future__ annotations로 런타임 평가 안 함 — 순수 문서/타입체크용.)

class FeedState(TypedDict, total=False):
    """get_feed_state 반환: 비었거나 폴링 캐시 필드."""
    etag: str
    last_modified: str
    last_fetched: datetime


class Store(Protocol):
    def upsert_items(self, items: list[RawItem]) -> int:
        """Insert items, skipping ids already present. Returns count of NEW items."""
        ...
    def get_feed_state(self, feed_id: str) -> FeedState:
        """Return {} or {'etag','last_modified','last_fetched'(datetime)}."""
        ...
    def set_feed_state(self, feed_id: str, **fields) -> None: ...
    def count(self) -> int: ...

    def filter_new_ids(self, ids: list[str]) -> list[str]:
        """`items`에 아직 없는 id만(입력 순서 보존)."""
        ...

    def set_meta(self, key: str, value: dict) -> None:
        """Write a small public-read metadata doc for the site (e.g. 'sources')."""
        ...

    def save_price(self, key: str, data: dict) -> None:
        """prices/{key} 최신 가격 스냅샷 set(뉴스 vs 가격 반응 앵커). store가 expire_at TTL 주입."""
        ...
    def get_price(self, key: str) -> dict:
        """prices/{key}. 없으면 {}."""
        ...
    def save_fundamental(self, symbol: str, data: dict) -> None:
        """fundamentals/{symbol} 최신 스냅샷 set(income/balance/cashflow). store가 expire_at TTL 주입."""
        ...
    def get_fundamental(self, symbol: str) -> dict:
        """fundamentals/{symbol}. 없으면 {}."""
        ...

    def filter_new_bar_ids(self, ids: list[str]) -> list[str]:
        """`price_bars`에 아직 없는 바 id만(입력 순서 보존) — 새 5분봉만 write."""
        ...
    def save_bars(self, bars: list[dict]) -> int:
        """price_bars 배치 적재(바 1개=문서 1개). 각 bar는 'id'·'datetime' 보유.
        store가 바 날짜 기준 expire_at TTL 주입. 반환=쓴 수."""
        ...
    def get_bars(self, key: str) -> list[dict]:
        """price_bars에서 한 심볼(key)의 바를 datetime 오름차순으로."""
        ...
