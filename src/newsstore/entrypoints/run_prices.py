"""가격 수집 엔트리포인트 — Yahoo Finance chart API로 config/prices.yaml 심볼을 prices/{key}에 저장.

Yahoo chart API는 무키(User-Agent만 필요). 한 콜로 현재값 + 등락 + 30일 시계열(차트).
"""
from __future__ import annotations
import argparse
import logging
import os
from urllib.parse import quote

import httpx

from ..collect.prices import load_price_symbols, run_price_pass
from ..store.factory import make_store

log = logging.getLogger("newsstore.entrypoints.run_prices")
BASE = "https://query1.finance.yahoo.com/v8/finance/chart/"
# Yahoo는 기본 UA를 차단 — 브라우저 UA 필요(뉴스 fetcher와 동일 관행).
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="newsstore price collector (Yahoo Finance)")
    ap.add_argument("--symbols", default="config/prices.yaml")
    args = ap.parse_args(argv)
    logging.basicConfig(level=os.environ.get("NEWSSTORE_LOG_LEVEL", "INFO"),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    symbols = load_price_symbols(args.symbols)
    client = httpx.Client(timeout=15.0, headers={"User-Agent": UA})

    def fetch(symbol: str) -> dict:                  # 주입 HTTP — 모듈은 파싱만
        r = client.get(f"{BASE}{quote(symbol)}",
                       params={"range": "1mo", "interval": "1d"})
        r.raise_for_status()
        return r.json()

    # Yahoo throttle 대응 — 콜 간 지연(env, 기본 1s). 심볼 수 적어 하한만.
    delay_s = float(os.environ.get("NEWSSTORE_PRICE_DELAY_S", "1"))
    try:
        with make_store() as store:
            n = run_price_pass(store, fetch, symbols, delay_s=delay_s)
    finally:
        client.close()
    log.info("price collect done: %d/%d saved", n, len(symbols))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
