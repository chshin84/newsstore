"""클러스터링 경계 어댑터 — newsstore 데이터(RawItem/스토리 dict) ↔ clustering Article/Story
매핑 + embed·llm 주입. 알고리즘은 clustering.py 소유(여기엔 로직 없음)."""
from __future__ import annotations

from .clustering import EventClusterer
from .clustering_types import Article, Story
from ..contracts.models import RawItem
from ..contracts.ports import LLMClient


def build_clusterer(client: LLMClient) -> EventClusterer:
    def embed(texts: list[str]) -> list[list[float]]:
        return [client.embed(t) for t in texts]
    return EventClusterer(embed=embed, llm=client)


def to_article(item: RawItem, vec) -> Article:
    return Article(id=item.id, title=item.title, body=item.body or "",
                   source=item.source, published_at=str(item.published_at or ""),
                   tags=(), embedding=tuple(vec))


def to_stories(rows) -> list[Story]:
    return [Story(id=r["id"], title=r.get("title") or "",
                  centroid_sum=tuple(r["centroid_sum"]))
            for r in rows if r.get("centroid_sum")]


def assign(clusterer: EventClusterer, item: RawItem, vec, open_stories) -> str | None:
    return clusterer.assign(to_article(item, vec), open_stories)
