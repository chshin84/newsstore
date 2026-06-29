"""클러스터링 계약 타입 — news-analytics @249aa3d에서 이식(2026-06-29).

순수 데이터 + 인터페이스만. 구현·저장·LLM 호출은 여기 없다(DI). 소비 측(processor/어댑터)이
Article/Story를 채워 넣고 결과를 받는다. 임베딩은 런타임에 주입된다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Sequence


@dataclass(frozen=True)
class Article:
    id: str
    title: str
    body: str
    source: str
    published_at: str                     # ISO8601
    tags: tuple[str, ...] = ()
    embedding: tuple[float, ...] | None = None   # 런타임 주입(fixture엔 없음)


@dataclass(frozen=True)
class Story:
    """사건 클러스터. 필드명은 newsstore Firestore `stories` 스키마와 일치(어댑터 1:1 매핑).

    수명주기: 생성 시 status='open' → 멤버 합류 시 last_seen 갱신 →
    last_seen < now-CLOSE_AFTER(24h)면 'closed'. 매칭 후보창 OPEN_WINDOW=48h.
    """
    id: str
    title: str
    member_ids: tuple[str, ...] = field(default_factory=tuple)
    entities: tuple[str, ...] = field(default_factory=tuple)
    status: str = "open"                   # 'open' | 'closed'
    count: int = 0
    first_seen: str = ""                   # ISO8601
    last_seen: str = ""                    # ISO8601
    centroid_sum: tuple[float, ...] | None = None   # 멤버 임베딩 합(centroid=합/count). 온라인
    #                                                 assign의 유사도 기준. 코사인은 스케일 불변이라
    #                                                 합을 그대로 써도 centroid와 동일(런타임 주입).


class LLMClient(Protocol):
    """주입되는 LLM 클라이언트. 유닛 테스트는 가짜(FakeLLM), 운영은 실제 Gemini."""

    def complete(self, prompt: str) -> str: ...


class Clusterer(Protocol):
    """기사를 기존 스토리에 배정하거나 새 스토리를 연다(온라인). story_id 또는 None 반환.

    의존(embed·llm)은 **생성자 주입** — assign엔 인자로 받지 않는다.
    """

    def assign(self, article: Article, open_stories: Sequence[Story]) -> str | None: ...
