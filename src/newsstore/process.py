from __future__ import annotations
import argparse
import logging
import os
from datetime import datetime, timezone

from .enrich.cluster import DEFAULT_THRESHOLD
from .enrich.llm import GeminiClient, LLMError
from .enrich.processor import process_once
from .enrich.taxonomy import load_taxonomy
from .store.factory import make_store

log = logging.getLogger("newsstore.process")

# 한 실행이 소비할 최대 배치 수 (비용 상한 — advisor-nonfunctional). 큐가 더 길면
# 다음 Scheduler 틱이 이어 처리. 0 = 무제한(권장 X).
MAX_BATCHES = int(os.environ.get("NEWSSTORE_MAX_BATCHES", "20"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="newsstore Step-2 enrichment processor (one pass)")
    ap.add_argument("--db", default=os.environ.get("NEWSSTORE_DB", "data/newsstore.db"))
    ap.add_argument("--taxonomy", default="config/taxonomy.yaml")
    ap.add_argument("--batch", type=int, default=10)
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=os.environ.get("NEWSSTORE_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:                       # 비밀 분리: 없으면 fail-loud (로그에 키 비노출)
        log.error("GEMINI_API_KEY not set — required for the enrichment processor")
        return 2

    backend = os.environ.get("NEWSSTORE_BACKEND", "sqlite").lower()
    if backend == "sqlite":
        os.makedirs(os.path.dirname(args.db) or ".", exist_ok=True)
    taxonomy = load_taxonomy(args.taxonomy)
    kw = {}
    if os.environ.get("GEMINI_MODEL"):
        kw["model"] = os.environ["GEMINI_MODEL"]
    if os.environ.get("GEMINI_EMBED_MODEL"):
        kw["embed_model"] = os.environ["GEMINI_EMBED_MODEL"]
    client = GeminiClient(api_key, **kw)

    threshold = float(os.environ.get("NEWSSTORE_CLUSTER_THRESHOLD", DEFAULT_THRESHOLD))
    totals = {"processed": 0, "stories_created": 0, "stories_joined": 0, "closed": 0}
    with make_store(backend, db_path=args.db) as store:
        for _ in range(MAX_BATCHES or 1_000_000):
            now = datetime.now(timezone.utc)
            try:
                stats = process_once(store, client, taxonomy, now=now,
                                     batch=args.batch, threshold=threshold)
            except LLMError as e:          # 구조화 에러 → 런 실패로 표면화
                log.error("enrichment aborted: %s", e)
                return 1
            for k in totals:
                totals[k] += stats[k]
            if stats["processed"] == 0:
                break

    log.info("enrichment done: %s", totals)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
