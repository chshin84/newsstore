"""팩터·펀더멘털 수집 엔트리포인트 — FMP /stable/에서 계약(docs/firestore-contract.md)대로 수집.

먼저 constituent에서 유니버스를 도출(+PIT 컬렉션 적재)하고, universe × 스펙을 돌며 재무·가격·
컨센서스 데이터를 컬렉션별로 적재한다. 다운스트림 백테스트 seam — newsstore는 수집·전달만 한다.

cadence로 무엇을 돌릴지 고른다(계약의 수집 주기):
  --cadence daily   : 배당조정 EOD 등 일 1회짜리만.
  --cadence weekly  : 재무제표·비율·시총·프로파일·§2 as-of 스냅샷 등 주 1회짜리(+유니버스 갱신).
  --cadence all     : 전부(초기 백필).
비밀(apikey)은 헤더로만 실어 URL·로그에 남지 않게 한다(SECRETS). FMP_API_KEY는 env에서만 읽는다.
"""
from __future__ import annotations
import argparse
import logging
import os
from datetime import datetime, timedelta, timezone

import httpx
import yaml

from ..collect.factors import specs_for, run_factor_pass
from ..collect.universe import collect_universe, INDEX_ENDPOINTS
from ..store.factory import make_store

log = logging.getLogger("newsstore.entrypoints.run_factors")
BASE_FMP = "https://financialmodelingprep.com/stable/"


def load_factors_config(path: str) -> tuple[list[str], int]:
    """config/factors.yaml → (indices, max_symbols). fail-loud(모르는 인덱스·형식 오류)."""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    indices = raw.get("indices")
    if not isinstance(indices, list) or not indices:
        raise ValueError(f"{path}: 'indices' 리스트가 필요하다")
    for idx in indices:
        if idx not in INDEX_ENDPOINTS:
            raise ValueError(f"{path}: 모르는 인덱스 {idx!r} — {sorted(INDEX_ENDPOINTS)} 중 하나")
    max_symbols = raw.get("max_symbols", 0)
    if not isinstance(max_symbols, int) or max_symbols < 0:
        raise ValueError(f"{path}: max_symbols는 0 이상 정수여야 한다 — {max_symbols!r}")
    return indices, max_symbols


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="newsstore factor/fundamentals collector (FMP)")
    ap.add_argument("--config", default="config/factors.yaml")
    ap.add_argument("--cadence", default="all", choices=["daily", "weekly", "all"])
    args = ap.parse_args(argv)
    logging.basicConfig(level=os.environ.get("NEWSSTORE_LOG_LEVEL", "INFO"),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    api_key = os.environ["FMP_API_KEY"]              # fail-loud: 없으면 KeyError로 즉시 중단
    indices, max_symbols = load_factors_config(args.config)
    specs = specs_for(args.cadence)

    now = datetime.now(timezone.utc)
    fetched_at = now.isoformat()
    capture_date = now.strftime("%Y%m%d")            # §2 as-of 문서 id 조각(주간 스냅샷 키)

    # 비밀은 헤더로만(SECRETS). FMP 750콜/분 → 콜 간 지연(env, 기본 0.1s).
    fmp = httpx.Client(timeout=30.0, headers={"apikey": api_key})
    delay_s = float(os.environ.get("NEWSSTORE_FACTOR_DELAY_S", "0.1"))

    def _get(path: str, params: dict) -> list | dict:
        r = fmp.get(f"{BASE_FMP}{path}", params=params)
        r.raise_for_status()
        return r.json()

    def fetch_current(idx):  return _get(INDEX_ENDPOINTS[idx][0], {})
    def fetch_changes(idx):  return _get(INDEX_ENDPOINTS[idx][1], {})
    def fetch_delisted():    return _get("delisted-companies", {})

    def fetch_spec(spec, symbol):                    # per-symbol 스펙 fetch(엔진이 호출)
        params = {"symbol": symbol, **spec.params}
        if spec.lookback_days:                       # 깊은 history(예: prices_eod 10년) — from/to 부여
            today = datetime.now(timezone.utc).date()
            params["from"] = (today - timedelta(days=spec.lookback_days)).isoformat()
            params["to"] = today.isoformat()
        return _get(spec.endpoint, params)

    try:
        with make_store() as store:
            universe = collect_universe(store, fetch_current, fetch_changes, fetch_delisted,
                                        indices, fetched_at=fetched_at)
            if max_symbols:
                universe = universe[:max_symbols]
                log.info("universe capped to %d (max_symbols)", len(universe))
            counts = run_factor_pass(store, fetch_spec, universe, specs,
                                     capture_date=capture_date, fetched_at=fetched_at,
                                     delay_s=delay_s)
    finally:
        fmp.close()

    total = sum(counts.values())
    log.info("factor collect done (cadence=%s): %d doc(s) over %d symbols; per-collection %s",
             args.cadence, total, len(universe), counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
