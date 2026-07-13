"""5분봉 1년 백필 엔트리포인트 — FMP historical-chart/5min을 주 단위로 역수집해 price_bars에 적재.

FMP는 넓은 from/to엔 최근 ~1주만 주므로, 1년치는 주 단위(~52콜/심볼)로 페이지네이션한다(실측).
대상은 --target으로 고른다:
  macro    : config/prices.yaml의 FMP 소스 심볼(지수·환율·원자재·VIX). Yahoo 폴백 3종(kosdaq·dxy·wti)은
             FMP 5분 미커버라 제외(Yahoo 5분은 ~60일만이라 1년 백필 불가 — 별도).
  universe : S&P500 ∪ Nasdaq-100 ∪ Dow 현재 구성종목(constituent에서 도출, ~600).
  both     : 둘 다.
초기 백필은 대용량이다(주식 600 × 1년 ≈ 1,180만 문서). 30일 TTL 컨베이어로 다운스트림이 받아간다.
비밀(apikey)은 헤더로만. FMP_API_KEY는 env에서만.
"""
from __future__ import annotations
import argparse
import logging
import os
from datetime import datetime, timezone

import httpx

from ..collect.prices import PriceSymbol, week_windows, run_intraday_backfill, load_price_symbols
from ..collect.universe import INDEX_ENDPOINTS
from ..store.factory import make_store

log = logging.getLogger("newsstore.entrypoints.run_intraday_backfill")
BASE_FMP = "https://financialmodelingprep.com/stable/"


def macro_symbols(path: str) -> list[PriceSymbol]:
    """config/prices.yaml에서 FMP 소스 5분봉 대상만(Yahoo 폴백 제외 — FMP 5분 미커버)."""
    return [s for s in load_price_symbols(path) if s.source == "fmp"]


def universe_symbols(fetch_current, indices: list[str]) -> list[PriceSymbol]:
    """indices 현재 구성종목 합집합 → 종목별 PriceSymbol(백필용, 저장 안 함)."""
    seen: dict[str, PriceSymbol] = {}
    for idx in indices:
        try:
            rows = fetch_current(idx)
        except Exception as e:
            log.warning("universe %s 구성 조회 실패: %s", idx, e)
            continue
        for r in (rows or []):
            sym = r.get("symbol") if isinstance(r, dict) else None
            if sym and sym not in seen:
                seen[sym] = PriceSymbol(sym, sym, r.get("name", sym), "주식", None, "fmp")
    return sorted(seen.values(), key=lambda s: s.key)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="newsstore 5min intraday backfill (FMP, weekly pagination)")
    ap.add_argument("--target", default="both", choices=["macro", "universe", "both"])
    ap.add_argument("--days", type=int, default=365, help="백필 기간(일). 기본 1년.")
    ap.add_argument("--symbols", default="config/prices.yaml", help="macro 심볼 SSOT")
    ap.add_argument("--max-symbols", type=int, default=0, help="유니버스 상한(0=무제한, 검증용)")
    args = ap.parse_args(argv)
    logging.basicConfig(level=os.environ.get("NEWSSTORE_LOG_LEVEL", "INFO"),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    api_key = os.environ["FMP_API_KEY"]              # fail-loud
    fmp = httpx.Client(timeout=30.0, headers={"apikey": api_key})
    delay_s = float(os.environ.get("NEWSSTORE_INTRADAY_DELAY_S", "0.1"))
    now = datetime.now(timezone.utc)
    fetched_at = now.isoformat()
    windows = week_windows(args.days, now.date())

    def fetch_current(idx):
        r = fmp.get(f"{BASE_FMP}{INDEX_ENDPOINTS[idx][0]}"); r.raise_for_status(); return r.json()

    def fetch_window(symbol, frm, to):               # GET /stable/historical-chart/5min?symbol=&from=&to=
        r = fmp.get(f"{BASE_FMP}historical-chart/5min",
                    params={"symbol": symbol, "from": frm, "to": to})
        r.raise_for_status()
        return r.json()

    symbols: list[PriceSymbol] = []
    if args.target in ("macro", "both"):
        symbols += macro_symbols(args.symbols)
    if args.target in ("universe", "both"):
        uni = universe_symbols(fetch_current, list(INDEX_ENDPOINTS))
        if args.max_symbols:
            uni = uni[:args.max_symbols]
        symbols += uni

    log.info("intraday backfill 시작: target=%s, %d심볼 × %d주창(%d일), 예상 콜=%d",
             args.target, len(symbols), len(windows), args.days, len(symbols) * len(windows))
    try:
        with make_store() as store:
            n = run_intraday_backfill(store, fetch_window, symbols, windows,
                                      fetched_at=fetched_at, delay_s=delay_s)
    finally:
        fmp.close()
    log.info("intraday backfill done: %d bars over %d symbols", n, len(symbols))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
