"""FMP 뉴스 수집 엔트리포인트 — 6종 파이어호스를 고정 lookback으로 재스캔해 items에 적재.

HTTP는 여기서만 배선(헤더 apikey=FMP_API_KEY). collect/fmp_news가 매핑·오케스트레이션.
"""
from __future__ import annotations
import argparse, logging, os
from datetime import datetime, timezone
import httpx

from ..collect.fmp_news import load_fmp_news_config, run_fmp_news_pass, PAGE_LIMIT
from ..store.factory import make_store

log = logging.getLogger("newsstore.entrypoints.run_fmp_news")

BASE_NEWS = "https://financialmodelingprep.com/stable/news/"
BASE_ARTICLES = "https://financialmodelingprep.com/stable/fmp-articles"

def build_fetchers(client, endpoints: list[str]) -> dict:
    """엔드포인트별 GET 함수. -latest는 from/to 지원, fmp-articles는 page/limit만.
    apikey는 client 헤더에만 — params·URL에 넣지 않는다(SECRETS)."""
    def make(ep):
        def fetch(frm, to, page):
            if ep == "fmp-articles":
                r = client.get(BASE_ARTICLES, params={"limit": PAGE_LIMIT, "page": page})
            else:
                r = client.get(f"{BASE_NEWS}{ep}",
                               params={"from": frm, "to": to, "limit": PAGE_LIMIT, "page": page})
            r.raise_for_status()
            return r.json() or []
        return fetch
    return {ep: make(ep) for ep in endpoints}

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="newsstore FMP news collector")
    ap.add_argument("--config", default="config/fmp_news.yaml")
    args = ap.parse_args(argv)
    logging.basicConfig(level=os.environ.get("NEWSSTORE_LOG_LEVEL", "INFO"),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    api_key = os.environ["FMP_API_KEY"]          # fail-loud
    cfg = load_fmp_news_config(args.config)
    delay_s = float(os.environ.get("NEWSSTORE_NEWS_DELAY_S", "0.2"))
    client = httpx.Client(timeout=30.0, headers={"apikey": api_key})
    fetchers = build_fetchers(client, cfg["endpoints"])
    try:
        with make_store() as store:
            summary = run_fmp_news_pass(
                store, fetchers, cfg["endpoints"], now=datetime.now(timezone.utc),
                lookback_days=cfg["lookback_days"],
                blackout_start_hour=cfg["blackout_start_hour"], blackout_end_hour=cfg["blackout_end_hour"],
                delay_s=delay_s)
    finally:
        client.close()
    total = sum(v for v in summary.values() if v > 0)
    log.info("fmp news collect done: %d new item(s) across %d endpoint(s): %s",
             total, len(summary), summary)     # summary는 카운트만 — 비밀·본문 없음
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
