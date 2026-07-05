"""종목 히스토리 수집 — 뉴스 언급 종목(watch 렌즈)의 Yahoo 히스토리를 stock_prices/{ticker}에 저장.

가격 앵커(run_prices)와 같은 Yahoo chart 파이프 재사용 — save만 save_stock_price로. 계속 업데이트.
v1 대상 = config/topics.yaml watch 렌즈 티커(삼성·하이닉스는 .KS, 미국 종목은 그대로).
(뉴스 entity에서 신규 티커 동적 발견은 future.)
"""
from __future__ import annotations
import argparse
import logging
import os
from urllib.parse import quote

import httpx

from ..collect.prices import PriceSymbol, run_price_pass
from ..enrich import topics as _topics
from ..store.factory import make_store

log = logging.getLogger("newsstore.entrypoints.run_stock_prices")
BASE = "https://query1.finance.yahoo.com/v8/finance/chart/"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="newsstore stock-history collector (Yahoo Finance)")
    ap.add_argument("--topics", default="config/topics.yaml")
    args = ap.parse_args(argv)
    logging.basicConfig(level=os.environ.get("NEWSSTORE_LOG_LEVEL", "INFO"),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    watch = _topics.watch_tickers(_topics.load_topics(args.topics))
    symbols = [PriceSymbol(w["ticker"], w["symbol"], w["label"]) for w in watch]
    client = httpx.Client(timeout=15.0, headers={"User-Agent": UA})

    def fetch(symbol: str) -> dict:                  # 주입 HTTP — 모듈은 파싱만
        r = client.get(f"{BASE}{quote(symbol)}", params={"range": "1mo", "interval": "1d"})
        r.raise_for_status()
        return r.json()

    delay_s = float(os.environ.get("NEWSSTORE_PRICE_DELAY_S", "1"))
    try:
        with make_store() as store:
            n = run_price_pass(store, fetch, symbols, delay_s=delay_s,
                               save=store.save_stock_price)   # stock_prices/{ticker}로
    finally:
        client.close()
    log.info("stock collect done: %d/%d saved", n, len(symbols))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
