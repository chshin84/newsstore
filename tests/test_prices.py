"""가격 수집(Twelve Data) — 순수 파싱·로드·계약. HTTP는 주입(fake)이라 네트워크 불요."""
from pathlib import Path

import pytest

from newsstore.collect.prices import (load_price_symbols, parse_quote, run_price_pass, PriceSymbol)

REPO = Path(__file__).resolve().parents[1]


def test_load_real_prices_yaml():
    syms = load_price_symbols(str(REPO / "config" / "prices.yaml"))
    keys = {s.key for s in syms}
    assert {"kospi", "sp500", "usdkrw", "wti", "gold", "btc"} <= keys      # 커버리지
    assert all(isinstance(s, PriceSymbol) and s.td_symbol for s in syms)


def test_load_fails_loud_on_dup_key(tmp_path):
    p = tmp_path / "d.yaml"
    p.write_text("symbols:\n  - {key: a, td_symbol: X, label: A}\n  - {key: a, td_symbol: Y, label: B}\n",
                 encoding="utf-8")
    with pytest.raises(ValueError, match="중복"):
        load_price_symbols(str(p))


def test_parse_quote_ok():
    raw = {"symbol": "GSPC", "close": "7483.23", "change": "-12.5",
           "percent_change": "-0.17", "datetime": "2026-07-04", "currency": "USD"}
    q = parse_quote(raw)
    assert q["close"] == 7483.23 and q["percent_change"] == -0.17
    assert q["datetime"] == "2026-07-04" and q["currency"] == "USD"


def test_parse_quote_error_or_missing():
    assert parse_quote({"status": "error", "message": "not found"}) is None   # TD 에러 응답
    assert parse_quote({"symbol": "X"}) is None                               # close 없음
    assert parse_quote(None) is None
    assert parse_quote({"close": "n/a"}) is None                              # 비수치 close


class _Store:
    def __init__(self): self.saved = {}
    def save_price(self, key, data): self.saved[key] = data


def test_run_price_pass_fetches_and_saves():
    syms = [PriceSymbol("sp500", "GSPC", "S&P500", "us_equity"),
            PriceSymbol("btc", "BTC/USD", "비트코인", "crypto")]
    calls = []
    def fake_fetch(td_symbol):                       # 주입 HTTP — 심볼별 응답
        calls.append(td_symbol)
        return {"symbol": td_symbol, "close": "100.0", "percent_change": "1.5",
                "datetime": "2026-07-04", "currency": "USD"}
    store = _Store()
    n = run_price_pass(store, fake_fetch, syms)
    assert n == 2 and set(store.saved) == {"sp500", "btc"}
    assert store.saved["sp500"]["close"] == 100.0 and store.saved["sp500"]["label"] == "S&P500"
    assert "GSPC" in calls and "BTC/USD" in calls


def test_run_price_pass_skips_failed_fetch():
    syms = [PriceSymbol("kospi", "KS11", "코스피", "kr_equity")]
    def fake_fetch(td_symbol):
        return {"status": "error", "message": "symbol not found"}   # 심볼 미지원 → 스킵(fail-soft)
    store = _Store()
    n = run_price_pass(store, fake_fetch, syms)
    assert n == 0 and store.saved == {}                              # 저장 안 함(비파괴)
