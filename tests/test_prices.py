"""가격 수집(FMP + Yahoo 하이브리드) — 순수 파싱·로드·디스패치·계약. HTTP는 주입(fake)이라 네트워크 불요."""
import json
import re
from pathlib import Path

import pytest

from newsstore.collect.prices import (load_price_symbols, parse_yahoo_chart,
                                      parse_fmp_quote_history, parse_fmp_treasury,
                                      run_price_pass, PriceSymbol)

REPO = Path(__file__).resolve().parents[1]
FIX = REPO / "tests" / "fixtures"
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T")


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
    # 프로즌 계약(IMP-web): 모든 심볼이 명시 group을 갖고, 허용 집합 안이다(주석 SSOT를 데이터로).
    for s in load_price_symbols(str(REPO / "config" / "prices.yaml")):
        assert s.group in ALLOWED_GROUPS, f"{s.key} group={s.group!r} 미허용"


def test_real_prices_yaml_order_is_yaml_sequence():
    # order = yaml 등장 순서(enumerate). web이 무순서 Firestore에서 순서 복원하는 근거.
    syms = load_price_symbols(str(REPO / "config" / "prices.yaml"))
    assert [s.order for s in syms] == list(range(len(syms)))   # 0..n-1 연속(불변식)


def test_real_prices_yaml_fmp_symbol_mapping_matches_grounding():
    # §5 접지 검증(환각 금지): FMP 심볼이 실측 매핑 그대로여야 한다.
    syms = {s.key: s for s in load_price_symbols(str(REPO / "config" / "prices.yaml"))}
    assert (syms["nasdaq"].symbol, syms["nasdaq"].source) == ("^IXIC", "fmp")
    assert (syms["sp500"].symbol, syms["sp500"].source) == ("^GSPC", "fmp")
    assert (syms["vix"].symbol, syms["vix"].source) == ("^VIX", "fmp")
    assert (syms["usdkrw"].symbol, syms["usdkrw"].source) == ("USDKRW", "fmp")   # =X 없음
    assert (syms["usdjpy"].symbol, syms["usdjpy"].source) == ("USDJPY", "fmp")
    assert (syms["gold"].symbol, syms["gold"].source) == ("GCUSD", "fmp")


def test_real_prices_yaml_treasury_mapping():
    # 미국채는 FMP treasury-rates가 권위 소스 — year2/year10/year30 매핑 정확해야 한다.
    syms = {s.key: s for s in load_price_symbols(str(REPO / "config" / "prices.yaml"))}
    assert (syms["us2y"].source, syms["us2y"].treasury_key) == ("fmp_treasury", "year2")
    assert (syms["us10y"].source, syms["us10y"].treasury_key) == ("fmp_treasury", "year10")
    assert (syms["us30y"].source, syms["us30y"].treasury_key) == ("fmp_treasury", "year30")


def test_real_prices_yaml_yahoo_fallback_is_exactly_three():
    # Yahoo 폴백은 FMP Premium 미커버 3종(kosdaq·dxy·wti)에만 — 조용히 늘거나 줄면 안 된다.
    syms = load_price_symbols(str(REPO / "config" / "prices.yaml"))
    yahoo = {s.key for s in syms if s.source == "yahoo"}
    assert yahoo == {"kosdaq", "dxy", "wti"}


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
    # source 미기재도 fail-loud(모르는 값과 동일 취급 — None은 화이트리스트 밖).
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
    # frozen 후방호환: 기존 3-인자 위치생성이 그대로 동작(group·order·treasury_key=None, source=fmp default).
    s = PriceSymbol("sp500", "^GSPC", "S&P500")
    assert s.group is None and s.order is None and s.source == "fmp" and s.treasury_key is None


# ─────────────────────────────── parse_yahoo_chart (폴백 파서 유지) ───────────────────────────────

# Yahoo epoch(초) — 실제 날짜(2026-06-30·07-01·07-02 UTC 자정)
E = [1782777600, 1782864000, 1782950400]


def _yc(closes, *, epochs=None, chart_prev=None, currency="USD", price=None, volumes=None):
    """Yahoo chart 응답 fake — closes=오래된→최신(Yahoo 순서). chart_prev=meta.chartPreviousClose.
    volumes=indicators.quote[0].volume(WB1 — 주식 거래량, 같은 콜)."""
    ts = epochs if epochs is not None else E[:len(closes)]
    meta = {"regularMarketPrice": price if price is not None else closes[-1], "currency": currency}
    if chart_prev is not None:
        meta["chartPreviousClose"] = chart_prev
    quote = {"close": closes}
    if volumes is not None:
        quote["volume"] = volumes
    return {"chart": {"result": [{"meta": meta, "timestamp": ts,
            "indicators": {"quote": [quote]}}], "error": None}}


def test_parse_yahoo_ok_value_and_chart():
    q = parse_yahoo_chart(_yc([746.77, 745.76, 744.78], price=744.78))
    assert q["close"] == 744.78 and q["currency"] == "USD"
    assert abs(q["percent_change"] - ((744.78 - 745.76) / 745.76 * 100)) < 1e-9
    assert [p["c"] for p in q["series"]] == [746.77, 745.76, 744.78]
    assert all(_DATE.match(p["t"]) for p in q["series"])
    assert q["datetime"] == q["series"][-1]["t"]


def test_parse_yahoo_close_from_series_not_live_price():
    # ^KS200 회귀: 시계열이 stale이고 라이브 regularMarketPrice가 달라도 값·등락은 시계열에서.
    q = parse_yahoo_chart(_yc([1454.0, 1366.0], price=1299.0))
    assert q["close"] == 1366.0
    assert abs(q["percent_change"] - ((1366.0 - 1454.0) / 1454.0 * 100)) < 1e-9


def test_parse_yahoo_drops_null_closes():
    q = parse_yahoo_chart(_yc([100.0, None, 102.0], epochs=E, price=102.0))
    assert [p["c"] for p in q["series"]] == [100.0, 102.0]
    assert abs(q["percent_change"] - ((102.0 - 100.0) / 100.0 * 100)) < 1e-9


def test_parse_yahoo_volume_aligns_after_null_close_drop():
    q = parse_yahoo_chart(_yc([100.0, None, 102.0], epochs=E, volumes=[11, 22, 33], price=102.0))
    assert [(p["c"], p["v"]) for p in q["series"]] == [(100.0, 11.0), (102.0, 33.0)]


def test_parse_yahoo_error_or_empty():
    assert parse_yahoo_chart({"chart": {"result": None, "error": {"code": "Not Found"}}}) is None
    assert parse_yahoo_chart({"chart": {"result": []}}) is None
    assert parse_yahoo_chart({}) is None
    assert parse_yahoo_chart(None) is None
    assert parse_yahoo_chart({"chart": {"result": [{"meta": {}, "timestamp": [],
            "indicators": {"quote": [{"close": []}]}}]}}) is None


# ─────────────────────────────── parse_fmp_quote_history ───────────────────────────────

def _fmp_quote(price=None, timestamp=1783036800):
    return [{"symbol": "^GSPC", "price": price, "timestamp": timestamp}]


def _fmp_hist(rows_newest_first):
    # rows = [(date, close, volume?)] 최신순(FMP 순서). volume 생략 가능.
    out = []
    for r in rows_newest_first:
        d = {"symbol": "^GSPC", "date": r[0], "close": r[1]}
        if len(r) > 2 and r[2] is not None:
            d["volume"] = r[2]
        out.append(d)
    return out


def test_parse_fmp_history_derives_from_series_oldest_to_newest():
    # FMP는 최신순 → 날짜 오름차순 정렬. 값=series[-1], 전일=series[-2]에서 등락 도출(§2).
    hist = _fmp_hist([("2026-07-02", 101.0, 30), ("2026-07-01", 100.0, 20), ("2026-06-30", 99.0, 10)])
    q = parse_fmp_quote_history(_fmp_quote(price=101.0), hist)
    assert [p["c"] for p in q["series"]] == [99.0, 100.0, 101.0]     # 오래된→최신
    assert [p["v"] for p in q["series"]] == [10.0, 20.0, 30.0]
    assert q["close"] == 101.0
    assert abs(q["percent_change"] - ((101.0 - 100.0) / 100.0 * 100)) < 1e-9   # 전일=100
    assert q["datetime"] == "2026-07-02" and q["currency"] is None


def test_parse_fmp_history_from_fixture_shape():
    # 실 FMP 응답 형태(픽스처)로 파싱 — 그라운딩된 필드명(close·date·volume) 검증.
    q = parse_fmp_quote_history(_fix("fmp_quote_sp500.json"), _fix("fmp_history_sp500.json"))
    assert q["close"] == 6187.68 and q["datetime"] == "2026-07-02"
    assert [p["c"] for p in q["series"]] == [6144.15, 6155.63, 6187.68]
    assert abs(q["percent_change"] - ((6187.68 - 6155.63) / 6155.63 * 100)) < 1e-9


def test_parse_fmp_light_uses_price_field():
    # /light 응답은 close 대신 price. 파서가 둘 다 받는다.
    rows = [{"symbol": "^GSPC", "date": "2026-07-02", "price": 50.0},
            {"symbol": "^GSPC", "date": "2026-07-01", "price": 48.0}]
    q = parse_fmp_quote_history([], rows)
    assert q["close"] == 50.0 and [p["c"] for p in q["series"]] == [48.0, 50.0]


def test_parse_fmp_empty_history_falls_back_to_quote_price():
    # 시계열이 비면 quote 라이브 price로 값만 채운다(등락은 전일 없음 → None).
    q = parse_fmp_quote_history(_fmp_quote(price=123.0), [])
    assert q["close"] == 123.0 and q["change"] is None and q["percent_change"] is None
    assert q["datetime"] == "2026-07-03"       # timestamp=1783036800 → UTC 날짜(E[2]+1일)


def test_parse_fmp_no_close_anywhere_is_none():
    assert parse_fmp_quote_history([], []) is None
    assert parse_fmp_quote_history(None, None) is None


# ─────────────────────────────── parse_fmp_treasury ───────────────────────────────

def test_parse_fmp_treasury_picks_key_and_derives():
    q = parse_fmp_treasury(_fix("fmp_treasury.json"), "year10")
    assert [p["c"] for p in q["series"]] == [4.43, 4.45, 4.48]       # 06-30→07-02 오름차순
    assert q["close"] == 4.48
    assert abs(q["percent_change"] - ((4.48 - 4.45) / 4.45 * 100)) < 1e-9
    assert q["datetime"] == "2026-07-02"


def test_parse_fmp_treasury_year2_and_year30():
    raw = _fix("fmp_treasury.json")
    assert parse_fmp_treasury(raw, "year2")["close"] == 4.71
    assert parse_fmp_treasury(raw, "year30")["close"] == 4.66


def test_parse_fmp_treasury_empty_is_none():
    assert parse_fmp_treasury([], "year10") is None
    assert parse_fmp_treasury(None, "year10") is None


# ─────────────────────────────── run_price_pass (source 디스패치) ───────────────────────────────

class _Store:
    def __init__(self): self.saved = {}
    def save_price(self, key, data): self.saved[key] = data


def _fetchers(*, fmp_quote=None, fmp_history=None, fmp_treasury=None, yahoo=None):
    calls = {"fmp_quote": [], "fmp_history": [], "fmp_treasury": 0, "yahoo": []}

    def _q(sym):
        calls["fmp_quote"].append(sym)
        return (fmp_quote or (lambda s: _fmp_quote(price=101.0)))(sym)

    def _h(sym):
        calls["fmp_history"].append(sym)
        return (fmp_history or (lambda s: _fmp_hist([("2026-07-02", 101.0), ("2026-07-01", 100.0)])))(sym)

    def _t():
        calls["fmp_treasury"] += 1
        return (fmp_treasury or (lambda: _fix("fmp_treasury.json")))()

    def _y(sym):
        calls["yahoo"].append(sym)
        return (yahoo or (lambda s: _yc([99.0, 100.0], price=100.0)))(sym)

    return {"fmp_quote": _q, "fmp_history": _h, "fmp_treasury": _t, "yahoo": _y}, calls


def test_run_price_pass_dispatches_by_source():
    syms = [PriceSymbol("sp500", "^GSPC", "S&P500", "지수", 0, "fmp"),
            PriceSymbol("us10y", "UST10Y", "미국채 10년", "금리", 1, "fmp_treasury", "year10"),
            PriceSymbol("wti", "CL=F", "WTI유가", "원자재", 2, "yahoo")]
    store = _Store()
    fetchers, calls = _fetchers()
    n = run_price_pass(store, fetchers, syms)
    assert n == 3 and set(store.saved) == {"sp500", "us10y", "wti"}
    assert calls["fmp_quote"] == ["^GSPC"] and calls["fmp_history"] == ["^GSPC"]   # fmp만 quote/history
    assert calls["yahoo"] == ["CL=F"]                                             # yahoo만 chart
    assert store.saved["us10y"]["close"] == 4.48                                  # treasury year10 도출
    assert store.saved["wti"]["close"] == 100.0                                   # yahoo series[-1]


def test_run_price_pass_fetches_treasury_once_for_all_maturities():
    # treasury-rates는 한 콜로 전 만기를 준다 — pass당 1회만 fetch(3종 심볼 공유).
    syms = [PriceSymbol("us2y", "UST2Y", "2Y", "금리", 0, "fmp_treasury", "year2"),
            PriceSymbol("us10y", "UST10Y", "10Y", "금리", 1, "fmp_treasury", "year10"),
            PriceSymbol("us30y", "UST30Y", "30Y", "금리", 2, "fmp_treasury", "year30")]
    store = _Store()
    fetchers, calls = _fetchers()
    n = run_price_pass(store, fetchers, syms)
    assert n == 3 and calls["fmp_treasury"] == 1                                  # 캐시 — 1회
    assert store.saved["us2y"]["close"] == 4.71 and store.saved["us30y"]["close"] == 4.66


def test_run_price_pass_stamps_source_fetched_at_and_flags():
    syms = [PriceSymbol("sp500", "^GSPC", "S&P500", "지수", 0, "fmp")]
    store = _Store()
    fetchers, _ = _fetchers()
    run_price_pass(store, fetchers, syms)
    d = store.saved["sp500"]
    assert d["source"] == "fmp" and d["group"] == "지수" and d["order"] == 0
    assert _ISO.match(d["fetched_at"])           # 신선도 스탬프(§2)
    assert d["flags"] == []                       # 정상 등락(±1%) — 상식범위 안


def test_run_price_pass_flags_out_of_range_non_destructively():
    # 상식범위 플래그(§2): 지수 ±15%·환율 ±5% 초과는 삭제 없이 flag만. 값은 보존.
    syms = [PriceSymbol("sp500", "^GSPC", "지수", "지수", 0, "fmp"),      # +20% 인덱스
            PriceSymbol("usdkrw", "USDKRW", "환율", "환율", 1, "fmp")]     # +8% 환율
    store = _Store()
    fetchers, _ = _fetchers(
        fmp_history=lambda s: (_fmp_hist([("2026-07-02", 120.0), ("2026-07-01", 100.0)])
                               if s == "^GSPC"
                               else _fmp_hist([("2026-07-02", 108.0), ("2026-07-01", 100.0)])))
    run_price_pass(store, fetchers, syms)
    assert store.saved["sp500"]["flags"] == ["percent_change_out_of_range"]
    assert store.saved["sp500"]["close"] == 120.0                        # 값 비파괴 보존
    assert store.saved["usdkrw"]["flags"] == ["percent_change_out_of_range"]


def test_run_price_pass_fx_within_range_not_flagged():
    syms = [PriceSymbol("usdjpy", "USDJPY", "환율", "환율", 0, "fmp")]     # +3% 환율(±5% 안)
    store = _Store()
    fetchers, _ = _fetchers(
        fmp_history=lambda s: _fmp_hist([("2026-07-02", 103.0), ("2026-07-01", 100.0)]))
    run_price_pass(store, fetchers, syms)
    assert store.saved["usdjpy"]["flags"] == []


def test_run_price_pass_skips_failed_fetch_non_destructively():
    syms = [PriceSymbol("kosdaq", "^KQ11", "코스닥", "지수", 0, "yahoo")]
    store = _Store()
    fetchers, _ = _fetchers(
        yahoo=lambda s: {"chart": {"result": None, "error": {"code": "Not Found"}}})
    n = run_price_pass(store, fetchers, syms)
    assert n == 0 and store.saved == {}          # 저장 안 함(비파괴 — 기존 값 유지)


def test_run_price_pass_one_failure_does_not_block_others():
    syms = [PriceSymbol("kosdaq", "^KQ11", "코스닥", "지수", 0, "yahoo"),
            PriceSymbol("sp500", "^GSPC", "S&P500", "지수", 1, "fmp")]
    store = _Store()

    def boom(s):
        raise RuntimeError("network down")

    fetchers, _ = _fetchers(yahoo=boom)
    n = run_price_pass(store, fetchers, syms)
    assert n == 1 and set(store.saved) == {"sp500"}   # 한 심볼 실패가 나머지를 막지 않음
