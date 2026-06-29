from __future__ import annotations
import logging
import uuid
from datetime import datetime, timedelta

from .classify import classify_kind
from .embedder import embed_items, embed_text, EMBED_CONCURRENCY
from . import cluster_adapter
from .clustering_types import Story
from ..contracts.ports import LLMClient
from .tagger import tag_items

_EMPTY_TAGS = {"tickers": [], "entities": [], "topics": []}

log = logging.getLogger("newsstore.enrich.processor")

OPEN_WINDOW = timedelta(hours=48)     # 비교 대상 '열린 스토리' 시간창 (spec §7)
CLOSE_AFTER = timedelta(hours=24)     # 무활동 시 close
MIN_EMBED_CHARS = 40                  # 이보다 얇으면 임베딩/클러스터 제외(노이즈 클러스터 방지; 실데이터 측정)
# 내러티브 소스가 아닌 곳(보일러플레이트 제목/본문이라 스타일로 오병합) — 태그만, 클러스터 제외.
NONCLUSTER_SOURCES = frozenset({"TruthSocial"})


def _flat_tags(tg: dict) -> list[str]:
    """저장용 평탄 태그 = tickers + entities + topics (뷰 드롭다운/필터)."""
    return list(tg["tickers"]) + list(tg["entities"]) + list(tg["topics"])


def process_once(store, client: LLMClient, taxonomy: dict, *, now: datetime,
                 batch: int = 10, open_window: timedelta = OPEN_WINDOW,
                 close_after: timedelta = CLOSE_AFTER,
                 noncluster_sources=NONCLUSTER_SOURCES,
                 tag: bool = True, clusterer=None, open_stories: list | None = None,
                 close: bool = True,
                 embed_concurrency: int = EMBED_CONCURRENCY, id_factory=None) -> dict:
    """get_unprocessed 한 배치: classify → (story만) embed(병렬) → centroid 클러스터 →
    save_enrichment + mark_processed → close_stale. 비파괴.

    - tag=False: LLM 태깅 생략(클러스터 전용 패스, 빠름). 스토리 의미 라벨링은 별도 lenses 패스가 담당.
    - index: VectorIndex(최근접 검색). 안 주면 배치당 1회 store에서 InMemory 인덱스를 구성
      (per-item Firestore 재조회 제거). 풀런은 run_enrich가 인덱스를 1회 만들어 배치 간 공유.
    """
    id_factory = id_factory or (lambda: uuid.uuid4().hex)
    items = store.get_unprocessed(limit=batch)
    if not items:
        return {"processed": 0, "stories_created": 0, "stories_joined": 0, "closed": 0}
    if clusterer is None:
        clusterer = cluster_adapter.build_clusterer(client)
    if open_stories is None:
        open_stories = cluster_adapter.to_stories(store.get_open_stories(now - open_window))

    kinds = {it.id: classify_kind(it.title, it.body or "") for it in items}
    story_items = [it for it in items if kinds[it.id] == "story"]

    tags_by_id: dict[str, dict] = {}
    vec_by_id: dict[str, list[float]] = {}
    if story_items:
        if tag:
            for it, tg in zip(story_items, tag_items(story_items, client, taxonomy, batch=batch)):
                tags_by_id[it.id] = tg
        else:
            for it in story_items:
                tags_by_id[it.id] = _EMPTY_TAGS
        embeddable = [it for it in story_items
                      if it.source not in noncluster_sources
                      and len(embed_text(it)) >= MIN_EMBED_CHARS]
        for it, vc in zip(embeddable, embed_items(embeddable, client, concurrency=embed_concurrency)):
            vec_by_id[it.id] = vc

    created = joined = 0
    for it in story_items:
        tg = tags_by_id[it.id]
        vec = vec_by_id.get(it.id)
        if vec is None:                       # 얇은/비내러티브: 태그만, 클러스터 제외(standalone)
            store.save_enrichment(it.id, kind="story", tags=_flat_tags(tg),
                                  embedding=None, story_id=None)
            continue
        entities = _flat_tags(tg)
        sid, is_new = _assign_and_persist(store, clusterer, open_stories, it, vec,
                                          entities, now, id_factory)
        if is_new:
            created += 1
        else:
            joined += 1
        store.save_enrichment(it.id, kind="story", tags=_flat_tags(tg),
                              embedding=vec, story_id=sid)

    for it in items:                          # spam/digest — kind만
        if kinds[it.id] != "story":
            store.save_enrichment(it.id, kind=kinds[it.id], tags=[],
                                  embedding=None, story_id=None)

    store.mark_processed([it.id for it in items], processed_at=now)
    closed = store.close_stale_stories(cutoff=now - close_after) if close else 0
    stats = {"processed": len(items), "stories_created": created,
             "stories_joined": joined, "closed": closed}
    log.info("process_once: %s", stats)
    return stats


def _assign_and_persist(store, clusterer, open_stories, it, vec, entities, now,
                        id_factory) -> tuple[str, bool]:
    """gray-band 클러스터러로 스토리 배정 + store 영속화 + 배치 내 open_stories 갱신.
    반환 (story_id, is_new)."""
    sid = cluster_adapter.assign(clusterer, it, vec, open_stories)
    if sid is None:
        sid = id_factory()
        store.create_story(sid, title=it.title, vec=vec, member_id=it.id,
                           entities=entities, now=now)
        # 같은 배치의 후속 기사가 이 신규 스토리를 후보로 보게(배치 내 가시성).
        open_stories.append(Story(id=sid, title=it.title, centroid_sum=tuple(vec)))
        return sid, True
    store.append_to_story(sid, vec=vec, member_id=it.id, entities=entities, now=now)
    # 합류 스토리의 centroid_sum 배치 내 갱신은 v1 미적용(다음 배치 재읽기로 반영).
    return sid, False
