"""가격 데이터 수집 — Twelve Data(/quote)로 지수·환율·원자재·크립토 스냅샷을 prices/{key}에 저장.

목적: exogenous 비-LLM 앵커 — 뉴스 센티먼트(프레임) vs 실제 가격 반응으로 over/under-reaction
판정 + 모델 순환 차단. SSOT는 config/prices.yaml. HTTP는 주입(테스트 fake) — 이 모듈은 파싱·
오케스트레이션만. 비밀(TWELVEDATA_API_KEY)은 엔트리포인트가 env로 받아 fetch에 배선.
"""
from __future__ import annotations
import logging
import time
from dataclasses import dataclass
from typing import Callable

import yaml

log = logging.getLogger("newsstore.collect.prices")


@dataclass(frozen=True)
class PriceSymbol:
    key: str            # 내부 id — prices/{key} 문서
    td_symbol: str      # Twelve Data 심볼(예: GSPC, USD/KRW, XAU/USD, BTC/USD)
    label: str
    lens: str | None = None


def load_price_symbols(path: str) -> list[PriceSymbol]:
    """config/prices.yaml 로드 + fail-loud(키 중복·필수필드 누락)."""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    rows = raw.get("symbols")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{path}: 'symbols' 리스트가 필요하다")
    out, seen = [], set()
    for r in rows:
        key, td = r.get("key"), r.get("td_symbol")
        if not (isinstance(key, str) and key.strip() and isinstance(td, str) and td.strip()):
            raise ValueError(f"{path}: key·td_symbol 필수 — {r}")
        if key in seen:
            raise ValueError(f"{path}: key 중복 {key!r}")
        seen.add(key)
        out.append(PriceSymbol(key.strip(), td.strip(), r.get("label", key), r.get("lens")))
    return out


SERIES_MAX_POINTS = 30           # 차트에 실을 일봉 수(값+차트 = 이 시계열 하나로 도출)


def _fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def parse_series(raw, *, max_points: int = SERIES_MAX_POINTS) -> dict | None:
    """Twelve Data /time_series(일봉) 응답 파싱 → 현재값·등락 + 차트 시계열(값+차트 겸용).
    values는 최신순: [0]=오늘 close, [1]=직전 → 등락 도출. series는 오래된→최신 {t,c}.
    에러/빈 값/비수치 → None(fail-soft, 저장 안 함)."""
    if not isinstance(raw, dict) or raw.get("status") == "error":
        return None
    vals = raw.get("values")
    if not isinstance(vals, list) or not vals:
        return None
    close = _fnum(vals[0].get("close") if isinstance(vals[0], dict) else None)
    if close is None:
        return None
    prev = _fnum(vals[1].get("close")) if len(vals) > 1 and isinstance(vals[1], dict) else None
    change = (close - prev) if prev is not None else None
    pct = ((close - prev) / prev * 100.0) if prev not in (None, 0) else None
    series = []
    for v in reversed(vals[:max_points]):            # 오래된→최신
        c = _fnum(v.get("close")) if isinstance(v, dict) else None
        if c is not None and v.get("datetime"):
            series.append({"t": v["datetime"], "c": c})
    meta = raw.get("meta") or {}
    return {"close": close, "change": change, "percent_change": pct,
            "datetime": vals[0].get("datetime"), "currency": meta.get("currency"),
            "series": series}


def run_price_pass(store, fetch: Callable[[str], dict], symbols: list[PriceSymbol],
                   *, delay_s: float = 0.0) -> int:
    """각 심볼을 fetch(td_symbol)→parse→store.save_price(key, ...). 반환=저장 수.
    개별 심볼 실패(에러 응답·파싱 실패)는 스킵(fail-soft, 비파괴 — 기존 값 유지).
    delay_s: 콜 간 지연(무료 tier 8콜/분 rate limit 대응 — 엔트리포인트가 주입)."""
    n = 0
    for i, s in enumerate(symbols):
        if delay_s and i:
            time.sleep(delay_s)
        try:
            raw = fetch(s.td_symbol)
        except Exception as e:                       # 네트워크/타임아웃 — 그 심볼만 스킵
            log.warning("price fetch %s(%s) 실패: %s", s.key, s.td_symbol, e)
            continue
        q = parse_series(raw)
        if q is None:
            log.warning("price %s(%s): 무효 응답 — 스킵", s.key, s.td_symbol)
            continue
        store.save_price(s.key, {**q, "label": s.label, "lens": s.lens, "td_symbol": s.td_symbol})
        n += 1
    log.info("price pass: %d/%d saved", n, len(symbols))
    return n
