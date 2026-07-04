"""가격 수집(Yahoo Finance) — 순수 파싱·로드·계약. HTTP는 주입(fake)이라 네트워크 불요."""
import re
from pathlib import Path

import pytest

from newsstore.collect.prices import (load_price_symbols, parse_yahoo_chart, run_price_pass,
                                      PriceSymbol)

REPO = Path(__file__).resolve().parents[1]
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def test_load_real_prices_yaml():
    syms = load_price_symbols(str(REPO / "config" / "prices.yaml"))
    keys = {s.key for s in syms}
    # Yahoo 실측 확정 키: 실제 지수·수익률·환율·원자재
    assert {"kospi200", "kosdaq", "nasdaq", "sp500", "us2y", "us10y", "us30y",
            "usdkrw", "usdjpy", "wti", "gold"} <= keys
    assert all(isinstance(s, PriceSymbol) and s.symbol for s in syms)


def test_load_fails_loud_on_dup_key(tmp_path):
    p = tmp_path / "d.yaml"
    p.write_text("symbols:\n  - {key: a, symbol: X, label: A}\n  - {key: a, symbol: Y, label: B}\n",
                 encoding="utf-8")
    with pytest.raises(ValueError, match="중복"):
        load_price_symbols(str(p))


# Yahoo epoch(초) — 실제 날짜(2026-06-30·07-01·07-02 UTC 자정)
E = [1782777600, 1782864000, 1782950400]


def _yc(closes, *, epochs=None, prev=None, currency="USD", price=None):
    """Yahoo chart 응답 fake — closes=오래된→최신(Yahoo 순서)."""
    ts = epochs if epochs is not None else E[:len(closes)]
    meta = {"regularMarketPrice": price if price is not None else closes[-1], "currency": currency}
    if prev is not None:
        meta["chartPreviousClose"] = prev
    return {"chart": {"result": [{"meta": meta, "timestamp": ts,
            "indicators": {"quote": [{"close": closes}]}}], "error": None}}


def test_parse_yahoo_ok_value_and_chart():
    # meta.regularMarketPrice=현재값, chartPreviousClose=직전 → 등락. series=오래된→최신 {날짜,c}.
    q = parse_yahoo_chart(_yc([746.77, 745.76, 744.78], prev=745.76, price=744.78))
    assert q["close"] == 744.78 and q["currency"] == "USD"
    assert abs(q["percent_change"] - ((744.78 - 745.76) / 745.76 * 100)) < 1e-9
    assert [p["c"] for p in q["series"]] == [746.77, 745.76, 744.78]   # 오래된→최신
    assert all(_DATE.match(p["t"]) for p in q["series"])               # t=날짜 문자열
    assert q["datetime"] == q["series"][-1]["t"]                       # 최신 날짜


def test_parse_yahoo_no_prev_no_change():
    q = parse_yahoo_chart(_yc([100.0], price=100.0))                   # chartPreviousClose 없음
    assert q["close"] == 100.0 and q["change"] is None and q["percent_change"] is None
    assert [p["c"] for p in q["series"]] == [100.0]


def test_parse_yahoo_drops_null_closes():
    # Yahoo는 휴장일 close에 null을 낀다 — 걸러야 함(길이 불일치 zip 안전).
    q = parse_yahoo_chart(_yc([100.0, None, 102.0], epochs=E, prev=100.0, price=102.0))
    assert [p["c"] for p in q["series"]] == [100.0, 102.0]             # null 드롭


def test_parse_yahoo_error_or_empty():
    assert parse_yahoo_chart({"chart": {"result": None, "error": {"code": "Not Found"}}}) is None
    assert parse_yahoo_chart({"chart": {"result": []}}) is None
    assert parse_yahoo_chart({}) is None
    assert parse_yahoo_chart(None) is None
    # regularMarketPrice 없으면 무효
    assert parse_yahoo_chart({"chart": {"result": [{"meta": {}, "timestamp": [], "indicators": {"quote": [{"close": []}]}}]}}) is None


class _Store:
    def __init__(self): self.saved = {}
    def save_price(self, key, data): self.saved[key] = data


def test_run_price_pass_fetches_and_saves():
    syms = [PriceSymbol("sp500", "^GSPC", "S&P500"),
            PriceSymbol("wti", "CL=F", "WTI유가")]
    calls = []
    def fake_fetch(symbol):                          # 주입 HTTP(Yahoo chart) — 심볼별 응답
        calls.append(symbol)
        return _yc([100.0, 101.0], prev=100.0, price=101.0)
    store = _Store()
    n = run_price_pass(store, fake_fetch, syms)
    assert n == 2 and set(store.saved) == {"sp500", "wti"}
    assert store.saved["sp500"]["close"] == 101.0 and store.saved["sp500"]["label"] == "S&P500"
    assert store.saved["sp500"]["symbol"] == "^GSPC"
    assert len(store.saved["sp500"]["series"]) == 2               # 차트 시계열 저장
    assert "^GSPC" in calls and "CL=F" in calls


def test_run_price_pass_skips_failed_fetch():
    syms = [PriceSymbol("kosdaq", "^KQ11", "코스닥")]
    def fake_fetch(symbol):
        return {"chart": {"result": None, "error": {"code": "Not Found"}}}   # 미지원 → 스킵(fail-soft)
    store = _Store()
    n = run_price_pass(store, fake_fetch, syms)
    assert n == 0 and store.saved == {}                              # 저장 안 함(비파괴)
