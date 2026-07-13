"""펀더멘털 수집 엔트리포인트 — FMP 재무제표를 fundamentals/{symbol}에 저장.

FMP stable REST(헤더 apikey=FMP_API_KEY). config/fundamentals.yaml의 고정 티커에
income/balance/cashflow(period=annual, limit=5)를 취합. HTTP는 여기서만 배선하고
collect/fundamentals는 취합·오케스트레이션만 한다.
"""
from __future__ import annotations
import argparse
import logging
import os

import httpx

from ..collect.fundamentals import load_fundamental_tickers, run_fundamentals_pass
from ..store.factory import make_store

log = logging.getLogger("newsstore.entrypoints.run_fundamentals")

BASE_FMP = "https://financialmodelingprep.com/stable/"
# 저장 dict 키(statement) → FMP 엔드포인트 경로.
ENDPOINT = {"income": "income-statement",
            "balance": "balance-sheet-statement",
            "cashflow": "cash-flow-statement"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="newsstore fundamentals collector (FMP)")
    ap.add_argument("--tickers", default="config/fundamentals.yaml")
    ap.add_argument("--limit", type=int, default=5)      # 연간 재무제표 최근 N개
    args = ap.parse_args(argv)
    logging.basicConfig(level=os.environ.get("NEWSSTORE_LOG_LEVEL", "INFO"),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    api_key = os.environ["FMP_API_KEY"]              # fail-loud: 없으면 KeyError로 즉시 중단
    tickers = load_fundamental_tickers(args.tickers)
    # 비밀(apikey)은 헤더로만 실어 URL·로그에 남지 않게 한다(SECRETS).
    client = httpx.Client(timeout=30.0, headers={"apikey": api_key})

    def fetch(ticker: str, statement: str) -> list:
        r = client.get(f"{BASE_FMP}{ENDPOINT[statement]}",
                       params={"symbol": ticker, "period": "annual", "limit": args.limit})
        r.raise_for_status()
        return r.json()

    try:
        with make_store() as store:
            n = run_fundamentals_pass(store, fetch, tickers)
    finally:
        client.close()
    log.info("fundamentals collect done: %d/%d saved", n, len(tickers))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
