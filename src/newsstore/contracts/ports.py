from __future__ import annotations
from datetime import datetime
from typing import Protocol
from .models import RawItem


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

    def filter_new_ids(self, ids: list[str]) -> list[str]:
        """`items`에 아직 없는 id만(입력 순서 보존)."""
        ...

    def set_meta(self, key: str, value: dict) -> None:
        """Write a small public-read metadata doc for the site (e.g. 'sources')."""
        ...

    def save_enrichment(self, item_id, *, kind, tags, embedding, story_id) -> None:
        """기사에 Step-2 인리치 필드 기록(kind/tags/embedding/story_id). 기존 필드 보존."""
        ...

    def get_open_stories(self, cutoff) -> list[dict]:
        """status=open이고 last_seen>=cutoff인 스토리:
        [{'id','title','centroid_sum'(원본 합),'centroid'(=합/count),'count'}]."""
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

    # Phase 1 토픽 렌즈 분류 계약.
    def save_story_lenses(self, story_id, lenses: list) -> None:
        """stories.lenses[](렌즈 id 배열) merge 저장(비파괴)."""
        ...
    def get_stories_for_lensing(self, cutoff) -> list[dict]:
        """status=open·last_seen>=cutoff 스토리: [{'id','title','member_ids','lenses'}]."""
        ...
    def get_story_member_signals(self, member_ids: list) -> dict:
        """멤버 기사 분류 신호 배치 집계: {'asset_hints','languages','tags','keyword_text'}."""
        ...

    # Step-3 요약 패스 계약 (플랜 A). 새 멤버가 생긴 스토리를 골라 LLM 요약을 채운다.
    def get_stories_needing_summary(self, limit: int) -> list[dict]:
        """last_seen desc 상위 limit개 중 count>summary_count(새 멤버)인 것만.
        [{'id','count','developments'(prior 델타, delta_time 포함 가능)}]."""
        ...
    def get_story_members(self, story_id: str) -> list[dict]:
        """story_id 멤버 기사 published_at asc. [{'title','body','source','published_at'}]."""
        ...
    def save_story_summary(self, story_id, *, title, summary, latest, developments,
                           summary_count, now) -> None:
        """요약 필드만 merge 저장(+summary_count, summary_at=now). 기존 필드(member_ids 등) 보존."""
        ...


class LLMClient(Protocol):
    def generate_json(self, prompt: str, *, timeout: float) -> dict: ...
    def embed(self, text: str, *, timeout: float) -> list[float]: ...
    def complete(self, prompt: str, *, timeout: float) -> str: ...


class VectorIndex(Protocol):
    """열린 스토리 중심핵에 대한 최근접 검색 + 증분 갱신.
    InMemory(브루트포스) / 미래 Firestore find_nearest 가 같은 계약을 구현."""
    def nearest(self, vec: list[float], *, threshold: float) -> str | None: ...
    def add_story(self, story_id: str, vec: list[float]) -> None: ...
    def add_member(self, story_id: str, vec: list[float]) -> None: ...
