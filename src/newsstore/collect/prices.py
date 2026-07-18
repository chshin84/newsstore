"""가격 데이터 수집 — FMP + Yahoo 하이브리드로 5분봉(인트라데이) 스트림을 수집한다.

목적: 다운스트림 적재용 원천 5분봉 스트림 + 웹 확인용 최신 스냅샷. SSOT는 config/prices.yaml.
HTTP는 주입(테스트 fake) — 이 모듈은 응답 파싱·오케스트레이션만. 소스는 심볼별로 셋 중 하나다:
  - fmp          : FMP historical-chart/5min(인트라데이 OHLCV). 지수·환율·원자재·변동성.
  - fmp_treasury : FMP treasury-rates에서 수익률 도출(year2/10/30). 미국채는 5분봉이 없어 **일봉 1바/일**.
  - yahoo        : Yahoo Finance chart(interval=5m, 무키·UA). FMP Premium 미커버 3종(kosdaq·dxy·wti) 폴백.
엔트리포인트(run_prices)가 FMP client(헤더 apikey)와 Yahoo client(UA)를 배선한다.

저장(두 갈래):
  - price_bars/{key}__{ts} : 바 하나당 문서(완전 스트림). 새 바만 write(filter_new_bar_ids로 dedup).
    멱등 — 겹쳐 받은 바는 같은 id라 재적재 안 함. expire_at(TTL 30일)은 store가 바 날짜에서 주입.
  - prices/{key}           : 최신 스냅샷(값+최근 시계열) — 웹 확인 UI가 읽는다. 매 패스 덮어쓰기.

market-data-integrity: 각 5분봉의 close는 그 봉 자체의 종가라 stale-라이브 오답이 없다. 스냅샷에는
신선도(fetched_at)·상식범위 flags(비파괴)를 실어 조용히 틀린 데이터를 검문소가 잡게 한다.
"""
from __future__ import annotations
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import yaml

log = logging.getLogger("newsstore.collect.prices")

ALLOWED_SOURCES = {"fmp", "fmp_treasury", "yahoo"}   # config/prices.yaml source 화이트리스트


@dataclass(frozen=True)
class PriceSymbol:
    key: str            # 내부 id — prices/{key} 문서, price_bars id 접두
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


SNAPSHOT_MAX_POINTS = 60         # 스냅샷 차트에 실을 최근 봉 수(웹 확인용 — 5분봉 60개 ≈ 5시간)

# 상식범위 가이드(market-data-integrity) — %등락이 넘으면 삭제하지 않고 비파괴 플래그만 단다.
# 지수는 ±15%, 환율은 ±5%. 금리·원자재·변동성은 정상 스윙이 커 임계를 두지 않는다.
RANGE_PCT_LIMIT = {"지수": 15.0, "환율": 5.0}


def _fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _now_iso() -> str:
    """신선도(fetched_at) — 조회 시각(UTC ISO). 스케줄러가 조용히 멈춰도 낡은 값을 걸러내게."""
    return datetime.now(timezone.utc).isoformat()


def _epoch_to_iso(t) -> str | None:
    try:
        return datetime.fromtimestamp(int(t), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def _bar_id(key: str, dt_str: str) -> str:
    """price_bars 문서 id — {key}__{숫자만 뽑은 타임스탬프}. 결정론이라 겹쳐 받아도 멱등."""
    digits = re.sub(r"\D", "", dt_str or "")[:14]     # YYYYMMDDHHMMSS(일봉이면 뒤가 짧다)
    return f"{key}__{digits}"


def _bar(s: PriceSymbol, dt_str: str, *, fetched_at: str,
         o=None, h=None, l=None, c=None, v=None) -> dict:
    """price_bars 문서 1건(바 1개). 소스 무관 공통 shape. datetime은 소스 문자열을 보존한다
    (다운스트림이 해석 — FMP 인트라데이는 거래소 로컬시각, Yahoo/treasury는 UTC/날짜)."""
    bar = {"id": _bar_id(s.key, dt_str), "key": s.key, "symbol": s.symbol,
           "label": s.label, "group": s.group, "order": s.order,
           "source": s.source, "datetime": dt_str, "close": c,
           "fetched_at": fetched_at}
    for name, val in (("open", o), ("high", h), ("low", l), ("volume", v)):
        if val is not None:
            bar[name] = val
    return bar


def bars_from_fmp_intraday(raw, s: PriceSymbol, *, fetched_at: str) -> list[dict]:
    """FMP historical-chart/5min 응답 → 시간순(오래된→최신) 바 리스트.
    raw=[{date,open,high,low,close,volume}] (FMP는 최신순). 무close 봉은 드롭(fail-soft)."""
    rows = raw if isinstance(raw, list) else []
    bars = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        c, dt = _fnum(row.get("close")), row.get("date")
        if c is None or not (isinstance(dt, str) and dt.strip()):
            continue
        bars.append(_bar(s, dt.strip(), fetched_at=fetched_at,
                         o=_fnum(row.get("open")), h=_fnum(row.get("high")),
                         l=_fnum(row.get("low")), c=c, v=_fnum(row.get("volume"))))
    bars.sort(key=lambda b: b["datetime"])           # ISO 문자열 사전순 = 시간순
    return bars


def bars_from_yahoo_intraday(raw, s: PriceSymbol, *, fetched_at: str) -> list[dict]:
    """Yahoo Finance chart(interval=5m) 응답 → 시간순 바 리스트. yahoo 폴백 전용.
    chart.result[0]: timestamp[]·indicators.quote[0].{open,high,low,close,volume}. epoch→UTC ISO."""
    if not isinstance(raw, dict):
        return []
    res = ((raw.get("chart") or {}).get("result")) if isinstance(raw.get("chart"), dict) else None
    if not isinstance(res, list) or not res or not isinstance(res[0], dict):
        return []
    r0 = res[0]
    ts = r0.get("timestamp") or []
    q0 = (((r0.get("indicators") or {}).get("quote") or [{}])[0] or {})
    closes, opens = q0.get("close") or [], q0.get("open") or []
    highs, lows, vols = q0.get("high") or [], q0.get("low") or [], q0.get("volume") or []
    bars = []
    for i, t in enumerate(ts):
        c = _fnum(closes[i]) if i < len(closes) else None
        dt = _epoch_to_iso(t)
        if c is None or dt is None:                  # 휴장 구간 null close는 드롭
            continue
        pick = lambda arr: _fnum(arr[i]) if i < len(arr) else None
        bars.append(_bar(s, dt, fetched_at=fetched_at,
                         o=pick(opens), h=pick(highs), l=pick(lows), c=c, v=pick(vols)))
    bars.sort(key=lambda b: b["datetime"])
    return bars


def bars_from_treasury(raw, s: PriceSymbol, *, fetched_at: str) -> list[dict]:
    """FMP treasury-rates → 일봉 1바/일(수익률 %). 미국채는 5분봉이 없어 날짜 단위.
    raw=[{date,year2,...}] — 각 행에서 treasury_key 필드를 close로. 무값 드롭(fail-soft)."""
    rows = raw if isinstance(raw, list) else []
    bars = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        c, dt = _fnum(row.get(s.treasury_key)), row.get("date")
        if c is None or not (isinstance(dt, str) and dt.strip()):
            continue
        bars.append(_bar(s, dt.strip(), fetched_at=fetched_at, c=c))
    bars.sort(key=lambda b: b["datetime"])
    return bars


def _range_flags(group, pct) -> list[str]:
    """상식범위 플래그(비파괴) — %등락이 group 임계를 넘으면 표시만. 값은 손대지 않는다(검증≠수정)."""
    lim = RANGE_PCT_LIMIT.get(group)
    if lim is not None and pct is not None and abs(pct) > lim:
        return ["percent_change_out_of_range"]
    return []


def _snapshot(bars: list[dict], s: PriceSymbol, *, fetched_at: str) -> dict:
    """웹 확인용 최신 스냅샷 — 값·등락은 최근 봉에서 도출, series=최근 N봉(값+차트 겸용).
    bars는 시간순(오래된→최신)이라고 가정. 빈 리스트면 None."""
    recent = bars[-SNAPSHOT_MAX_POINTS:]
    close = recent[-1]["close"]
    prev = recent[-2]["close"] if len(recent) >= 2 else None
    change = (close - prev) if prev is not None else None
    pct = ((close - prev) / prev * 100.0) if prev not in (None, 0) else None
    series = [{"t": b["datetime"], "c": b["close"], **({"v": b["volume"]} if "volume" in b else {})}
              for b in recent]
    return {"close": close, "change": change, "percent_change": pct,
            "datetime": recent[-1]["datetime"], "currency": None, "series": series,
            "label": s.label, "symbol": s.symbol, "group": s.group, "order": s.order,
            "source": s.source, "fetched_at": fetched_at,
            "flags": _range_flags(s.group, pct)}


_UNSET = object()   # treasury-rates는 한 콜로 전 만기를 주므로 pass당 한 번만 fetch(캐시 센티널)


def run_price_pass(store, fetchers: dict, symbols: list[PriceSymbol],
                   *, delay_s: float = 0.0) -> int:
    """각 심볼을 source별로 fetch→바 추출→(새 바만) price_bars 적재 + prices/{key} 스냅샷 갱신.
    반환 = 이번 패스에 새로 적재한 바 수.

    fetchers = {"fmp_intraday": fn(symbol), "fmp_treasury": fn(), "yahoo_intraday": fn(symbol)} — HTTP 주입.
    개별 심볼 실패(에러 응답·파싱 실패)는 스킵(fail-soft, 비파괴 — 기존 값 유지).
    delay_s: 콜 간 지연(레이트리밋 대응 — 엔트리포인트가 주입)."""
    treasury_raw = _UNSET
    fetched_at = _now_iso()
    total_new = 0
    for i, s in enumerate(symbols):
        if delay_s and i:
            time.sleep(delay_s)
        try:
            if s.source == "yahoo":
                bars = bars_from_yahoo_intraday(fetchers["yahoo_intraday"](s.symbol), s,
                                                fetched_at=fetched_at)
            elif s.source == "fmp":
                bars = bars_from_fmp_intraday(fetchers["fmp_intraday"](s.symbol), s,
                                              fetched_at=fetched_at)
            elif s.source == "fmp_treasury":
                if treasury_raw is _UNSET:
                    treasury_raw = fetchers["fmp_treasury"]()   # pass당 1회(전 만기 공유)
                bars = bars_from_treasury(treasury_raw, s, fetched_at=fetched_at)
            else:                                                # load_price_symbols가 막지만 방어적으로
                raise ValueError(f"unknown source {s.source!r}")
        except Exception as e:                       # 네트워크/타임아웃/응답 이상 — 그 심볼만 스킵
            log.warning("price fetch %s(%s, %s) 실패: %s", s.key, s.symbol, s.source, e)
            continue
        if not bars:
            log.warning("price %s(%s, %s): 무효 응답/무 바 — 스킵", s.key, s.symbol, s.source)
            continue
        # 완결 안 된 마지막 봉은 스트림에 적재하지 않는다(상시 드롭). filter_new_bar_ids가 한 번
        # 쓴 바를 다시 안 써서, 형성 중 봉을 저장하면 불완전값이 그대로 고착된다
        # (market-data-integrity: forming ≠ final). 다음 폴에 완결되면 그때 저장(FMP 히스토리라
        # 손실 없음). 스냅샷은 최신값 표시라 전체 봉을 쓰고 매 패스 덮어써 자가교정한다.
        stream_bars = bars[:-1]
        new_ids = set(store.filter_new_bar_ids([b["id"] for b in stream_bars]))
        saved = store.save_bars([b for b in stream_bars if b["id"] in new_ids])
        total_new += saved
        # 웹 확인용 최신 스냅샷(값+최근 시계열) 갱신.
        store.save_price(s.key, _snapshot(bars, s, fetched_at=fetched_at))
        log.info("price %s: +%d new bar(s) (of %d fetched)", s.key, saved, len(bars))
    log.info("price pass: %d new bar(s) saved across %d symbols", total_new, len(symbols))
    return total_new
