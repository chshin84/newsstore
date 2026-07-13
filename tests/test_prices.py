"""가격 수집(FMP + Yahoo, 5분봉 스트림) — 순수 파싱·로드·디스패치·계약. HTTP는 주입(fake)이라 네트워크 불요."""
import json
import re
from pathlib import Path

import pytest

from datetime import date

from newsstore.collect.prices import (load_price_symbols, PriceSymbol,
                                      bars_from_fmp_intraday, bars_from_yahoo_intraday,
                                      bars_from_treasury, run_price_pass, _bar_id,
                                      week_windows, run_intraday_backfill)

REPO = Path(__file__).resolve().parents[1]
FIX = REPO / "tests" / "fixtures"
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T")
FA = "2026-07-10T16:05:00+00:00"          # 테스트용 고정 fetched_at


def _fix(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


# ─────────────────────────────── config/prices.yaml (SSOT) ───────────────────────────────

def test_load_real_prices_yaml():
    syms = load_price_symbols(str(REPO / "config" / "prices.yaml"))
    keys = {s.key for s in syms}
    assert {"kosdaq", "nasdaq", "sp500", "us2y", "us10y", "us30y",
            "usdkrw", "usdjpy", "wti", "gold", "dxy", "vix"} <= keys
    assert all(isinstance(s, PriceSymbol) and s.symbol for s in syms)


ALLOWED_GROUPS = {"지수", "금리", "환율", "원자재", "변동성"}


def test_real_prices_yaml_every_symbol_has_valid_group():
    for s in load_price_symbols(str(REPO / "config" / "prices.yaml")):
        assert s.group in ALLOWED_GROUPS, f"{s.key} group={s.group!r} 미허용"


def test_real_prices_yaml_order_is_yaml_sequence():
    syms = load_price_symbols(str(REPO / "config" / "prices.yaml"))
    assert [s.order for s in syms] == list(range(len(syms)))   # 0..n-1 연속(불변식)


def test_real_prices_yaml_fmp_symbol_mapping_matches_grounding():
    # 접지 검증(환각 금지): FMP 심볼이 실측 매핑 그대로여야 한다.
    syms = {s.key: s for s in load_price_symbols(str(REPO / "config" / "prices.yaml"))}
    assert (syms["nasdaq"].symbol, syms["nasdaq"].source) == ("^IXIC", "fmp")
    assert (syms["sp500"].symbol, syms["sp500"].source) == ("^GSPC", "fmp")
    assert (syms["vix"].symbol, syms["vix"].source) == ("^VIX", "fmp")
    assert (syms["usdkrw"].symbol, syms["usdkrw"].source) == ("USDKRW", "fmp")   # =X 없음
    assert (syms["usdjpy"].symbol, syms["usdjpy"].source) == ("USDJPY", "fmp")
    assert (syms["gold"].symbol, syms["gold"].source) == ("GCUSD", "fmp")


def test_real_prices_yaml_treasury_mapping():
    syms = {s.key: s for s in load_price_symbols(str(REPO / "config" / "prices.yaml"))}
    assert (syms["us2y"].source, syms["us2y"].treasury_key) == ("fmp_treasury", "year2")
    assert (syms["us10y"].source, syms["us10y"].treasury_key) == ("fmp_treasury", "year10")
    assert (syms["us30y"].source, syms["us30y"].treasury_key) == ("fmp_treasury", "year30")


def test_real_prices_yaml_yahoo_fallback_is_exactly_three():
    # Yahoo 폴백은 FMP Premium 미커버 3종(kosdaq·dxy·wti)에만 — 조용히 늘거나 줄면 안 된다.
    syms = load_price_symbols(str(REPO / "config" / "prices.yaml"))
    assert {s.key for s in syms if s.source == "yahoo"} == {"kosdaq", "dxy", "wti"}


def test_load_reads_source_and_treasury_key(tmp_path):
    p = tmp_path / "g.yaml"
    p.write_text("symbols:\n"
                 "  - {key: a, symbol: X, label: A, group: 지수, source: fmp}\n"
                 "  - {key: b, symbol: UST10Y, label: B, group: 금리, source: fmp_treasury, treasury_key: year10}\n",
                 encoding="utf-8")
    syms = load_price_symbols(str(p))
    assert (syms[0].source, syms[0].treasury_key, syms[0].order) == ("fmp", None, 0)
    assert (syms[1].source, syms[1].treasury_key, syms[1].order) == ("fmp_treasury", "year10", 1)


def test_load_fails_loud_on_unknown_source(tmp_path):
    p = tmp_path / "u.yaml"
    p.write_text("symbols:\n  - {key: a, symbol: X, label: A, group: 지수, source: bloomberg}\n",
                 encoding="utf-8")
    with pytest.raises(ValueError, match="source"):
        load_price_symbols(str(p))


def test_load_fails_loud_on_missing_source(tmp_path):
    p = tmp_path / "m.yaml"
    p.write_text("symbols:\n  - {key: a, symbol: X, label: A, group: 지수}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="source"):
        load_price_symbols(str(p))


def test_load_fails_loud_on_treasury_without_key(tmp_path):
    p = tmp_path / "t.yaml"
    p.write_text("symbols:\n  - {key: a, symbol: X, label: A, group: 금리, source: fmp_treasury}\n",
                 encoding="utf-8")
    with pytest.raises(ValueError, match="treasury_key"):
        load_price_symbols(str(p))


def test_load_fails_loud_on_dup_key(tmp_path):
    p = tmp_path / "d.yaml"
    p.write_text("symbols:\n  - {key: a, symbol: X, label: A, source: fmp}\n"
                 "  - {key: a, symbol: Y, label: B, source: fmp}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="중복"):
        load_price_symbols(str(p))


def test_price_symbol_positional_backward_compat():
    s = PriceSymbol("sp500", "^GSPC", "S&P500")
    assert s.group is None and s.order is None and s.source == "fmp" and s.treasury_key is None


# ─────────────────────────────── bar id ───────────────────────────────

def test_bar_id_deterministic_from_key_and_timestamp():
    # 결정론 id — 같은 (key, 타임스탬프)면 같은 id라 겹쳐 받아도 멱등(중복 문서 방지).
    assert _bar_id("sp500", "2026-07-10 15:55:00") == "sp500__20260710155500"
    assert _bar_id("us10y", "2026-07-02") == "us10y__20260702"


# ─────────────────────────────── bars_from_fmp_intraday ───────────────────────────────

SP = PriceSymbol("sp500", "^GSPC", "S&P500", "지수", 0, "fmp")


def _fmp_intra(rows_newest_first):
    # rows = [(date, close, open?, high?, low?, vol?)] 최신순(FMP 순서).
    out = []
    for r in rows_newest_first:
        d = {"date": r[0], "close": r[1]}
        for i, name in enumerate(("open", "high", "low", "volume"), start=2):
            if len(r) > i and r[i] is not None:
                d[name] = r[i]
        out.append(d)
    return out


def test_bars_from_fmp_intraday_sorted_oldest_to_newest_with_ohlcv():
    raw = _fmp_intra([("2026-07-10 10:10:00", 102.0, 101.0, 103.0, 100.5, 30),
                      ("2026-07-10 10:05:00", 101.0, 100.0, 101.5, 99.5, 20),
                      ("2026-07-10 10:00:00", 100.0, 99.0, 100.5, 98.5, 10)])
    bars = bars_from_fmp_intraday(raw, SP, fetched_at=FA)
    assert [b["close"] for b in bars] == [100.0, 101.0, 102.0]           # 오래된→최신
    assert [b["volume"] for b in bars] == [10.0, 20.0, 30.0]
    assert bars[0]["open"] == 99.0 and bars[-1]["high"] == 103.0
    assert bars[-1]["id"] == "sp500__20260710101000"
    assert bars[-1]["datetime"] == "2026-07-10 10:10:00"                 # 소스 문자열 보존
    assert all(b["key"] == "sp500" and b["source"] == "fmp" and b["fetched_at"] == FA for b in bars)


def test_bars_from_fmp_intraday_fixture_shape():
    # 실 FMP historical-chart/5min 응답 형태(픽스처) — 필드명(date·open·high·low·close·volume) 검증.
    bars = bars_from_fmp_intraday(_fix("fmp_intraday_sp500.json"), SP, fetched_at=FA)
    assert [b["close"] for b in bars] == [7576.90, 7577.32, 7575.38]     # 15:45→15:55
    assert bars[-1]["datetime"] == "2026-07-10 15:55:00" and bars[-1]["volume"] == 160254000.0


def test_bars_from_fmp_intraday_drops_no_close():
    raw = [{"date": "2026-07-10 10:00:00", "close": None},
           {"date": "2026-07-10 10:05:00"},
           {"date": "2026-07-10 10:10:00", "close": 5.0}]
    bars = bars_from_fmp_intraday(raw, SP, fetched_at=FA)
    assert [b["close"] for b in bars] == [5.0]


def test_bars_from_fmp_intraday_empty():
    assert bars_from_fmp_intraday([], SP, fetched_at=FA) == []
    assert bars_from_fmp_intraday(None, SP, fetched_at=FA) == []


# ─────────────────────────────── bars_from_yahoo_intraday ───────────────────────────────

WTI = PriceSymbol("wti", "CL=F", "WTI유가", "원자재", 9, "yahoo")
E = [1783080000, 1783080300, 1783080600]      # 5분 간격 epoch(초)


def _yc5(*, closes, opens=None, highs=None, lows=None, volumes=None, epochs=None):
    ts = epochs if epochs is not None else E[:len(closes)]
    q = {"close": closes}
    for name, arr in (("open", opens), ("high", highs), ("low", lows), ("volume", volumes)):
        if arr is not None:
            q[name] = arr
    return {"chart": {"result": [{"meta": {}, "timestamp": ts,
            "indicators": {"quote": [q]}}], "error": None}}


def test_bars_from_yahoo_intraday_epoch_to_iso_with_ohlcv():
    raw = _yc5(closes=[50.0, 51.0, 52.0], opens=[49, 50, 51],
               highs=[50.5, 51.5, 52.5], lows=[48.5, 49.5, 50.5], volumes=[11, 22, 33])
    bars = bars_from_yahoo_intraday(raw, WTI, fetched_at=FA)
    assert [b["close"] for b in bars] == [50.0, 51.0, 52.0]
    assert [b["volume"] for b in bars] == [11.0, 22.0, 33.0]
    assert all(_ISO.match(b["datetime"]) for b in bars)                 # epoch → UTC ISO
    assert bars[0]["source"] == "yahoo" and bars[0]["key"] == "wti"
    assert bars[-1]["id"].startswith("wti__")


def test_bars_from_yahoo_intraday_drops_null_close_and_aligns():
    raw = _yc5(closes=[100.0, None, 102.0], volumes=[11, 22, 33], epochs=E)
    bars = bars_from_yahoo_intraday(raw, WTI, fetched_at=FA)
    assert [(b["close"], b["volume"]) for b in bars] == [(100.0, 11.0), (102.0, 33.0)]


def test_bars_from_yahoo_intraday_empty_or_error():
    assert bars_from_yahoo_intraday({"chart": {"result": None, "error": {"code": "x"}}}, WTI, fetched_at=FA) == []
    assert bars_from_yahoo_intraday({"chart": {"result": []}}, WTI, fetched_at=FA) == []
    assert bars_from_yahoo_intraday({}, WTI, fetched_at=FA) == []
    assert bars_from_yahoo_intraday(None, WTI, fetched_at=FA) == []


# ─────────────────────────────── bars_from_treasury (일봉 1바/일) ───────────────────────────────

US10Y = PriceSymbol("us10y", "UST10Y", "미국채 10년", "금리", 4, "fmp_treasury", "year10")


def test_bars_from_treasury_picks_key_daily():
    bars = bars_from_treasury(_fix("fmp_treasury.json"), US10Y, fetched_at=FA)
    assert [b["close"] for b in bars] == [4.43, 4.45, 4.48]              # 06-30→07-02 오름차순
    assert [b["datetime"] for b in bars] == ["2026-06-30", "2026-07-01", "2026-07-02"]
    assert bars[-1]["id"] == "us10y__20260702" and bars[0]["key"] == "us10y"


def test_bars_from_treasury_year2_and_year30():
    raw = _fix("fmp_treasury.json")
    us2y = PriceSymbol("us2y", "UST2Y", "2Y", "금리", 3, "fmp_treasury", "year2")
    us30y = PriceSymbol("us30y", "UST30Y", "30Y", "금리", 5, "fmp_treasury", "year30")
    assert bars_from_treasury(raw, us2y, fetched_at=FA)[-1]["close"] == 4.71
    assert bars_from_treasury(raw, us30y, fetched_at=FA)[-1]["close"] == 4.66


def test_bars_from_treasury_empty():
    assert bars_from_treasury([], US10Y, fetched_at=FA) == []
    assert bars_from_treasury(None, US10Y, fetched_at=FA) == []


# ─────────────────────────────── run_price_pass (스트림 적재 + 스냅샷) ───────────────────────────────

class _Store:
    """save_price(스냅샷) + filter_new_bar_ids/save_bars(스트림) 계약을 흉내내는 fake."""
    def __init__(self):
        self.saved = {}       # prices/{key} 스냅샷
        self.bars = {}        # price_bars: id -> doc
    def save_price(self, key, data):
        self.saved[key] = data
    def filter_new_bar_ids(self, ids):
        return [i for i in ids if i not in self.bars]
    def save_bars(self, bars):
        for b in bars:
            self.bars[b["id"]] = b
        return len(bars)


def _fetchers(*, fmp_intraday=None, fmp_treasury=None, yahoo_intraday=None):
    calls = {"fmp_intraday": [], "fmp_treasury": 0, "yahoo_intraday": []}

    def _f(sym):
        calls["fmp_intraday"].append(sym)
        return (fmp_intraday or (lambda s: _fmp_intra([("2026-07-10 10:05:00", 101.0),
                                                       ("2026-07-10 10:00:00", 100.0)])))(sym)

    def _t():
        calls["fmp_treasury"] += 1
        return (fmp_treasury or (lambda: _fix("fmp_treasury.json")))()

    def _y(sym):
        calls["yahoo_intraday"].append(sym)
        return (yahoo_intraday or (lambda s: _yc5(closes=[99.0, 100.0], epochs=E[:2])))(sym)

    return {"fmp_intraday": _f, "fmp_treasury": _t, "yahoo_intraday": _y}, calls


def test_run_price_pass_dispatches_by_source_and_streams_bars():
    syms = [SP,
            US10Y,
            WTI]
    store = _Store()
    fetchers, calls = _fetchers()
    n = run_price_pass(store, fetchers, syms)
    assert calls["fmp_intraday"] == ["^GSPC"] and calls["yahoo_intraday"] == ["CL=F"]
    assert n == 2 + 3 + 2                                      # sp500 2바 + treasury 3일 + wti 2바
    assert set(store.saved) == {"sp500", "us10y", "wti"}       # 스냅샷 3종
    assert store.saved["us10y"]["close"] == 4.48               # treasury year10 최신
    assert store.saved["wti"]["close"] == 100.0                # yahoo 최신 봉
    assert {b["key"] for b in store.bars.values()} == {"sp500", "us10y", "wti"}


def test_run_price_pass_fetches_treasury_once_for_all_maturities():
    syms = [PriceSymbol("us2y", "UST2Y", "2Y", "금리", 0, "fmp_treasury", "year2"),
            US10Y,
            PriceSymbol("us30y", "UST30Y", "30Y", "금리", 2, "fmp_treasury", "year30")]
    store = _Store()
    fetchers, calls = _fetchers()
    run_price_pass(store, fetchers, syms)
    assert calls["fmp_treasury"] == 1                          # 캐시 — 1회
    assert store.saved["us2y"]["close"] == 4.71 and store.saved["us30y"]["close"] == 4.66


def test_run_price_pass_writes_only_new_bars_on_repeat():
    # 멱등/dedup: 같은 바를 다시 받으면 새 바 0개(filter_new_bar_ids로 걸러짐).
    store = _Store()
    fetchers, _ = _fetchers()
    first = run_price_pass(store, fetchers, [SP])
    second = run_price_pass(store, fetchers, [SP])
    assert first == 2 and second == 0
    assert len(store.bars) == 2                                # 중복 문서 안 쌓임


def test_run_price_pass_snapshot_stamps_source_fetched_at_flags():
    store = _Store()
    fetchers, _ = _fetchers()
    run_price_pass(store, fetchers, [SP])
    d = store.saved["sp500"]
    assert d["source"] == "fmp" and d["group"] == "지수" and d["order"] == 0
    assert _ISO.match(d["fetched_at"]) and d["flags"] == []   # 신선도 + 정상범위
    assert [p["c"] for p in d["series"]] == [100.0, 101.0]     # 최근 시계열


def test_run_price_pass_flags_out_of_range_non_destructively():
    # 상식범위 플래그: 지수 ±15%·환율 ±5% 초과는 삭제 없이 flag만. 값·바는 보존.
    syms = [PriceSymbol("sp500", "^GSPC", "S&P500", "지수", 0, "fmp"),
            PriceSymbol("usdkrw", "USDKRW", "원/달러", "환율", 1, "fmp")]
    store = _Store()
    fetchers, _ = _fetchers(
        fmp_intraday=lambda s: (_fmp_intra([("2026-07-10 10:05:00", 120.0), ("2026-07-10 10:00:00", 100.0)])
                                if s == "^GSPC"
                                else _fmp_intra([("2026-07-10 10:05:00", 108.0), ("2026-07-10 10:00:00", 100.0)])))
    run_price_pass(store, fetchers, syms)
    assert store.saved["sp500"]["flags"] == ["percent_change_out_of_range"]
    assert store.saved["sp500"]["close"] == 120.0             # 값 비파괴 보존
    assert store.saved["usdkrw"]["flags"] == ["percent_change_out_of_range"]


def test_run_price_pass_fx_within_range_not_flagged():
    store = _Store()
    fetchers, _ = _fetchers(
        fmp_intraday=lambda s: _fmp_intra([("2026-07-10 10:05:00", 103.0), ("2026-07-10 10:00:00", 100.0)]))
    run_price_pass(store, fetchers, [PriceSymbol("usdjpy", "USDJPY", "엔/달러", "환율", 0, "fmp")])
    assert store.saved["usdjpy"]["flags"] == []               # +3% (±5% 안)


def test_run_price_pass_skips_failed_fetch_non_destructively():
    store = _Store()
    fetchers, _ = _fetchers(
        yahoo_intraday=lambda s: {"chart": {"result": None, "error": {"code": "Not Found"}}})
    n = run_price_pass(store, fetchers, [PriceSymbol("kosdaq", "^KQ11", "코스닥", "지수", 0, "yahoo")])
    assert n == 0 and store.saved == {} and store.bars == {}  # 저장 안 함(비파괴)


def test_run_price_pass_one_failure_does_not_block_others():
    def boom(s):
        raise RuntimeError("network down")
    store = _Store()
    fetchers, _ = _fetchers(yahoo_intraday=boom)
    n = run_price_pass(store, fetchers,
                       [PriceSymbol("kosdaq", "^KQ11", "코스닥", "지수", 0, "yahoo"), SP])
    assert set(store.saved) == {"sp500"}                      # 한 심볼 실패가 나머지를 막지 않음


# ─────────────────────────────── week_windows (5분봉 1년 백필 페이지네이션) ───────────────────────────────

def test_week_windows_covers_lookback_newest_first():
    ws = week_windows(14, date(2026, 7, 13))
    assert ws[0] == ("2026-07-07", "2026-07-13")          # 최신 주(≤7일)
    assert all(a <= b for a, b in ws)                     # from ≤ to
    assert all((date.fromisoformat(b) - date.fromisoformat(a)).days <= 6 for a, b in ws)  # 각 창 ≤7일
    assert min(a for a, _ in ws) == "2026-06-29"          # lookback 하한(today-14)까지 덮음
    assert len(ws) == 3


def test_week_windows_one_year_has_about_52_windows():
    ws = week_windows(365, date(2026, 7, 13))
    assert 52 <= len(ws) <= 54                            # 1년 ≈ 52~53주(경계 포함)


def test_run_intraday_backfill_dedups_across_windows():
    store = _Store()
    def fw(sym, frm, to):                                 # 어느 창이든 같은 바 반환
        return _fmp_intra([("2026-07-10 10:00:00", 100.0)])
    n = run_intraday_backfill(store, fw, [SP], [("a", "b"), ("c", "d")], fetched_at=FA)
    assert n == 1                                         # 2창 같은 바 → 새 바 1개(멱등 dedup)
    assert len(store.bars) == 1


def test_run_intraday_backfill_iterates_symbols_times_windows():
    store = _Store()
    seen = []
    def fw(sym, frm, to):
        seen.append((sym, frm, to))
        return _fmp_intra([(f"2026-07-10 10:00:00", 100.0 + len(seen))])
    run_intraday_backfill(store, fw, [SP, WTI], week_windows(14, date(2026, 7, 13)), fetched_at=FA)
    assert len(seen) == 2 * 3                             # 2 심볼 × 3 창


def test_run_intraday_backfill_one_failure_does_not_block_others():
    store = _Store()
    def fw(sym, frm, to):
        if sym == "^GSPC":
            raise RuntimeError("net")
        return _fmp_intra([("2026-07-10 10:00:00", 50.0)])
    n = run_intraday_backfill(store, fw, [SP, WTI], [("a", "b")], fetched_at=FA)
    assert n == 1 and {b["key"] for b in store.bars.values()} == {"wti"}
