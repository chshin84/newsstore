"""신호 패스(오케스트레이션) — 에뮬레이터 왕복으로 프로즌 스키마·정직 불변식·비파괴를 강제.

프로덕션 계약(datetime 직렬화·store.db 왕복)을 실물로 태워, fake로는 못 잡는 크래셔를 막는다
(solved: fake store가 계약 필드 빼먹어 datetime 직렬화 크래셔를 통과시킨 전례). store 픽스처는
FIRESTORE_EMULATOR_HOST 없으면 skip(Docker test 서비스가 에뮬레이터 기동)."""
from datetime import datetime, timedelta, timezone

from newsstore.enrich.signals_pass import run_signals_pass
from newsstore.enrich import topics as _topics


def _mkseries(closes, *, vols=None, now=None):
    """파싱된 series([{t,c,v?}], 오래된→최신) — end=오늘(now), 하루 간격."""
    end = (now or datetime.now(timezone.utc)).date()
    n = len(closes)
    out = []
    for i, c in enumerate(closes):
        d = end - timedelta(days=n - 1 - i)
        p = {"t": d.isoformat(), "c": c}
        if vols is not None:
            p["v"] = vols[i]
        out.append(p)
    return out


def _calm(n=70, start=100.0):
    out = [start]
    for i in range(n - 1):
        out.append(out[-1] * (1 + (0.001 if i % 2 else -0.001)))
    return out


def _big_last(n=70, start=100.0, jump=0.15):
    c = _calm(n - 1, start)
    c.append(c[-1] * (1 + jump))
    return c


def _build_series(now, *, big_tickers=(), thin_big_tickers=(), novol_big_tickers=()):
    """watch/price 티커별 파싱된 series 맵.
      big_tickers      = 마지막날 급등 + 거래량 급증(→ WB4 큐 진입)
      thin_big_tickers = 급등이지만 베이스라인 40일(<표본 게이트) (→ 제외)
      novol_big_tickers= 급등이지만 거래량 평평(확인 실패) (→ 제외)."""
    calm_vol = [100.0] * 70
    big_vol = [100.0] * 69 + [1_000_000.0]
    t = _topics.load_topics()
    stock_series, price_series, price_label = {}, {}, {}
    for w in _topics.watch_lenses(t):
        tk = w["ticker"]
        if tk in thin_big_tickers:
            stock_series[tk] = _mkseries(_big_last(40), vols=[100.0] * 39 + [1e6], now=now)
        elif tk in novol_big_tickers:
            stock_series[tk] = _mkseries(_big_last(70), vols=calm_vol, now=now)   # 거래량 평평
        elif tk in big_tickers:
            stock_series[tk] = _mkseries(_big_last(70), vols=big_vol, now=now)
        else:
            stock_series[tk] = _mkseries(_calm(70), vols=calm_vol, now=now)
    from newsstore.collect.prices import load_price_symbols
    for s in load_price_symbols("config/prices.yaml"):
        price_series[s.key] = _mkseries(_calm(70), vols=calm_vol, now=now)
        price_label[s.key] = s.label
    return stock_series, price_series, price_label


def _seed_story(store, sid, *, entities, lenses, first_seen, last_seen):
    store.db.collection("stories").document(sid).set({
        "title": sid, "status": "open", "entities": entities, "lenses": lenses,
        "first_seen": first_seen, "last_seen": last_seen,
        # 기존 cluster/summary 필드(비파괴 확인용) — signals가 건드리면 안 됨
        "count": 3, "member_ids": ["m1", "m2", "m3"], "summary": "기존 요약",
    })


def _run(store):
    now = datetime.now(timezone.utc)
    fs, ls = now - timedelta(days=3), now - timedelta(hours=1)
    # story A: 엔비디아 언급(→NVDA 착지·커버) · us_equity+fx+crypto(브레드스, crypto=uncovered)
    _seed_story(store, "sA", entities=["엔비디아", "NVIDIA"],
                lenses=["us_equity", "fx", "crypto"], first_seen=fs, last_seen=ls)
    # story B: 삼성전자 언급(→005930 커버) — 삼성이 급등해도 서사 커버라 큐 제외돼야
    _seed_story(store, "sB", entities=["삼성전자"], lenses=["kr_equity"],
                first_seen=fs, last_seen=ls)
    # story C: 매칭 없는 개체 → 착지 폴백(tickers 빈·asset_class_fallback true)
    _seed_story(store, "sC", entities=["관련 없는 일반 뉴스"], lenses=["oil_energy"],
                first_seen=fs, last_seen=ls)
    # TSLA=big+uncovered(→큐 포함), 005930=big+covered(→큐 제외)
    stock_series, price_series, price_label = _build_series(now, big_tickers={"TSLA", "005930"})
    totals = run_signals_pass(store, stock_series=stock_series, price_series=price_series,
                              price_label=price_label, now=now)
    return now, totals


def test_frozen_unexplained_moves_schema_and_coverage(store):
    _run(store)
    doc = store.db.collection("signals").document("unexplained_moves").get().to_dict()
    assert doc is not None
    # 프로즌 doc shape 정확 일치(fail-loud on drift). unverified는 정직 불변식이 요구.
    assert set(doc) == {"generated_at", "items", "min_sample_ok", "unverified"}
    assert doc["unverified"] is True and doc["min_sample_ok"] is True   # 70pts≥표본 게이트
    tickers = {it.get("ticker") for it in doc["items"]}
    assert "TSLA" in tickers                       # 큰 이동+거래량+미커버 → 큐
    assert "005930" not in tickers                 # 큰 이동이어도 서사 커버 → 제외
    tsla = next(it for it in doc["items"] if it.get("ticker") == "TSLA")
    # 프로즌 stock item shape 정확 일치(주식은 ticker 키, key 아님)
    assert set(tsla) == {"ticker", "label", "kind", "move_z", "move_pct",
                         "vol_confirmed", "story_coverage", "rank", "unverified"}
    assert tsla["kind"] == "stock" and tsla["vol_confirmed"] is True
    assert tsla["story_coverage"] is False and tsla["unverified"] is True
    # rank는 백엔드 확정(1..n 연속, move_z 내림차순 정합)
    ranks = sorted(it["rank"] for it in doc["items"])
    assert ranks == list(range(1, len(doc["items"]) + 1))


def test_frozen_landing_schema_resolve_and_fallback(store):
    now, _ = _run(store)
    a = store.db.collection("stories").document("sA").get().to_dict()
    land = a["landing"]
    assert set(land) == {"tickers", "asset_class_fallback", "unverified"}
    assert land["unverified"] is True and land["asset_class_fallback"] is False
    nvda = next(t for t in land["tickers"] if t["ticker"] == "NVDA")
    assert set(nvda) == {"ticker", "label", "excess_pct", "window_days", "resolved"}
    assert nvda["resolved"] is True and isinstance(nvda["excess_pct"], float)
    assert nvda["window_days"] >= 2
    # 매칭 없는 스토리 → 폴백(tickers 빈)
    c = store.db.collection("stories").document("sC").get().to_dict()
    assert c["landing"]["asset_class_fallback"] is True and c["landing"]["tickers"] == []


def test_resolve_story_tickers_uses_watch_lenses_union_title():
    # 수정: entity_resolve가 제목만 보던 걸 → watch_* 렌즈(렌즈 패스가 이미 단 연결) ∪ 제목으로.
    from newsstore.enrich.signals_pass import _resolve_story_tickers
    watch = _topics.watch_lenses(_topics.load_topics())
    # 제목에 이름 없어도 watch_micron 렌즈로 MU 회수(예전엔 landing 빈 폴백의 주범)
    r1 = _resolve_story_tickers({"title": "반도체 급락", "entities": [], "lenses": ["us_equity", "watch_micron"]}, watch)
    assert [m["ticker"] for m in r1] == ["MU"]
    # 렌즈 ∪ 제목 키워드, dedup(마이크론=렌즈, 엔비디아=제목)
    r2 = _resolve_story_tickers({"title": "엔비디아·마이크론 동반 하락", "entities": [], "lenses": ["watch_micron"]}, watch)
    t = [m["ticker"] for m in r2]
    assert set(t) == {"MU", "NVDA"} and len(t) == len(set(t))
    # 미매칭 → 빈(호출자 폴백)
    assert _resolve_story_tickers({"title": "날씨", "entities": [], "lenses": ["us_econ"]}, watch) == []


def test_frozen_breadth_schema_and_uncovered(store):
    _run(store)
    a = store.db.collection("stories").document("sA").get().to_dict()
    br = a["breadth"]
    assert set(br) == {"span", "asset_classes", "price_confirmed", "uncovered", "unverified"}
    assert br["unverified"] is True
    assert set(br["asset_classes"]) == {"us_equity", "fx", "crypto"}
    assert br["span"] == 3
    assert br["uncovered"] == ["crypto"]           # 가격계열 없는 자산군(‘안 움직임’ 아님)
    assert isinstance(br["price_confirmed"], bool)


def test_unverified_invariant_on_every_signal_output(store):
    # 정직 불변식(fail-loud): signals doc·item·landing·breadth 모든 산출에 unverified:true.
    _run(store)
    doc = store.db.collection("signals").document("unexplained_moves").get().to_dict()
    assert doc["unverified"] is True
    for it in doc["items"]:
        assert it["unverified"] is True
    for sid in ("sA", "sB", "sC"):
        d = store.db.collection("stories").document(sid).get().to_dict()
        assert d["landing"]["unverified"] is True
        assert d["breadth"]["unverified"] is True


def _run_bare(store, **series_kw):
    """스토리 없이(커버리지 무관) 신호 패스 실행 — WB4 게이트 단독 검증용."""
    now = datetime.now(timezone.utc)
    ss, ps, pl = _build_series(now, **series_kw)
    run_signals_pass(store, stock_series=ss, price_series=ps, price_label=pl, now=now)
    return store.db.collection("signals").document("unexplained_moves").get().to_dict()


def test_wb4_excludes_thin_baseline_move(store):
    # 오발화 차단: 급등이어도 베이스라인이 얇으면(<표본 게이트) z 신뢰 불가 → 큐 제외.
    doc = _run_bare(store, thin_big_tickers={"AAPL"})
    assert "AAPL" not in {it.get("ticker") for it in doc["items"]}
    assert doc["min_sample_ok"] is False           # 얇은 심볼 스캔 → 데이터 건강 강등(정직)


def test_wb4_requires_volume_confirmation_for_stock(store):
    # 주식은 거래량 확인 필수: 급등이어도 거래량 평평(미확인)이면 큐 제외.
    doc = _run_bare(store, novol_big_tickers={"MSFT"})
    assert "MSFT" not in {it.get("ticker") for it in doc["items"]}


def test_wb4_funnel_counters_conserve_and_attribute(store):
    # IB2: 퍼널 카운터가 탈락 단계를 귀속하고, 불변식(scanned=Σdrops+queued)을 지킨다(매직넘버 없음).
    now, totals = _run(store)
    f = totals["funnel"]
    assert set(f) == {"scanned", "dropped_z", "dropped_sample",
                      "dropped_volume", "dropped_covered", "queued"}
    assert f["scanned"] == (f["dropped_z"] + f["dropped_sample"] + f["dropped_volume"]
                            + f["dropped_covered"] + f["queued"])          # 보존 불변식
    assert f["queued"] == totals["unexplained"]                            # 큐 = 발행 items 수
    assert f["scanned"] > 0                                                # 뭔가는 스캔됨


def test_wb4_funnel_volume_drop_is_stock_only(store):
    # 주식전용 거래량 게이트: 급등이나 거래량 평평인 주식은 dropped_volume에 귀속(비주식은 이 게이트 없음).
    now = datetime.now(timezone.utc)
    ss, ps, pl = _build_series(now, novol_big_tickers={"MSFT"})
    totals = run_signals_pass(store, stock_series=ss, price_series=ps, price_label=pl, now=now)
    assert totals["funnel"]["dropped_volume"] >= 1        # 거래량 미확인 주식이 이 단계로 탈락


def test_wb4_funnel_covered_drop_attributes_narrative_coverage(store):
    # 서사 커버된 급등(005930)은 dropped_covered에 귀속(‘설명 안 됨’ 아님).
    _seed_story(store, "sB", entities=["삼성전자"], lenses=["kr_equity"],
                first_seen=datetime.now(timezone.utc) - timedelta(days=3),
                last_seen=datetime.now(timezone.utc) - timedelta(hours=1))
    now = datetime.now(timezone.utc)
    ss, ps, pl = _build_series(now, big_tickers={"005930"})
    totals = run_signals_pass(store, stock_series=ss, price_series=ps, price_label=pl, now=now)
    assert totals["funnel"]["dropped_covered"] >= 1       # 삼성 급등이 서사 커버라 커버리지 탈락


def test_signals_pass_is_nondestructive_to_story(store):
    # 비파괴/additive: landing/breadth만 추가하고 기존 cluster/summary 필드는 보존(merge=True).
    _run(store)
    d = store.db.collection("stories").document("sA").get().to_dict()
    assert d["summary"] == "기존 요약" and d["count"] == 3
    assert d["member_ids"] == ["m1", "m2", "m3"] and d["status"] == "open"
    assert "landing" in d and "breadth" in d
