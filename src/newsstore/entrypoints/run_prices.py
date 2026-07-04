"""가격 수집 엔트리포인트 — Twelve Data /quote로 config/prices.yaml 심볼을 prices/{key}에 저장.

비밀: TWELVEDATA_API_KEY(env, Secret Manager 주입 — 커밋/로그 비노출). 무료 800콜/일.
"""
from __future__ import annotations
import argparse
import logging
import os

import httpx

from ..collect.prices import load_price_symbols, run_price_pass
from ..store.factory import make_store

log = logging.getLogger("newsstore.entrypoints.run_prices")
BASE = "https://api.twelvedata.com/quote"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="newsstore price collector (Twelve Data)")
    ap.add_argument("--symbols", default="config/prices.yaml")
    args = ap.parse_args(argv)
    logging.basicConfig(level=os.environ.get("NEWSSTORE_LOG_LEVEL", "INFO"),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    api_key = os.environ.get("TWELVEDATA_API_KEY")
    if not api_key:                                  # 비밀 분리: 없으면 fail-loud(키 로그 비노출)
        log.error("TWELVEDATA_API_KEY not set — required for price collector")
        return 2

    symbols = load_price_symbols(args.symbols)
    client = httpx.Client(timeout=15.0)

    def fetch(td_symbol: str) -> dict:               # 주입 HTTP — 모듈은 파싱만
        r = client.get(BASE, params={"symbol": td_symbol, "apikey": api_key})
        r.raise_for_status()
        return r.json()

    try:
        with make_store() as store:
            n = run_price_pass(store, fetch, symbols)
    finally:
        client.close()
    log.info("price collect done: %d/%d saved", n, len(symbols))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
