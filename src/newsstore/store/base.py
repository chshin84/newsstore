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
