"""펀더멘털 수집(FMP) — 순수 로드·취합·계약. HTTP는 주입(fake)이라 네트워크 불요."""
import json
import re
from pathlib import Path

import pytest

from newsstore.collect.fundamentals import (load_fundamental_tickers,
                                            run_fundamentals_pass, STATEMENTS)

REPO = Path(__file__).resolve().parents[1]
FIX = REPO / "tests" / "fixtures"
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T")


def _fix(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


# ─────────────────────────────── config/fundamentals.yaml (SSOT) ───────────────────────────────

def test_load_real_fundamentals_yaml():
    tickers = load_fundamental_tickers(str(REPO / "config" / "fundamentals.yaml"))
    assert tickers and all(isinstance(t, str) and t.isupper() for t in tickers)
    assert len(set(tickers)) == len(tickers)          # 중복 없음(불변식)


def test_load_normalizes_and_dedups(tmp_path):
    p = tmp_path / "f.yaml"
    p.write_text("tickers:\n  - aapl\n  - MSFT\n", encoding="utf-8")
    assert load_fundamental_tickers(str(p)) == ["AAPL", "MSFT"]     # 대문자 정규화


def test_load_fails_loud_on_empty(tmp_path):
    p = tmp_path / "e.yaml"
    p.write_text("tickers: []\n", encoding="utf-8")
    with pytest.raises(ValueError, match="tickers"):
        load_fundamental_tickers(str(p))


def test_load_fails_loud_on_dup(tmp_path):
    p = tmp_path / "d.yaml"
    p.write_text("tickers:\n  - AAPL\n  - aapl\n", encoding="utf-8")
    with pytest.raises(ValueError, match="중복"):
        load_fundamental_tickers(str(p))


def test_load_fails_loud_on_non_string(tmp_path):
    p = tmp_path / "n.yaml"
    p.write_text("tickers:\n  - AAPL\n  - 123\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_fundamental_tickers(str(p))


# ─────────────────────────────── run_fundamentals_pass ───────────────────────────────

class _Store:
    def __init__(self): self.saved = {}
    def save_fundamental(self, symbol, data): self.saved[symbol] = data


def _fixture_fetch(ticker, statement):
    # 실 FMP 응답 형태(픽스처)를 statement별로 반환 — AAPL만 준비.
    return _fix(f"fmp_{statement}_aapl.json")


def test_run_fundamentals_pass_saves_three_statements_and_fetched_at():
    store = _Store()
    n = run_fundamentals_pass(store, _fixture_fetch, ["AAPL"])
    assert n == 1
    d = store.saved["AAPL"]
    assert set(d) == {"income", "balance", "cashflow", "fetched_at"}
    for stmt in STATEMENTS:
        assert isinstance(d[stmt], list) and d[stmt]                # 각 문서 비어있지 않음
    assert d["income"][0]["symbol"] == "AAPL" and d["income"][0]["revenue"] == 416200000000
    assert d["balance"][0]["totalAssets"] == 352500000000
    assert d["cashflow"][0]["operatingCashFlow"] == 122500000000
    assert _ISO.match(d["fetched_at"])                              # 신선도 스탬프(§2)


def test_run_fundamentals_pass_calls_each_statement_per_ticker():
    store = _Store()
    calls = []

    def fetch(ticker, statement):
        calls.append((ticker, statement))
        return [{"symbol": ticker}]

    run_fundamentals_pass(store, fetch, ["AAPL", "MSFT"])
    assert calls == [("AAPL", "income"), ("AAPL", "balance"), ("AAPL", "cashflow"),
                     ("MSFT", "income"), ("MSFT", "balance"), ("MSFT", "cashflow")]


def test_run_fundamentals_pass_guards_none_like_real_client():
    # mock vs 실클라이언트 None 차이: 실 SDK는 빈 결과에 None을 줄 수 있다 → `x or []` 가드.
    store = _Store()

    def fetch(ticker, statement):
        return None if statement == "cashflow" else [{"symbol": ticker}]

    n = run_fundamentals_pass(store, fetch, ["AAPL"])
    assert n == 1 and store.saved["AAPL"]["cashflow"] == []          # None → [] (crash 없음)
    assert store.saved["AAPL"]["income"] == [{"symbol": "AAPL"}]


def test_run_fundamentals_pass_skips_when_all_empty():
    store = _Store()
    n = run_fundamentals_pass(store, lambda t, s: [], ["AAPL"])
    assert n == 0 and store.saved == {}                             # 세 문서 모두 무효 → 저장 안 함


def test_run_fundamentals_pass_one_failure_does_not_block_others():
    store = _Store()

    def fetch(ticker, statement):
        if ticker == "AAPL":
            raise RuntimeError("rate limited")
        return [{"symbol": ticker}]

    n = run_fundamentals_pass(store, fetch, ["AAPL", "MSFT"])
    assert n == 1 and set(store.saved) == {"MSFT"}                  # 한 티커 실패가 나머지를 막지 않음
