"""가격 데이터 수집 — FMP + Yahoo 하이브리드로 지수·수익률·환율·원자재를 prices/{key}에 저장.

목적: 가격 탭(값+차트). SSOT는 config/prices.yaml. HTTP는 주입(테스트 fake) — 이 모듈은
응답 파싱·오케스트레이션만. 소스는 심볼별로 셋 중 하나다(config가 SSOT):
  - fmp          : FMP quote + historical-price-eod(일봉). 대다수 지수·환율·원자재·변동성.
  - fmp_treasury : FMP treasury-rates에서 수익률 도출(year2/year10/year30). 미국채가 권위 소스.
  - yahoo        : Yahoo Finance chart(무키, UA만). FMP Premium 미커버 3종(kosdaq·dxy·wti) 폴백.
엔트리포인트(run_prices)가 FMP client(헤더 apikey)와 Yahoo client(UA)를 배선한다.

market-data-integrity: 값·등락은 라이브 시세가 아니라 시계열에서 도출(stale 라이브를 close로 쓰면
다일간 등락 오답 — parse_yahoo_chart 주석 참조). 저장 dict에 신선도(fetched_at)·소스(source)·상식범위
플래그(flags, 비파괴)를 실어 조용히 틀린 데이터를 검문소가 잡게 한다. 만료(expire_at)는 store가 주입.
"""
from __future__ import annotations
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import yaml

log = logging.getLogger("newsstore.collect.prices")

ALLOWED_SOURCES = {"fmp", "fmp_treasury", "yahoo"}   # config/prices.yaml source 화이트리스트


@dataclass(frozen=True)
class PriceSymbol:
    key: str            # 내부 id — prices/{key} 문서
    symbol: str         # 소스 심볼(fmp: ^GSPC·USDKRW·GCUSD, yahoo: ^KQ11·CL=F, treasury: 표시용)
    label: str
    group: str | None = None            # 분류(지수·금리·환율·원자재·변동성) — 프로즌 계약, IMP-web 소비.
    order: int | None = None            # yaml 등장 순서(load enumerate) — 무순서 Firestore에서 web이 순서 복원.
    source: str = "fmp"                 # fmp | fmp_treasury | yahoo — fetch/parse 디스패치 근거.
    treasury_key: str | None = None     # source=fmp_treasury일 때 treasury-rates 응답의 키(year2 등).


def load_price_symbols(path: str) -> list[PriceSymbol]:
    """config/prices.yaml 로드 + fail-loud(키 중복·필수필드 누락·모르는 source).

    group은 yaml에서 그대로 읽는다(주석 SSOT를 데이터로 — VIX=변동성·달러지수=환율 명시).
    order는 load 시 등장 순서(enumerate) — PriceSymbol/저장 dict에 실어 web이 순서 복원.
    source는 반드시 명시하고 ALLOWED_SOURCES 안이어야 한다. source=fmp_treasury는 treasury_key 필수."""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    rows = raw.get("symbols")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{path}: 'symbols' 리스트가 필요하다")
    out, seen = [], set()
    for i, r in enumerate(rows):
        key, sym = r.get("key"), r.get("symbol")
        if not (isinstance(key, str) and key.strip() and isinstance(sym, str) and sym.strip()):
            raise ValueError(f"{path}: key·symbol 필수 — {r}")
        if key in seen:
            raise ValueError(f"{path}: key 중복 {key!r}")
        seen.add(key)
        src = r.get("source")
        if src not in ALLOWED_SOURCES:
            raise ValueError(f"{path}: {key!r} source는 {sorted(ALLOWED_SOURCES)} 중 하나여야 한다 — {src!r}")
        tkey = r.get("treasury_key")
        if src == "fmp_treasury" and not (isinstance(tkey, str) and tkey.strip()):
            raise ValueError(f"{path}: {key!r} source=fmp_treasury는 treasury_key 필수(year2/year10/year30)")
        out.append(PriceSymbol(key.strip(), sym.strip(), r.get("label", key),
                               r.get("group"), i, src,
                               tkey.strip() if isinstance(tkey, str) else None))
    return out


SERIES_MAX_POINTS = 30           # 차트에 실을 일봉 수(값+차트 = 이 시계열 하나로 도출)

# 상식범위 가이드(§2 market-data-integrity) — %등락이 넘으면 삭제하지 않고 비파괴 플래그만 단다.
# 지수는 ±15%, 환율은 ±5%. 금리·원자재·변동성은 정상 스윙이 커 임계를 두지 않는다.
RANGE_PCT_LIMIT = {"지수": 15.0, "환율": 5.0}


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


def _iso_date(v) -> str | None:
    """FMP date('2026-07-10' 또는 '2026-07-10 16:00:00')에서 날짜 부분만."""
    return v.split(" ")[0] if isinstance(v, str) and v.strip() else None


def _now_iso() -> str:
    """신선도(fetched_at) — 조회 시각(UTC ISO). 스케줄러가 조용히 멈춰도 낡은 값을 걸러내게."""
    return datetime.now(timezone.utc).isoformat()


def _derive(series: list[dict], *, fallback_close=None, fallback_dt=None,
            currency=None) -> dict | None:
    """시계열(오래된→최신)에서 값·등락을 도출해 저장 계약 dict를 만든다(소스 무관 공통).
    close=series[-1], 전일=series[-2]. 시계열이 비면 fallback(라이브 시세)로 값만 채운다."""
    close = series[-1]["c"] if series else fallback_close
    if close is None:
        return None
    prev = series[-2]["c"] if len(series) >= 2 else None
    change = (close - prev) if prev is not None else None
    pct = ((close - prev) / prev * 100.0) if prev not in (None, 0) else None
    return {"close": close, "change": change, "percent_change": pct,
            "datetime": (series[-1]["t"] if series else fallback_dt),
            "currency": currency, "series": series}


def parse_yahoo_chart(raw, *, max_points: int = SERIES_MAX_POINTS) -> dict | None:
    """Yahoo Finance chart API 응답 파싱 → 현재값·등락 + 차트 시계열(값+차트 겸용). yahoo 폴백 전용.
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
    quote0 = (((r0.get("indicators") or {}).get("quote") or [{}])[0] or {})
    quotes = quote0.get("close") or []
    # 거래량(WB1): 같은 콜에 실려온다. **주식만 의미**(FX·수익률지수·선물은 호출자가 무시).
    # 없으면 series 점에 'v' 키 자체를 안 실어(additive·비파괴 — 기존 소비자 무영향).
    volumes = quote0.get("volume") or []
    series = []
    for i, (t, c) in enumerate(zip(ts, quotes)):
        cv, dt = _fnum(c), _epoch_to_date(t)
        if cv is not None and dt is not None:
            pt = {"t": dt, "c": cv}
            vv = _fnum(volumes[i]) if i < len(volumes) else None   # i는 ts 인덱스와 정렬(null close만 드롭)
            if vv is not None:
                pt["v"] = vv
            series.append(pt)
    series = series[-max_points:]                    # 최근 N일(오래된→최신 유지)
    # 값·등락 모두 시계열에서 도출 — 값=series[-1](차트 끝점과 일치), 전일=series[-2].
    # ⚠️ regularMarketPrice(라이브)를 close로 쓰면 시계열이 stale일 때 다일간 등락이 되고
    #    (^KS200 사례 -10%), meta.chartPreviousClose는 range=1mo에선 '한 달 전'이라 둘 다 안 씀.
    return _derive(series, fallback_close=_fnum(meta.get("regularMarketPrice")),
                   fallback_dt=_epoch_to_date(meta.get("regularMarketTime")),
                   currency=meta.get("currency"))


def parse_fmp_quote_history(quote_json, hist_json, *, max_points: int = SERIES_MAX_POINTS) -> dict | None:
    """FMP quote + historical-price-eod 응답 파싱 → 현재값·등락 + 차트 시계열.
    hist_json=[{symbol,date,close,volume,...}] (또는 /light의 price) — FMP는 **최신순**이라
    날짜로 오름차순 정렬해 series(오래된→최신)를 만든다. 값·등락은 시계열에서 도출(§2).
    시계열이 비면 quote의 라이브 price로 값만 폴백. 무close → None(fail-soft)."""
    quote = (quote_json[0] if isinstance(quote_json, list) and quote_json
             and isinstance(quote_json[0], dict) else {})
    rows = hist_json if isinstance(hist_json, list) else []
    series = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        c = _fnum(row.get("close"))
        if c is None:
            c = _fnum(row.get("price"))          # /light 응답은 close 대신 price
        dt = _iso_date(row.get("date"))
        if c is None or dt is None:
            continue
        pt = {"t": dt, "c": c}
        v = _fnum(row.get("volume"))
        if v is not None:
            pt["v"] = v
        series.append(pt)
    series.sort(key=lambda p: p["t"])            # FMP 최신순 → 오래된→최신(ISO 날짜 사전순=시간순)
    series = series[-max_points:]
    return _derive(series, fallback_close=_fnum(quote.get("price")),
                   fallback_dt=_epoch_to_date(quote.get("timestamp")), currency=None)


def parse_fmp_treasury(raw, treasury_key: str, *, max_points: int = SERIES_MAX_POINTS) -> dict | None:
    """FMP treasury-rates 응답에서 한 만기(treasury_key)의 수익률 시계열을 뽑아 값·등락 도출.
    raw=[{date,month1,...,year2,year10,year30}] — 각 행에서 treasury_key 필드를 취해 series 구성.
    수익률은 % 단위이며 값·등락은 시계열에서 도출. 무행/무값 → None(fail-soft)."""
    rows = raw if isinstance(raw, list) else []
    series = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        c = _fnum(row.get(treasury_key))
        dt = _iso_date(row.get("date"))
        if c is None or dt is None:
            continue
        series.append({"t": dt, "c": c})
    series.sort(key=lambda p: p["t"])            # 날짜 오름차순(오래된→최신)
    series = series[-max_points:]
    return _derive(series, currency=None)


def _range_flags(group, pct) -> list[str]:
    """상식범위 플래그(비파괴) — %등락이 group 임계를 넘으면 표시만. 값은 손대지 않는다(검증≠수정)."""
    lim = RANGE_PCT_LIMIT.get(group)
    if lim is not None and pct is not None and abs(pct) > lim:
        return ["percent_change_out_of_range"]
    return []


_UNSET = object()   # treasury-rates는 한 콜로 전 만기를 주므로 pass당 한 번만 fetch(캐시 센티널)


def run_price_pass(store, fetchers: dict, symbols: list[PriceSymbol],
                   *, delay_s: float = 0.0) -> int:
    """각 심볼을 source별로 fetch→parse→store.save_price(key, ...). 반환=저장 수.

    fetchers = {"fmp_quote": fn(symbol), "fmp_history": fn(symbol),
                "fmp_treasury": fn(), "yahoo": fn(symbol)} — HTTP 주입(테스트 fake).
    저장 dict = 파서 계약 + label·symbol·group·order + source·fetched_at·flags(§2). expire_at은 store가 주입.
    개별 심볼 실패(에러 응답·파싱 실패)는 스킵(fail-soft, 비파괴 — 기존 값 유지).
    delay_s: 콜 간 지연(레이트리밋 대응 — 엔트리포인트가 주입)."""
    treasury_raw = _UNSET
    n = 0
    for i, s in enumerate(symbols):
        if delay_s and i:
            time.sleep(delay_s)
        try:
            if s.source == "yahoo":
                q = parse_yahoo_chart(fetchers["yahoo"](s.symbol))
            elif s.source == "fmp":
                q = parse_fmp_quote_history(fetchers["fmp_quote"](s.symbol),
                                            fetchers["fmp_history"](s.symbol))
            elif s.source == "fmp_treasury":
                if treasury_raw is _UNSET:
                    treasury_raw = fetchers["fmp_treasury"]()   # pass당 1회(전 만기 공유)
                q = parse_fmp_treasury(treasury_raw, s.treasury_key)
            else:                                                # load_price_symbols가 막지만 방어적으로
                raise ValueError(f"unknown source {s.source!r}")
        except Exception as e:                       # 네트워크/타임아웃/응답 이상 — 그 심볼만 스킵
            log.warning("price fetch %s(%s, %s) 실패: %s", s.key, s.symbol, s.source, e)
            continue
        if q is None:
            log.warning("price %s(%s, %s): 무효 응답 — 스킵", s.key, s.symbol, s.source)
            continue
        store.save_price(s.key, {**q, "label": s.label, "symbol": s.symbol,
                                 "group": s.group, "order": s.order,   # 프로즌 계약(IMP-web): 분류·순서 병합
                                 "source": s.source, "fetched_at": _now_iso(),
                                 "flags": _range_flags(s.group, q.get("percent_change"))})
        n += 1
    log.info("price pass: %d/%d saved", n, len(symbols))
    return n
