"""가격 수집 엔트리포인트 — FMP + Yahoo 하이브리드로 config/prices.yaml 심볼의 5분봉을 수집.

5분봉 스트림을 price_bars/에 적재(새 바만)하고, prices/{key}에 최신 스냅샷을 갱신(웹 확인용).
주 소스는 FMP stable REST(헤더 apikey=FMP_API_KEY). FMP Premium 미커버 3종(kosdaq·dxy·wti)만
Yahoo Finance chart(interval=5m, 무키·UA)로 폴백. 미국채 수익률은 5분봉이 없어 treasury-rates
일봉(1바/일). HTTP는 여기서만 배선하고 collect/prices는 파싱·오케스트레이션만 한다.
"""
from __future__ import annotations
import argparse
import logging
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import httpx

from ..collect.prices import load_price_symbols, run_price_pass
from ..store.factory import make_store

log = logging.getLogger("newsstore.entrypoints.run_prices")

BASE_FMP = "https://financialmodelingprep.com/stable/"
BASE_YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/"
# Yahoo는 기본 UA를 차단 — 브라우저 UA 필요(뉴스 fetcher와 동일 관행).
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
# 인트라데이 조회 창 — 페이로드를 묶으면서, 스케줄러가 잠시 멈춰도 최근 며칠 5분봉을 갭필한다
# (새 바만 write하므로 겹침은 무비용). Yahoo 5m는 range로만 창을 준다.
INTRADAY_LOOKBACK_DAYS = 3
YAHOO_INTRADAY_RANGE = "5d"
# treasury-rates는 기간 조회 — 일봉 시계열 확보에 주말·공휴일 버퍼를 둔 달력일이 필요.
TREASURY_LOOKBACK_DAYS = 60


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="newsstore price collector (FMP + Yahoo, 5min bars)")
    ap.add_argument("--symbols", default="config/prices.yaml")
    args = ap.parse_args(argv)
    logging.basicConfig(level=os.environ.get("NEWSSTORE_LOG_LEVEL", "INFO"),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    api_key = os.environ["FMP_API_KEY"]              # fail-loud: 없으면 KeyError로 즉시 중단
    symbols = load_price_symbols(args.symbols)
    # 비밀(apikey)은 헤더로만 실어 URL·로그에 남지 않게 한다(SECRETS).
    fmp = httpx.Client(timeout=30.0, headers={"apikey": api_key})
    yahoo = httpx.Client(timeout=15.0, headers={"User-Agent": UA})

    def fmp_intraday(symbol: str) -> list:           # GET /stable/historical-chart/5min?symbol=^GSPC
        today = datetime.now(timezone.utc).date()
        frm = today - timedelta(days=INTRADAY_LOOKBACK_DAYS)
        r = fmp.get(f"{BASE_FMP}historical-chart/5min",
                    params={"symbol": symbol, "from": frm.isoformat(), "to": today.isoformat()})
        r.raise_for_status()
        return r.json()

    def fmp_treasury() -> list:                      # GET /stable/treasury-rates?from=&to=
        today = datetime.now(timezone.utc).date()
        frm = today - timedelta(days=TREASURY_LOOKBACK_DAYS)
        r = fmp.get(f"{BASE_FMP}treasury-rates",
                    params={"from": frm.isoformat(), "to": today.isoformat()})
        r.raise_for_status()
        return r.json()

    def yahoo_intraday(symbol: str) -> dict:         # Yahoo chart 5m(무키, UA) — 폴백 3종
        r = yahoo.get(f"{BASE_YAHOO}{quote(symbol)}",
                      params={"range": YAHOO_INTRADAY_RANGE, "interval": "5m"})
        r.raise_for_status()
        return r.json()

    fetchers = {"fmp_intraday": fmp_intraday,
                "fmp_treasury": fmp_treasury, "yahoo_intraday": yahoo_intraday}

    # 콜 간 지연(레이트리밋 대응 — env, 기본 0.2s). 심볼 수 적어 하한만.
    delay_s = float(os.environ.get("NEWSSTORE_PRICE_DELAY_S", "0.2"))
    try:
        with make_store() as store:
            n = run_price_pass(store, fetchers, symbols, delay_s=delay_s)
    finally:
        fmp.close()
        yahoo.close()
    log.info("price collect done: %d new bar(s) across %d symbols", n, len(symbols))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
