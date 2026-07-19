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
    """get_pending_embed_items 반환 — 임베딩 입력(title·body)과 TTL 미러링(expire_at).
    키는 기존 관례 `id`가 아니라 `item_id`다 — item_vectors가 items를 참조하는 외래 키
    성격이라 명시적으로 구분하며, 문서 경로 item_vectors/{item_id}와 정합한다."""
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
