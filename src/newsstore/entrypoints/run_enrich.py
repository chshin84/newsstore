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

# 한 실행이 소비할 최대 배치 수 (비용 상한 — advisor-nonfunctional).
# 0 = 사실상 무제한(권장 X) — 아래 UNBOUNDED_BATCH_CAP를 내부 안전 천장으로 사용.
MAX_BATCHES = int(os.environ.get("NEWSSTORE_MAX_BATCHES", "1000"))
UNBOUNDED_BATCH_CAP = 1_000_000   # MAX_BATCHES=0(무제한) 시 폭주 방지 안전 상한


def _run_cluster(store, client, taxonomy, *, noncluster, batch, concurrency) -> dict:
    """Pass 1 — 클러스터 전용(빠름): embed(병렬) + gray-band 배정. LLM 태깅 없음.

    clusterer는 1회 구성해 공유하되, open_stories는 **배치마다 재읽기** — 앞 배치의
    합류로 커진 centroid_sum을 다음 배치 배정이 봐야 한다(processor의 '다음 배치
    재읽기' 계약 이행 — 실행 전체 공유는 다배치 백필에서 stale centroid 파편화를 냈다).
    배치 내부 공유는 유지되므로 아이템 단위 제곱 재조회는 없다.
    """
    clusterer = cluster_adapter.build_clusterer(client)
    totals = {"processed": 0, "stories_created": 0, "stories_joined": 0, "closed": 0}
    for i in range(MAX_BATCHES or UNBOUNDED_BATCH_CAP):
        now = datetime.now(timezone.utc)
        open_stories = cluster_adapter.to_stories(store.get_open_stories(now - OPEN_WINDOW))
        if i == 0:
            log.info("cluster pass: seeded %d open-story candidates", len(open_stories))
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
    ap.add_argument("--mode", choices=["cluster", "summary", "lenses", "score", "article", "report"],
                    default="cluster",
                    help="cluster=embed+cluster(빠름) / summary=스토리 LLM 요약(Pass 3, 시간당) "
                         "/ lenses=토픽 렌즈 멀티라벨 분류 / score=dual score(risk/impact) / article=보고서 생성"
                         " / report=프레임+데일리 리포트(스펙 2026-06-30)")
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
                from ..enrich import topics as _topics
                now = datetime.now(timezone.utc)
                store.set_meta("lenses", _topics.lens_labels(_topics.load_topics()))  # UI 렌즈 라벨 발행(SSOT)
                totals = {"classified": run_lens_pass(store, now=now, cutoff=now - OPEN_WINDOW,
                                                      client=client)}
            elif args.mode == "score":
                from ..enrich.scorer import run_score_pass
                now = datetime.now(timezone.utc)
                totals = run_score_pass(store, client, now=now, cutoff=now - OPEN_WINDOW)
            elif args.mode == "article":
                from ..enrich.article import run_article_pass
                now = datetime.now(timezone.utc)
                totals = run_article_pass(store, client, now=now, cutoff=now - OPEN_WINDOW)
            elif args.mode == "report":
                # 분기 내부에서 함수를 직접 임포트하지 않고 모듈 경유로 호출한다
                # (테스트의 monkeypatch.setattr("newsstore.enrich.frames.run_frame_pass", ...)가 먹도록).
                from ..enrich import frames as _frames, report as _report
                from ..enrich import topics as _topics
                now = datetime.now(timezone.utc)
                t = _topics.load_topics()
                # UI 앵커(SSOT 발행) — Firestore map은 키가 정렬돼 그룹 순서를 잃으므로
                # 순서 보존 배열([{name, lens_ids}])로 발행한다(m1).
                store.set_meta("report_groups",
                               {"groups": [{"name": g, "lens_ids": ids}
                                           for g, ids in _topics.report_groups(t).items()]})
                lens_ids = _topics.report_lens_ids(t)             # 리포트=자산(standing)만
                context_ids = _topics.context_lens_ids(t)         # 시장프레임·백드롭 입력(비자산 포함)
                # 렌즈별 실제 가격 컨텍스트(뉴스 지연 보정 교차검증) — 가격키 매핑된 렌즈만.
                # price_ctx=프롬프트 주입용 포맷 문자열 / price_map=divergence 배지(A1)용 원 가격(series·pct).
                price_ctx, price_map = {}, {}
                for lid in lens_ids:
                    pk = _topics.price_key_for(t, lid)
                    if pk:
                        price_doc = store.get_price(pk)
                        ctx = _report.price_context(price_doc)
                        if ctx:
                            price_ctx[lid] = ctx
                        if price_doc:
                            price_map[lid] = {"key": pk, "doc": price_doc}
                _frames.run_frame_pass(store, client, lens_ids=lens_ids, now=now,   # 선행(§4)
                                       context_lens_ids=context_ids)
                totals = _report.run_report_pass(store, client, lens_ids=lens_ids, now=now,
                                                 context_lens_ids=context_ids,
                                                 price_ctx_by_lens=price_ctx,
                                                 price_by_lens=price_map)
        except LLMError as e:
            log.error("enrichment aborted: %s", e)
            return 1

    log.info("%s done: %s", args.mode, totals)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
