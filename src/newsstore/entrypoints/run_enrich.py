from __future__ import annotations
import argparse
import logging
import os
from datetime import datetime, timezone

from ..enrich.embedder import EMBED_CONCURRENCY
from ..enrich import cluster_adapter
from ..enrich.gemini import GeminiClient, LLMError
from ..enrich.processor import (process_once, NONCLUSTER_SOURCES,
                               OPEN_WINDOW, CLOSE_AFTER)
from ..enrich.taxonomy import load_taxonomy
from ..store.factory import make_store

log = logging.getLogger("newsstore.entrypoints.run_enrich")

# 한 실행이 소비할 최대 배치 수 (비용 상한 — advisor-nonfunctional). 0 = 무제한(권장 X).
MAX_BATCHES = int(os.environ.get("NEWSSTORE_MAX_BATCHES", "1000"))


def _run_cluster(store, client, taxonomy, *, noncluster, batch, concurrency) -> dict:
    """Pass 1 — 클러스터 전용(빠름): embed(병렬) + gray-band 배정. LLM 태깅 없음.

    clusterer/open_stories를 1회 구성해 배치 간 공유(Firestore 제곱 재조회 제거).
    """
    now0 = datetime.now(timezone.utc)
    clusterer = cluster_adapter.build_clusterer(client)
    open_stories = cluster_adapter.to_stories(store.get_open_stories(now0 - OPEN_WINDOW))
    log.info("cluster pass: seeded %d open-story candidates", len(open_stories))
    totals = {"processed": 0, "stories_created": 0, "stories_joined": 0, "closed": 0}
    for _ in range(MAX_BATCHES or 1_000_000):
        now = datetime.now(timezone.utc)
        stats = process_once(store, client, taxonomy, now=now, batch=batch,
                             noncluster_sources=noncluster,
                             tag=False, clusterer=clusterer, open_stories=open_stories,
                             close=False, embed_concurrency=concurrency)
        for k in totals:
            totals[k] += stats[k]
        if stats["processed"] == 0:
            break
    totals["closed"] = store.close_stale_stories(cutoff=datetime.now(timezone.utc) - CLOSE_AFTER)
    return totals


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="newsstore Step-2 enrichment processor")
    ap.add_argument("--taxonomy", default="config/taxonomy.yaml")
    ap.add_argument("--mode", choices=["cluster", "tag", "summary", "lenses", "score"],
                    default="cluster",
                    help="cluster=embed+cluster(빠름) / summary=스토리 LLM 요약(Pass 3, 시간당) "
                         "/ lenses=토픽 렌즈 멀티라벨 분류 / score=dual score(risk/impact, Phase 3) "
                         "/ tag=스토리 태깅(폐기 예정)")
    ap.add_argument("--batch", type=int, default=50)
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=os.environ.get("NEWSSTORE_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:                       # 비밀 분리: 없으면 fail-loud (로그에 키 비노출)
        log.error("GEMINI_API_KEY not set — required for the enrichment processor")
        return 2

    taxonomy = load_taxonomy(args.taxonomy)
    kw = {}
    if os.environ.get("GEMINI_MODEL"):
        kw["model"] = os.environ["GEMINI_MODEL"]
    if os.environ.get("GEMINI_EMBED_MODEL"):
        kw["embed_model"] = os.environ["GEMINI_EMBED_MODEL"]
    client = GeminiClient(api_key, **kw)

    noncluster = (frozenset(s.strip() for s in os.environ["NEWSSTORE_NONCLUSTER_SOURCES"].split(",") if s.strip())
                  if os.environ.get("NEWSSTORE_NONCLUSTER_SOURCES") else NONCLUSTER_SOURCES)
    concurrency = int(os.environ.get("NEWSSTORE_EMBED_CONCURRENCY", EMBED_CONCURRENCY))

    with make_store() as store:                  # Firestore(에뮬레이터 or 실)
        try:
            if args.mode == "cluster":
                totals = _run_cluster(store, client, taxonomy,
                                      noncluster=noncluster, batch=args.batch,
                                      concurrency=concurrency)
            elif args.mode == "summary":
                from ..enrich.summarizer import run_summary_pass
                summary_batch = int(os.environ.get("NEWSSTORE_SUMMARY_BATCH", "10"))
                totals = run_summary_pass(store, client, limit=summary_batch,
                                          now=datetime.now(timezone.utc))
            elif args.mode == "lenses":
                from ..enrich.lens_pass import run_lens_pass
                now = datetime.now(timezone.utc)
                totals = {"classified": run_lens_pass(store, now=now, cutoff=now - OPEN_WINDOW,
                                                      client=client)}
            elif args.mode == "score":
                from ..enrich.scorer import run_score_pass
                now = datetime.now(timezone.utc)
                totals = run_score_pass(store, client, now=now, cutoff=now - OPEN_WINDOW)
            else:
                from ..enrich.tagger import tag_stories
                totals = tag_stories(store, client, taxonomy, batch=10,
                                     max_stories=MAX_BATCHES * 10 or None)
        except LLMError as e:
            log.error("enrichment aborted: %s", e)
            return 1

    log.info("%s done: %s", args.mode, totals)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
