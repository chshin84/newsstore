from __future__ import annotations
from datetime import datetime
from typing import Protocol
from ..models import RawItem

class Store(Protocol):
    def upsert_items(self, items: list[RawItem]) -> int:
        """Insert items, skipping ids already present. Returns count of NEW items."""
        ...
    def get_feed_state(self, feed_id: str) -> dict:
        """Return {} or {'etag','last_modified','last_fetched'(datetime)}."""
        ...
    def set_feed_state(self, feed_id: str, **fields) -> None: ...
    def count(self) -> int: ...

    # Step-2 hand-off contract. Any backend (SQLite now, Firestore later) must
    # let the Processor pull un-tagged raw items and mark them done.
    def get_unprocessed(self, limit: int | None = None) -> list[RawItem]:
        """Oldest-first raw items not yet processed by Step-2."""
        ...
    def mark_processed(self, ids: list[str], processed_at: datetime | None = None) -> int:
        """Mark ids processed (idempotent). Returns rows actually changed."""
        ...

    def set_meta(self, key: str, value: dict) -> None:
        """Write a small public-read metadata doc for the site (e.g. 'sources')."""
        ...

    def save_enrichment(self, item_id, *, kind, tags, embedding, story_id) -> None:
        """기사에 Step-2 인리치 필드 기록(kind/tags/embedding/story_id). 기존 필드 보존."""
        ...

    def get_open_stories(self, cutoff) -> list[dict]:
        """status=open이고 last_seen>=cutoff인 스토리: [{'id','centroid'}]. centroid=sum/count."""
        ...
    def create_story(self, story_id, *, title, vec, member_id, entities, now) -> None:
        """새 스토리: centroid_sum=vec, count=1, member_ids=[member_id], status=open."""
        ...
    def append_to_story(self, story_id, *, vec, member_id, entities, now) -> None:
        """centroid_sum+=vec, count+=1, member_ids+=member_id, entities합집합, last_seen=now."""
        ...
    def close_stale_stories(self, cutoff) -> int:
        """last_seen<cutoff인 open 스토리를 closed로. 변경 수 반환."""
        ...
