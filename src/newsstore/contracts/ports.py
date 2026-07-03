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


class Development(TypedDict, total=False):
    """스토리 전개 1건(요약 패스 산출). 키는 추가적(레거시 안전)이라 total=False."""
    text: str
    time: datetime
    source_count: int
    delta_time: datetime
    event_time: datetime | None


class OpenStory(TypedDict):
    """get_open_stories 반환: 클러스터 후보(centroid_sum=원본 합, centroid=합/count)."""
    id: str
    title: str
    centroid_sum: list[float]
    centroid: list[float]
    count: int


class LensingStory(TypedDict):
    """get_stories_for_lensing 반환."""
    id: str
    title: str
    member_ids: list[str]
    lenses: list[str]
    count: int


class MemberSignals(TypedDict):
    """get_story_member_signals 반환: 멤버 기사 분류 신호 배치 집계."""
    asset_hints: list[str]
    languages: list[str]
    tags: list[str]
    keyword_text: str


class SummaryCandidate(TypedDict):
    """get_stories_needing_summary 반환."""
    id: str
    count: int
    developments: list[Development]


class StoryMember(TypedDict):
    """get_story_members 반환: 멤버 기사 발췌."""
    title: str
    body: str
    source: str
    published_at: datetime | None


class ScoringStory(TypedDict, total=False):
    """get_stories_for_scoring 반환(요약/렌즈 결측 가능 → total=False)."""
    id: str
    title: str
    count: int
    lenses: list[str]
    summary: str
    developments: list[Development]


class ArticleStory(TypedDict, total=False):
    """get_stories_for_article 반환(점수/ref 결측 가능 → total=False)."""
    id: str
    title: str
    count: int
    lenses: list[str]
    summary: str
    developments: list[Development]
    risk: int
    impact: int
    risk_ref: int
    impact_ref: int
    score_ref_at: datetime
    first_seen: datetime


class FramePole(TypedDict):
    """프레임 극 1개. id는 리포트 섹션이 pole_id로 인용(결정론 실재 검증용)."""
    id: str
    text: str


class Frame(TypedDict, total=False):
    """frames/{lens_id} — 프레임 패스 단독 writer(스펙 §3·§6). 3축, 축당 ≤FRAME_MAX_POLES."""
    risks: list[FramePole]
    premiums: list[FramePole]
    watchpoints: list[FramePole]
    updated_at: datetime


class ReportStory(TypedDict, total=False):
    """get_stories_for_report 반환 — 리포트 입력 후보(open·72h·해당 렌즈)."""
    id: str
    title: str
    summary: str
    lenses: list[str]
    risk: int
    impact: int
    count: int
    developments: list[Development]
    last_seen: datetime          # 랭킹 폴백(developments 없는 스토리 — story_rank)


class Store(Protocol):
    def upsert_items(self, items: list[RawItem]) -> int:
        """Insert items, skipping ids already present. Returns count of NEW items."""
        ...
    def get_feed_state(self, feed_id: str) -> FeedState:
        """Return {} or {'etag','last_modified','last_fetched'(datetime)}."""
        ...
    def set_feed_state(self, feed_id: str, **fields) -> None: ...
    def count(self) -> int: ...

    # Step-2 hand-off contract. The store backend (Firestore) must
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

    def save_enrichment(self, item_id: str, *, kind: str, tags: list[str],
                        embedding: list[float] | None, story_id: str | None) -> None:
        """기사에 Step-2 인리치 필드 기록(kind/tags/embedding/story_id). 기존 필드 보존."""
        ...

    def get_open_stories(self, cutoff: datetime) -> list[OpenStory]:
        """status=open이고 last_seen>=cutoff인 스토리."""
        ...
    def create_story(self, story_id: str, *, title: str, vec: list[float], member_id: str,
                     entities: list[str], now: datetime) -> None:
        """새 스토리: centroid_sum=vec, count=1, member_ids=[member_id], status=open."""
        ...
    def append_to_story(self, story_id: str, *, vec: list[float], member_id: str,
                        entities: list[str], now: datetime) -> None:
        """centroid_sum+=vec, count+=1, member_ids+=member_id, entities합집합, last_seen=now."""
        ...
    def close_stale_stories(self, cutoff: datetime) -> int:
        """last_seen<cutoff인 open 스토리를 closed로. 변경 수 반환."""
        ...

    # Phase 1 토픽 렌즈 분류 계약.
    def save_story_lenses(self, story_id: str, lenses: list[str],
                          count: int | None = None) -> None:
        """stories.lenses[](렌즈 id 배열) merge 저장(비파괴). +lensed_count=count
        (incremental 가드 — save_story_score·save_story_article과 동일 컨벤션)."""
        ...
    def get_stories_for_lensing(self, cutoff: datetime) -> list[LensingStory]:
        """status=open·last_seen>=cutoff 스토리."""
        ...
    def get_story_member_signals(self, member_ids: list[str]) -> MemberSignals:
        """멤버 기사 분류 신호 배치 집계."""
        ...

    # Step-3 요약 패스 계약 (플랜 A). 새 멤버가 생긴 스토리를 골라 LLM 요약을 채운다.
    def get_stories_needing_summary(self, limit: int) -> list[SummaryCandidate]:
        """last_seen desc 상위 limit개 중 count>summary_count(새 멤버)인 것만."""
        ...
    def get_story_members(self, story_id: str) -> list[StoryMember]:
        """story_id 멤버 기사 published_at asc."""
        ...
    def save_story_summary(self, story_id, *, title, summary, latest, developments,
                           summary_count, now) -> None:
        """요약 필드만 merge 저장(+summary_count, summary_at=now). 기존 필드(member_ids 등) 보존."""
        ...

    # Phase 3 dual score 패스 계약. 게이트 후 risk/impact를 매겨 비파괴 저장한다.
    def get_stories_for_scoring(self, cutoff: datetime) -> list[ScoringStory]:
        """status=open·last_seen>=cutoff·count>scored_count(incremental) 스토리."""
        ...
    def save_story_score(self, story_id, *, risk, impact, risk_reason, impact_reason,
                         count=None, now=None) -> None:
        """점수 필드만 merge 저장(+scored_count=count, scored_at=now). 기존 필드 보존(비파괴)."""
        ...

    # Phase 4 아티클 생성 패스 계약. headline/lead/article + 전일대비 ref를 비파괴 저장(developments 불간섭).
    def get_stories_for_article(self, cutoff: datetime) -> list[ArticleStory]:
        """status=open·last_seen>=cutoff·count>articled_count(incremental) 스토리."""
        ...
    def save_story_article(self, story_id, *, headline, lead, article,
                           risk_ref=None, impact_ref=None, score_ref_at=None,
                           count=None, now=None) -> None:
        """헤드라인/리드/아티클 + ref만 merge 저장(+articled_count=count, articled_at=now).
        developments는 안 씀(summary 단독 writer) — 기존 필드 보존(비파괴 by construction)."""
        ...

    # 리포트 탭(v1, 스펙 2026-06-30) — frames/reports 계약.
    def get_frame(self, lens_id: str) -> Frame:
        """frames/{lens_id}. 없으면 {}(첫 런)."""
        ...
    def save_frame(self, lens_id: str, frame: Frame, *, now: datetime) -> None:
        """frames/{lens_id} 통째 set(전량 재심 산출물) + 이전 판을
        frames_history/{lens_id}/snapshots/{ISO date}에 스냅샷(additive — 스펙 §6)."""
        ...
    def get_stories_for_report(self, lens_id: str, cutoff: datetime) -> list[ReportStory]:
        """status=open·last_seen>=cutoff·lenses∋lens_id. 전수 스캔+클라 필터(타 패스 패턴)."""
        ...
    def save_report(self, doc_id: str, report: dict) -> None:
        """reports/{doc_id} 통째 set(per-run 전량 재생성 — 스펙 §6). _backdrop·rising 포함."""
        ...
    def get_report(self, doc_id: str) -> dict:
        """reports/{doc_id}. 없으면 {}."""
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
