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
    assert {"kosdaq", "nasdaq", "sp500", "us2y", "us10y", "us30y",
            "usdkrw", "usdjpy", "wti", "gold"} <= keys
    assert all(isinstance(s, PriceSymbol) and s.symbol for s in syms)


ALLOWED_GROUPS = {"지수", "금리", "환율", "원자재", "변동성"}


def test_real_prices_yaml_every_symbol_has_valid_group():
    # 프로즌 계약(IMP-web): 모든 심볼이 명시 group을 갖고, 허용 집합 안이다(주석 SSOT를 데이터로).
    syms = load_price_symbols(str(REPO / "config" / "prices.yaml"))
    for s in syms:
        assert s.group in ALLOWED_GROUPS, f"{s.key} group={s.group!r} 미허용"


def test_real_prices_yaml_order_is_yaml_sequence():
    # order = yaml 등장 순서(enumerate). web이 무순서 Firestore에서 순서 복원하는 근거.
    syms = load_price_symbols(str(REPO / "config" / "prices.yaml"))
    assert [s.order for s in syms] == list(range(len(syms)))   # 0..n-1 연속(불변식)


def test_real_prices_yaml_registers_vix_and_dollar_index():
    # 실측 스팟체크 통과분 등재(2026-07-06): VIX=변동성·달러지수(DX-Y.NYB)=환율.
    syms = {s.key: s for s in load_price_symbols(str(REPO / "config" / "prices.yaml"))}
    assert syms["vix"].symbol == "^VIX" and syms["vix"].group == "변동성"
    assert syms["dxy"].symbol == "DX-Y.NYB" and syms["dxy"].group == "환율"


def test_load_reads_group_and_assigns_order(tmp_path):
    p = tmp_path / "g.yaml"
    p.write_text("symbols:\n  - {key: a, symbol: X, label: A, group: 지수}\n"
                 "  - {key: b, symbol: Y, label: B, group: 환율}\n", encoding="utf-8")
    syms = load_price_symbols(str(p))
    assert (syms[0].group, syms[0].order) == ("지수", 0)
    assert (syms[1].group, syms[1].order) == ("환율", 1)


def test_load_symbol_without_group_is_none_backward_compat(tmp_path):
    # 후방호환: group 미기재면 None(additive — web은 undefined로 graceful).
    p = tmp_path / "n.yaml"
    p.write_text("symbols:\n  - {key: a, symbol: X, label: A}\n", encoding="utf-8")
    syms = load_price_symbols(str(p))
    assert syms[0].group is None and syms[0].order == 0


def test_price_symbol_positional_three_args_still_construct():
    # frozen 후방호환: 기존 3-인자 위치생성(테스트·호출부)이 그대로 동작(group·order 말미 default).
    s = PriceSymbol("sp500", "^GSPC", "S&P500")
    assert s.group is None and s.order is None


def test_run_price_pass_merges_group_and_order_into_saved():
    # 프로즌 계약: 저장 dict에 group(str)·order(int) 병합(IMP-web 소비).
    syms = [PriceSymbol("sp500", "^GSPC", "S&P500", "지수", 0),
            PriceSymbol("vix", "^VIX", "VIX변동성", "변동성", 1)]
    store = _Store()
    run_price_pass(store, lambda s: _yc([100.0, 101.0], price=101.0), syms)
    assert store.saved["sp500"]["group"] == "지수" and store.saved["sp500"]["order"] == 0
    assert store.saved["vix"]["group"] == "변동성" and store.saved["vix"]["order"] == 1


def test_load_fails_loud_on_dup_key(tmp_path):
    p = tmp_path / "d.yaml"
    p.write_text("symbols:\n  - {key: a, symbol: X, label: A}\n  - {key: a, symbol: Y, label: B}\n",
                 encoding="utf-8")
    with pytest.raises(ValueError, match="중복"):
        load_price_symbols(str(p))


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


def test_parse_yahoo_volume_added_when_present():
    # WB1: 거래량이 있으면 series 점에 'v'로 실린다(같은 콜). 없으면 'v' 키 자체가 없다(additive).
    q = parse_yahoo_chart(_yc([100.0, 101.0, 102.0], volumes=[10, 20, 30], price=102.0))
    assert [p["v"] for p in q["series"]] == [10.0, 20.0, 30.0]
    assert [p["c"] for p in q["series"]] == [100.0, 101.0, 102.0]     # close 불변
    q2 = parse_yahoo_chart(_yc([100.0, 101.0], price=101.0))          # 거래량 미수신
    assert all("v" not in p for p in q2["series"])                    # 'v' 없음(비파괴)


def test_parse_yahoo_volume_aligns_after_null_close_drop():
    # null close는 드롭되지만 거래량은 timestamp 인덱스에 정렬(밀림 없음).
    q = parse_yahoo_chart(_yc([100.0, None, 102.0], epochs=E, volumes=[11, 22, 33], price=102.0))
    assert [(p["c"], p["v"]) for p in q["series"]] == [(100.0, 11.0), (102.0, 33.0)]  # null행 통째 드롭


def test_parse_yahoo_ok_value_and_chart():
    # regularMarketPrice=현재값, 전일=series[-2] → 등락. series=오래된→최신 {날짜,c}.
    q = parse_yahoo_chart(_yc([746.77, 745.76, 744.78], price=744.78))
    assert q["close"] == 744.78 and q["currency"] == "USD"
    assert abs(q["percent_change"] - ((744.78 - 745.76) / 745.76 * 100)) < 1e-9   # 전일=745.76
    assert [p["c"] for p in q["series"]] == [746.77, 745.76, 744.78]   # 오래된→최신
    assert all(_DATE.match(p["t"]) for p in q["series"])               # t=날짜 문자열
    assert q["datetime"] == q["series"][-1]["t"]                       # 최신 날짜


def test_parse_yahoo_daychange_ignores_month_ago_chartprevclose():
    # 회귀 가드: range=1mo의 meta.chartPreviousClose는 '한 달 전'이라 일간 등락에 쓰면 오답
    # (코스닥 ▼15% 사고). 전일 등락은 series[-2]에서 도출해야 한다.
    q = parse_yahoo_chart(_yc([900.0, 1000.0, 1010.0], chart_prev=900.0, price=1010.0))
    assert abs(q["percent_change"] - ((1010.0 - 1000.0) / 1000.0 * 100)) < 1e-9   # 전일=1000, +1%
    assert abs(q["percent_change"]) < 2                                # 월간(+12%) 아님


def test_parse_yahoo_close_from_series_not_live_price():
    # ^KS200 회귀: 시계열이 stale이고 라이브 regularMarketPrice가 달라도 값·등락은 시계열에서
    # (라이브 vs stale 시계열 비교가 -10% 같은 다일간 오답을 냈던 사고).
    q = parse_yahoo_chart(_yc([1454.0, 1366.0], price=1299.0))    # 라이브=1299, 시계열 끝=1366
    assert q["close"] == 1366.0                                   # 값=series[-1](라이브 아님)
    assert abs(q["percent_change"] - ((1366.0 - 1454.0) / 1454.0 * 100)) < 1e-9  # 전일=series[-2]


def test_parse_yahoo_no_prior_day_no_change():
    q = parse_yahoo_chart(_yc([100.0], price=100.0))                   # 시계열 1점 → 전일 없음
    assert q["close"] == 100.0 and q["change"] is None and q["percent_change"] is None
    assert [p["c"] for p in q["series"]] == [100.0]


def test_parse_yahoo_drops_null_closes():
    # Yahoo는 휴장일 close에 null을 낀다 — 걸러야 함(길이 불일치 zip 안전).
    q = parse_yahoo_chart(_yc([100.0, None, 102.0], epochs=E, price=102.0))
    assert [p["c"] for p in q["series"]] == [100.0, 102.0]             # null 드롭
    assert abs(q["percent_change"] - ((102.0 - 100.0) / 100.0 * 100)) < 1e-9   # 전일=100(null 건너뜀)


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
        return _yc([100.0, 101.0], price=101.0)
    store = _Store()
    n = run_price_pass(store, fake_fetch, syms)
    assert n == 2 and set(store.saved) == {"sp500", "wti"}
    assert store.saved["sp500"]["close"] == 101.0 and store.saved["sp500"]["label"] == "S&P500"
    assert store.saved["sp500"]["symbol"] == "^GSPC"
    assert len(store.saved["sp500"]["series"]) == 2               # 차트 시계열 저장
    assert "^GSPC" in calls and "CL=F" in calls


def test_run_price_pass_uses_custom_save():
    # 종목 히스토리: save=store.save_stock_price로 stock_prices에 저장(가격 앵커와 분리).
    saved = {}
    class _S2:
        def save_price(self, k, d): saved[("price", k)] = d
        def save_stock_price(self, k, d): saved[("stock", k)] = d
    store = _S2()
    syms = [PriceSymbol("005930", "005930.KS", "삼성전자")]
    n = run_price_pass(store, lambda s: _yc([99.0, 100.0], price=100.0),
                       syms, save=store.save_stock_price)
    assert n == 1 and ("stock", "005930") in saved and ("price", "005930") not in saved
    assert saved[("stock", "005930")]["close"] == 100.0 and saved[("stock", "005930")]["symbol"] == "005930.KS"


def test_run_price_pass_skips_failed_fetch():
    syms = [PriceSymbol("kosdaq", "^KQ11", "코스닥")]
    def fake_fetch(symbol):
        return {"chart": {"result": None, "error": {"code": "Not Found"}}}   # 미지원 → 스킵(fail-soft)
    store = _Store()
    n = run_price_pass(store, fake_fetch, syms)
    assert n == 0 and store.saved == {}                              # 저장 안 함(비파괴)
