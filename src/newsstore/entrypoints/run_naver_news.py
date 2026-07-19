"""네이버 검색 뉴스 수집 엔트리포인트 — 키워드별 한국 뉴스를 items에 적재.

HTTP는 여기서만 배선(헤더 X-Naver-Client-Id/Secret=env 비밀). collect/naver_news가 매핑·오케스트레이션.
"""
from __future__ import annotations
import argparse, logging, os
from datetime import datetime, timezone
import httpx

from ..collect.naver_news import load_naver_config, run_naver_pass
from ..store.factory import make_store

log = logging.getLogger("newsstore.entrypoints.run_naver_news")

NAVER_NEWS_URL = "https://openapi.naver.com/v1/search/news.json"


def build_fetch(client, display: int):
    """쿼리 → 검색 뉴스 GET. 인증은 client 헤더에만(params·URL·로그에 비밀 금지, SECRETS).
    sort=date로 최신순 — 매 패스 고정 window 재스캔(멱등 URL 중복제거는 store가 담당)."""
    def fetch(query):
        r = client.get(NAVER_NEWS_URL, params={"query": query, "display": display, "sort": "date"})
        r.raise_for_status()
        return (r.json() or {}).get("items") or []
    return fetch


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="newsstore Naver news collector")
    ap.add_argument("--config", default="config/naver_news.yaml")
    args = ap.parse_args(argv)
    logging.basicConfig(level=os.environ.get("NEWSSTORE_LOG_LEVEL", "INFO"),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    client_id = os.environ["NAVER_CLIENT_ID"]          # fail-loud
    client_secret = os.environ["NAVER_CLIENT_SECRET"]  # fail-loud
    cfg = load_naver_config(args.config)
    delay_s = float(os.environ.get("NEWSSTORE_NEWS_DELAY_S", "0.2"))
    client = httpx.Client(timeout=30.0, headers={
        "X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret})
    fetch = build_fetch(client, cfg["display"])
    try:
        with make_store() as store:
            summary = run_naver_pass(
                store, fetch, cfg["queries"], now=datetime.now(timezone.utc),
                poll_minutes=cfg["poll_minutes"], delay_s=delay_s)
    finally:
        client.close()
    total = sum(v for v in summary.values() if v > 0)
    log.info("naver news collect done: %d new item(s) across %d query(ies): %s",
             total, len(summary), summary)     # summary는 카운트만 — 비밀·본문 없음
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
