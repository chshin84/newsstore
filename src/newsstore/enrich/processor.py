from __future__ import annotations
import logging
import uuid
from datetime import datetime, timedelta

from .classify import classify_kind
from .cluster import assign, DEFAULT_THRESHOLD
from .embedder import embed_items
from .llm import LLMClient
from .tagger import tag_items

log = logging.getLogger("newsstore.enrich.processor")

OPEN_WINDOW = timedelta(hours=48)     # 비교 대상 '열린 스토리' 시간창 (spec §7)
CLOSE_AFTER = timedelta(hours=24)     # 무활동 시 close


def _flat_tags(tg: dict) -> list[str]:
    """저장용 평탄 태그 = tickers + entities + topics (뷰 드롭다운/필터)."""
    return list(tg["tickers"]) + list(tg["entities"]) + list(tg["topics"])


def process_once(store, client: LLMClient, taxonomy: dict, *, now: datetime,
                 batch: int = 10, open_window: timedelta = OPEN_WINDOW,
                 close_after: timedelta = CLOSE_AFTER,
                 threshold: float = DEFAULT_THRESHOLD, id_factory=None) -> dict:
    """get_unprocessed 한 배치 처리: classify → (story만) tag+embed → centroid 클러스터 →
    save_enrichment + mark_processed → close_stale. 비파괴(원본 보존, kind로 분류만).

    벡터/LLM은 주입 client. story_id는 Processor 책임(uuid4) — Store 계약 아님.
    """
    id_factory = id_factory or (lambda: uuid.uuid4().hex)
    items = store.get_unprocessed(limit=batch)
    if not items:
        return {"processed": 0, "stories_created": 0, "stories_joined": 0, "closed": 0}

    # 1. 선필터(kind) — 비파괴
    kinds = {it.id: classify_kind(it.title, it.body or "") for it in items}
    story_items = [it for it in items if kinds[it.id] == "story"]

    # 2. 태깅 + 임베딩 (kind=story만)
    tags_by_id: dict[str, dict] = {}
    vec_by_id: dict[str, list[float]] = {}
    if story_items:
        tags = tag_items(story_items, client, taxonomy, batch=batch)
        vecs = embed_items(story_items, client)
        for it, tg, vc in zip(story_items, tags, vecs):
            tags_by_id[it.id] = tg
            vec_by_id[it.id] = vc

    created = joined = 0
    # 3. centroid 클러스터 (열린 스토리 매 항목 재조회 → 같은 배치 내 합류 가능)
    for it in story_items:
        vec = vec_by_id[it.id]
        tg = tags_by_id[it.id]
        entities = _flat_tags(tg)
        sid = assign(vec, store.get_open_stories(cutoff=now - open_window), threshold=threshold)
        if sid is None:
            sid = id_factory()
            store.create_story(sid, title=it.title, vec=vec, member_id=it.id,
                               entities=entities, now=now)
            created += 1
        else:
            store.append_to_story(sid, vec=vec, member_id=it.id, entities=entities, now=now)
            joined += 1
        store.save_enrichment(it.id, kind="story", tags=_flat_tags(tg),
                              embedding=vec, story_id=sid)

    # 4. spam/digest — kind만 기록(임베딩/스토리 없음)
    for it in items:
        if kinds[it.id] != "story":
            store.save_enrichment(it.id, kind=kinds[it.id], tags=[],
                                  embedding=None, story_id=None)

    # 5. 큐에서 제거
    store.mark_processed([it.id for it in items], processed_at=now)

    # 6. 무활동 스토리 마감
    closed = store.close_stale_stories(cutoff=now - close_after)

    stats = {"processed": len(items), "stories_created": created,
             "stories_joined": joined, "closed": closed}
    log.info("process_once: %s", stats)
    return stats
