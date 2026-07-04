"""가격 데이터 수집 — Yahoo Finance chart API로 실제 지수·수익률·환율·원자재를 prices/{key}에 저장.

목적: 가격 탭(값+차트). SSOT는 config/prices.yaml. HTTP는 주입(테스트 fake) — 이 모듈은
Yahoo 응답 파싱·오케스트레이션만. Yahoo chart API는 무키(User-Agent만 필요) — 엔트리포인트가 배선.
개별 종목 히스토리(뉴스 언급 종목)도 같은 파서로 stock_prices/{ticker}에 저장(run_stock_prices).
"""
from __future__ import annotations
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

import yaml

log = logging.getLogger("newsstore.collect.prices")


@dataclass(frozen=True)
class PriceSymbol:
    key: str            # 내부 id — prices/{key} 문서
    symbol: str         # Yahoo 심볼(예: ^GSPC, ^KQ11, KRW=X, CL=F, 005930.KS)
    label: str


def load_price_symbols(path: str) -> list[PriceSymbol]:
    """config/prices.yaml 로드 + fail-loud(키 중복·필수필드 누락)."""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    rows = raw.get("symbols")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{path}: 'symbols' 리스트가 필요하다")
    out, seen = [], set()
    for r in rows:
        key, sym = r.get("key"), r.get("symbol")
        if not (isinstance(key, str) and key.strip() and isinstance(sym, str) and sym.strip()):
            raise ValueError(f"{path}: key·symbol 필수 — {r}")
        if key in seen:
            raise ValueError(f"{path}: key 중복 {key!r}")
        seen.add(key)
        out.append(PriceSymbol(key.strip(), sym.strip(), r.get("label", key)))
    return out


SERIES_MAX_POINTS = 30           # 차트에 실을 일봉 수(값+차트 = 이 시계열 하나로 도출)


def _fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _epoch_to_date(t) -> str | None:
    try:
        return datetime.fromtimestamp(int(t), tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def parse_yahoo_chart(raw, *, max_points: int = SERIES_MAX_POINTS) -> dict | None:
    """Yahoo Finance chart API 응답 파싱 → 현재값·등락 + 차트 시계열(값+차트 겸용).
    chart.result[0]: meta.regularMarketPrice(=현재값), meta.chartPreviousClose(직전),
    timestamp[]·indicators.quote[0].close[](일봉). series=오래된→최신 {t(날짜),c}.
    에러/무result/무close → None(fail-soft, 저장 안 함)."""
    if not isinstance(raw, dict):
        return None
    res = ((raw.get("chart") or {}).get("result")) if isinstance(raw.get("chart"), dict) else None
    if not isinstance(res, list) or not res or not isinstance(res[0], dict):
        return None
    r0 = res[0]
    meta = r0.get("meta") or {}
    ts = r0.get("timestamp") or []
    quotes = (((r0.get("indicators") or {}).get("quote") or [{}])[0] or {}).get("close") or []
    series = []
    for t, c in zip(ts, quotes):
        cv, dt = _fnum(c), _epoch_to_date(t)
        if cv is not None and dt is not None:
            series.append({"t": dt, "c": cv})
    series = series[-max_points:]                    # 최근 N일(오래된→최신 유지)
    # 값·등락 모두 시계열에서 도출 — 값=series[-1](차트 끝점과 일치), 전일=series[-2].
    # ⚠️ regularMarketPrice(라이브)를 close로 쓰면 시계열이 stale일 때 다일간 등락이 되고
    #    (^KS200 사례 -10%), meta.chartPreviousClose는 range=1mo에선 '한 달 전'이라 둘 다 안 씀.
    close = series[-1]["c"] if series else _fnum(meta.get("regularMarketPrice"))
    if close is None:
        return None
    prev = series[-2]["c"] if len(series) >= 2 else None
    change = (close - prev) if prev is not None else None
    pct = ((close - prev) / prev * 100.0) if prev not in (None, 0) else None
    return {"close": close, "change": change, "percent_change": pct,
            "datetime": (series[-1]["t"] if series else _epoch_to_date(meta.get("regularMarketTime"))),
            "currency": meta.get("currency"), "series": series}


def run_price_pass(store, fetch: Callable[[str], dict], symbols: list[PriceSymbol],
                   *, delay_s: float = 0.0) -> int:
    """각 심볼을 fetch(symbol)→parse_yahoo_chart→store.save_price(key, ...). 반환=저장 수.
    개별 심볼 실패(에러 응답·파싱 실패)는 스킵(fail-soft, 비파괴 — 기존 값 유지).
    delay_s: 콜 간 지연(Yahoo throttle 대응 — 엔트리포인트가 주입)."""
    n = 0
    for i, s in enumerate(symbols):
        if delay_s and i:
            time.sleep(delay_s)
        try:
            raw = fetch(s.symbol)
        except Exception as e:                       # 네트워크/타임아웃 — 그 심볼만 스킵
            log.warning("price fetch %s(%s) 실패: %s", s.key, s.symbol, e)
            continue
        q = parse_yahoo_chart(raw)
        if q is None:
            log.warning("price %s(%s): 무효 응답 — 스킵", s.key, s.symbol)
            continue
        store.save_price(s.key, {**q, "label": s.label, "symbol": s.symbol})
        n += 1
    log.info("price pass: %d/%d saved", n, len(symbols))
    return n
