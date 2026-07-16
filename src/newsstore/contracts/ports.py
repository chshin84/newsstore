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


class PendingItem(TypedDict):
    """get_pending_embed_items 반환 — 임베딩 입력(title·body)과 TTL 미러링(expire_at)."""
    item_id: str
    title: str
    body: str
    expire_at: datetime


class VectorEntry(TypedDict):
    """save_vectors 입력 — 호출자는 이 셋만 제공, embed_model·embedded_at은 store가 주입."""
    item_id: str
    vector: list[float]
    expire_at: datetime


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
    # 팩터·펀더멘털 계약(다운스트림 seam) — 제네릭 컬렉션 적재. store가 expire_at(수집 시각+30일) 주입.
    def save_docs(self, collection: str, docs: list[dict]) -> int:
        """collection에 문서 배치 set(각 doc는 'id' 보유). 반환=쓴 수."""
        ...
    def filter_new_ids_in(self, collection: str, ids: list[str]) -> list[str]:
        """collection에 아직 없는 id만(입력 순서 보존)."""
        ...
    def save_snapshot(self, collection: str, doc_id: str, data: dict) -> None:
        """현재값 스냅샷 한 문서 덮어쓰기(profiles·index_members 등)."""
        ...
    def get_snapshot(self, collection: str, doc_id: str) -> dict:
        """collection/{doc_id}. 없으면 {}."""
        ...
    def get_docs(self, collection: str, *, field: str | None = None, value=None) -> list[dict]:
        """collection 문서 조회(field 지정 시 where 필터, 아니면 전체)."""
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

    # 임베딩 계약(spec 2026-07-16) — item_vectors 컬렉션 + items.embed_pending 플래그.
    def get_pending_embed_items(self, limit: int) -> list[PendingItem]:
        """items where embed_pending==true 를 limit까지(대기 큐 조회)."""
        ...
    def save_vectors(self, entries: list[VectorEntry]) -> int:
        """item_vectors set + 원본 embed_pending 해제(같은 batch). embed_model·embedded_at은
        store가 주입(단일 통제점). 원본이 TTL로 사라진 항목은 건너뛴다(격리). 반환=쓴 수."""
        ...
    def clear_embed_pending(self, ids: list[str]) -> None:
        """재시도 무의미(영구 실패) 기사의 플래그 처분 — 벡터 없이 플래그만 제거."""
        ...
