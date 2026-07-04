"""가격 수집(Twelve Data) — 순수 파싱·로드·계약. HTTP는 주입(fake)이라 네트워크 불요."""
from pathlib import Path

import pytest

from newsstore.collect.prices import (load_price_symbols, parse_series, run_price_pass, PriceSymbol)

REPO = Path(__file__).resolve().parents[1]


def test_load_real_prices_yaml():
    syms = load_price_symbols(str(REPO / "config" / "prices.yaml"))
    keys = {s.key for s in syms}
    # 무료 tier 실측 확정 키(ETF 프록시): 자산군 커버리지
    assert {"kr_equity", "sp500", "nasdaq", "usdkrw", "wti", "gold", "btc"} <= keys
    assert all(isinstance(s, PriceSymbol) and s.td_symbol for s in syms)


def test_load_fails_loud_on_dup_key(tmp_path):
    p = tmp_path / "d.yaml"
    p.write_text("symbols:\n  - {key: a, td_symbol: X, label: A}\n  - {key: a, td_symbol: Y, label: B}\n",
                 encoding="utf-8")
    with pytest.raises(ValueError, match="중복"):
        load_price_symbols(str(p))


def _ts(pairs, currency="USD"):
    """time_series 응답 fake — pairs=[(datetime, close), ...] 최신순."""
    return {"meta": {"currency": currency},
            "values": [{"datetime": d, "close": c} for d, c in pairs]}


def test_parse_series_ok_value_and_chart():
    # 최신순 values → 현재 close(=values[0]) + 직전 대비 등락 + 차트 시계열(오래된→최신)
    q = parse_series(_ts([("2026-07-02", "744.78"), ("2026-07-01", "745.76"),
                          ("2026-06-30", "746.77")]))
    assert q["close"] == 744.78 and q["datetime"] == "2026-07-02" and q["currency"] == "USD"
    assert abs(q["percent_change"] - ((744.78 - 745.76) / 745.76 * 100)) < 1e-9
    assert q["series"][0] == {"t": "2026-06-30", "c": 746.77}     # 오래된 먼저
    assert q["series"][-1] == {"t": "2026-07-02", "c": 744.78}    # 최신 마지막


def test_parse_series_single_point_no_change():
    q = parse_series(_ts([("2026-07-02", "100")]))
    assert q["close"] == 100.0 and q["change"] is None and q["percent_change"] is None
    assert q["series"] == [{"t": "2026-07-02", "c": 100.0}]       # 한 점도 차트엔 유효


def test_parse_series_error_or_empty():
    assert parse_series({"status": "error", "message": "not found"}) is None
    assert parse_series({"values": []}) is None                   # 빈 시계열
    assert parse_series({}) is None
    assert parse_series(None) is None
    assert parse_series(_ts([("d", "n/a")])) is None              # 비수치 close


class _Store:
    def __init__(self): self.saved = {}
    def save_price(self, key, data): self.saved[key] = data


def test_run_price_pass_fetches_and_saves():
    syms = [PriceSymbol("sp500", "SPY", "S&P500", "us_equity"),
            PriceSymbol("btc", "BTC/USD", "비트코인", "crypto")]
    calls = []
    def fake_fetch(td_symbol):                       # 주입 HTTP(time_series) — 심볼별 응답
        calls.append(td_symbol)
        return _ts([("2026-07-02", "101.0"), ("2026-07-01", "100.0")])
    store = _Store()
    n = run_price_pass(store, fake_fetch, syms)
    assert n == 2 and set(store.saved) == {"sp500", "btc"}
    assert store.saved["sp500"]["close"] == 101.0 and store.saved["sp500"]["label"] == "S&P500"
    assert len(store.saved["sp500"]["series"]) == 2               # 차트 시계열 저장
    assert "SPY" in calls and "BTC/USD" in calls


def test_run_price_pass_skips_failed_fetch():
    syms = [PriceSymbol("kospi", "KS11", "코스피", "kr_equity")]
    def fake_fetch(td_symbol):
        return {"status": "error", "message": "symbol not found"}   # 심볼 미지원 → 스킵(fail-soft)
    store = _Store()
    n = run_price_pass(store, fake_fetch, syms)
    assert n == 0 and store.saved == {}                              # 저장 안 함(비파괴)
