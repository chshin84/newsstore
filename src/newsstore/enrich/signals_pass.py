"""신호 패스 (오케스트레이션) — signals 엔진을 Firestore·긴 베이스라인 series에 배선.

세 산출(프로즌 계약, V2-web 소비):
- WB3 스토리 doc `landing`  — 스토리→티커→지수 대비 초과수익(베타제거). 회고 base-rate(매매신호 아님).
- WB4 `signals/unexplained_moves` — 큰 z이동+(주식)거래량+서사 미커버 → 조사 큐(백엔드가 rank 확정).
- WB5 스토리 doc `breadth`  — 자산군 폭 + 베타제거 후 초과이동 확인(리스크오프 공동하락 배제).

**모든 산출 doc·필드에 unverified:true**(검증 전 — 조사 트리아지/가설이지 conviction 아님). 테스트가 강제.
저장은 store.db(주입 클라이언트) 경유 — 이 패스가 소유한 신규 컬렉션/필드만 additive로 쓴다
(기존 story cluster/summary/score/article 필드는 merge=True로 불변; report/frames 생성 무변경).

**모듈 경계**: enrich는 collect를 import하지 않는다(test_module_boundaries). 긴 베이스라인 Yahoo
페치·파싱은 **엔트리포인트**(collect+store 접근 가능)가 하고, 여기엔 파싱된 series 맵만 주입한다.
덕에 이 패스의 WB3/4/5 로직은 네트워크·collect 없이 series 맵 주입만으로 온전히 테스트된다.
"""
from __future__ import annotations
import logging
from datetime import timedelta

from . import signals as _sig
from . import topics as _topics

log = logging.getLogger("newsstore.enrich.signals_pass")

# 긴 베이스라인 파싱 상한(엔트리포인트가 parse_yahoo_chart max_points로 사용) — 30일 스파크와 분리.
BASELINE_MAX_POINTS = 400          # range=1y(≈250거래일) 여유 상한
SIGNALS_WINDOW = timedelta(hours=72)   # 최근 창(리포트와 동일 지평) — open 스토리 커버리지·착지 창
MARKET_FACTOR_KEY = "sp500"        # 브레드스 베타제거의 공통 시장인자(리스크오프 공동변동 제거축)
# ⚠ 한계(정직): 단일인자(sp500) 베타제거는 **주식 레그에만** 엄밀히 유효하다. FX·금리·귀금속은
# sp500 베타가 불안정/≈0이라 공동변동 제거가 약하고, kr_equity(kosdaq)는 미장 대비 종가 시차(~13h)로
# 베타가 감쇠한다. 그래서 breadth는 unverified:true(가설·트리아지)로만 노출한다. 다인자 리스크모델은
# Phase-2. 그럼에도 표본 게이트 + BREADTH_MIN_ANCHOR≥2로 명백한 공동하락 오인은 억제한다.
# 거래량이 유의미한 '주식성' 가격키(개별종목 + 주식지수). 나머지(FX·수익률지수·선물)=vol null.
STOCK_INDEX_KEYS = frozenset({"sp500", "nasdaq", "kosdaq"})


def _benchmark_key_for_ticker(ticker: str) -> str:
    """watch 티커의 시장지수(베타제거 기준). 한국(숫자 티커)=kosdaq, 그 외=sp500(광의 시장)."""
    return "kosdaq" if str(ticker).isdigit() else MARKET_FACTOR_KEY


def _open_stories(store, cutoff) -> list[dict]:
    """window 안의 open 스토리 — signals가 쓰는 필드만(entities·lenses·제목·first_seen).
    store.db 직접 조회(store 계약 미변경 소유권 — signals 전용 신규 읽기)."""
    out = []
    for snap in store.db.collection("stories").where("status", "==", "open").stream():
        d = snap.to_dict() or {}
        ls = d.get("last_seen")
        if not (ls and ls >= cutoff):
            continue
        out.append({"id": snap.id, "title": d.get("title") or "",
                    "entities": d.get("entities") or [], "lenses": d.get("lenses") or [],
                    "first_seen": d.get("first_seen"), "last_seen": ls})
    return out


def _window_dates(first_seen, now) -> tuple[str, str]:
    """스토리 창 [start,end] ISO 날짜문자열(포함). first_seen 없으면 최근창 시작으로 폴백.
    날짜문자열 비교라 tz 3축 무관."""
    start = (first_seen or (now - SIGNALS_WINDOW)).date().isoformat()
    return start, now.date().isoformat()


def run_signals_pass(store, *, stock_series: dict, price_series: dict,
                     price_label: dict | None = None, now,
                     topics_path: str = "config/topics.yaml") -> dict:
    """v2 신호 패스 진입 — 파싱된 긴 베이스라인 series 맵을 주입받아 배선(페치는 엔트리포인트).
      stock_series: {ticker: [ {t,c,v?} ...]}     (watch 종목 일봉·거래량)
      price_series: {price_key: [ {t,c,v?} ...]}  (지수·FX·수익률·원자재 일봉)
      price_label:  {price_key: label}            (WB4 item 라벨용, 없으면 key로 폴백)
    반환 totals(관측용). 산출은 store.db(signals doc + story landing/breadth 필드)."""
    price_label = price_label or {}
    t = _topics.load_topics(topics_path)
    watch = _topics.watch_lenses(t)
    stock_label = {w["ticker"]: w["label"] for w in watch}
    lens_price_keys = _topics.all_lens_price_keys(t)        # standing lens → [price_key...]
    lens_type = {l["id"]: l["type"] for l in t["lenses"]}

    stories = _open_stories(store, now - SIGNALS_WINDOW)

    # 서사 커버리지 집합(WB4용) — 최근 스토리가 손댄 티커/가격키.
    covered_tickers, covered_keys = set(), set()
    for s in stories:
        for m in _sig.entity_resolve([s["title"], *s["entities"]], watch):
            covered_tickers.add(m["ticker"])
        for lid in s["lenses"]:
            if lens_type.get(lid) == "standing":
                covered_keys.update(lens_price_keys.get(lid, []))

    totals = {"unexplained": 0, "landing": 0, "breadth": 0, "stories": len(stories)}

    # ── WB4. 설명 안 되는 움직임 (조사 큐) ────────────────────────────────
    items, robust = [], True

    def _scan(idkey: str, label: str, kind: str, series: list, covered: bool, is_stock: bool):
        nonlocal robust
        stats = _sig.baseline_stats(series)
        if not stats["min_sample_ok"]:           # 데이터 건강(스캔한 모든 심볼) → doc 플래그 강등
            robust = False
        z = _sig.move_z(_sig.latest_return(series), stats)
        if not _sig.is_big_move(z):
            return
        # 하드 게이트: 얇은 베이스라인의 z는 신뢰 불가 → 큐에 넣지 않는다(오발화 차단, 리뷰 high).
        if not stats["min_sample_ok"]:
            return
        volc = _sig.volume_confirmed(series, is_stock=is_stock)
        # 거래량 확인 **필수**(주식·주식지수): True가 아니면(미확인 None·미확 False) 큐 제외.
        # 비주식(FX·수익률지수·선물)=volc None, 거래량 게이트 없음(가격 z만으로 큐, vol_confirmed=null).
        if is_stock and volc is not True:
            return
        if covered:                              # 서사가 이미 붙음 → '설명 안 됨' 아님
            return
        rec = _sig.latest_return(series)
        items.append({("ticker" if kind == "stock" else "key"): idkey, "label": label,
                      "kind": kind, "move_z": round(z, 3),
                      "move_pct": round(rec * 100.0, 3) if rec is not None else None,
                      "vol_confirmed": volc, "story_coverage": False, "unverified": True,
                      "_score": abs(z) * (_sig.WATCH_RANK_WEIGHT if kind == "stock" else 1.0)})

    for w in watch:
        tk = w["ticker"]
        _scan(tk, w["label"], "stock", stock_series.get(tk) or [],
              tk in covered_tickers, is_stock=True)
    for key in sorted(price_series):
        # 리포트 대상(standing) 렌즈에 매핑된 가격키만 스캔(고아 계열 제외 — WB2가 전부 매핑).
        if not any(key in ks for ks in lens_price_keys.values()):
            continue
        _scan(key, price_label.get(key, key), "index", price_series.get(key) or [],
              key in covered_keys, is_stock=(key in STOCK_INDEX_KEYS))

    items.sort(key=lambda it: it["_score"], reverse=True)   # 백엔드가 rank 확정(move_z·watch가중)
    for i, it in enumerate(items, 1):
        it["rank"] = i
        it.pop("_score", None)
    store.db.collection("signals").document("unexplained_moves").set(
        {"generated_at": now, "items": items, "min_sample_ok": robust, "unverified": True})
    totals["unexplained"] = len(items)

    # ── WB3. 개체 착지 + WB5. 매크로 브레드스 (스토리 doc 필드) ──────────────
    mkt = price_series.get(MARKET_FACTOR_KEY) or []
    for s in stories:
        start, end = _window_dates(s["first_seen"], now)

        # WB3 landing — resolve → 티커별 지수 대비 초과수익(베타제거).
        landing_tickers = []
        for m in _sig.entity_resolve([s["title"], *s["entities"]], watch):
            ser = stock_series.get(m["ticker"]) or []
            bench = price_series.get(_benchmark_key_for_ticker(m["ticker"])) or []
            stats = _sig.baseline_stats(ser)
            ex = _sig.excess_return(ser, bench, start, end)
            if ex is not None and stats["min_sample_ok"]:
                landing_tickers.append({
                    "ticker": m["ticker"], "label": m["label"],
                    "excess_pct": round(ex["excess"] * 100.0, 3),
                    "window_days": ex["window_days"], "resolved": True})
        landing = {"tickers": landing_tickers,
                   "asset_class_fallback": not landing_tickers, "unverified": True}
        store.db.collection("stories").document(s["id"]).set({"landing": landing}, merge=True)
        totals["landing"] += 1

        # WB5 breadth — 자산군 폭 + 베타제거 후 초과이동 확인(공동하락 배제).
        asset_lenses = [lid for lid in dict.fromkeys(s["lenses"])
                        if lens_type.get(lid) == "standing"]
        uncovered = [lid for lid in asset_lenses if not lens_price_keys.get(lid)]
        confirmed = 0
        for lid in asset_lenses:
            hit = False
            for key in lens_price_keys.get(lid, []):
                ser = price_series.get(key) or []
                st = _sig.baseline_stats(ser)
                ex = _sig.excess_return(ser, mkt, start, end)
                # WB3 착지와 동일 표본 게이트(리뷰 high: 브레드스만 미가드였음).
                if ex is not None and st["min_sample_ok"] and _sig.excess_is_big(ex["excess"], st):
                    hit = True
                    break
            if hit:
                confirmed += 1
        breadth = {"span": len(asset_lenses), "asset_classes": asset_lenses,
                   "price_confirmed": confirmed >= _sig.BREADTH_MIN_ANCHOR,
                   "uncovered": uncovered, "unverified": True}
        store.db.collection("stories").document(s["id"]).set({"breadth": breadth}, merge=True)
        totals["breadth"] += 1

    log.info("signals pass: %s", totals)
    return totals
