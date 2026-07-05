"""신호 엔진(pure) — 분포 정규화·표본게이트·베타제거·엔티티매칭·거래량 한정. 네트워크·Firestore 불요.

불변식으로 검증한다(상수 값을 박지 않음): ① z는 자기 std로 정규화(절대%가 아니라 분포 상대)
② 표본 미달이면 min_sample_ok=False ③ 베타제거 후 리스크오프 공동변동은 excess≈0(개별이동만 큼)
④ entity_resolve는 keywords 결정론 매칭 ⑤ 거래량 확인은 주식만(그 외 None)."""
from datetime import date, timedelta

from newsstore.enrich import signals as sig
from newsstore.enrich import topics as topics


def mkseries(closes, *, vols=None, start=date(2025, 1, 1)):
    out, d = [], start
    for i, c in enumerate(closes):
        p = {"t": d.isoformat(), "c": c}
        if vols is not None:
            p["v"] = vols[i]
        out.append(p)
        d += timedelta(days=1)
    return out


def _scale_asset(market_closes, k, start=100.0):
    """자산 일간수익률 = k × 시장 일간수익률(베타=k 유도). 누적은 복리라 근사."""
    out, prev_m, ac = [], None, start
    for m in market_closes:
        if prev_m is not None and prev_m != 0:
            ac *= (1 + k * (m - prev_m) / prev_m)
        out.append(ac)
        prev_m = m
    return out


# ── move_detector: 분포 상대(정규화) — 절대 % 매직넘버 아님 ──────────────────
def test_move_z_is_distribution_relative_not_absolute():
    # 같은 절대 하루 % 이동이라도, 저변동 자산은 '큰 이동'이고 고변동 자산은 아니다.
    calm = [100.0]
    for _ in range(69):
        calm.append(calm[-1] * (1 + (0.001 if len(calm) % 2 else -0.001)))  # ±0.1% 진동
    wild = [100.0]
    for _ in range(69):
        wild.append(wild[-1] * (1 + (0.05 if len(wild) % 2 else -0.05)))    # ±5% 진동
    bump = 0.03                                                             # +3% 하루 이동(동일)
    calm.append(calm[-1] * (1 + bump))
    wild.append(wild[-1] * (1 + bump))
    zc = sig.move_z(sig.latest_return(mkseries(calm)), sig.baseline_stats(mkseries(calm)))
    zw = sig.move_z(sig.latest_return(mkseries(wild)), sig.baseline_stats(mkseries(wild)))
    assert sig.is_big_move(zc)          # 저변동엔 +3%가 드문 이동
    assert not sig.is_big_move(zw)      # 고변동엔 +3%가 평범
    assert abs(zc) > abs(zw)            # 정규화 방향 확인


def test_min_sample_gate_flags_thin_baseline():
    thin = sig.baseline_stats(mkseries([100.0 + i * 0.1 for i in range(sig.BASELINE_MIN_SAMPLE - 1)]))
    thick = sig.baseline_stats(mkseries([100.0 + i * 0.1 for i in range(sig.BASELINE_MIN_SAMPLE + 5)]))
    assert thin["min_sample_ok"] is False
    assert thick["min_sample_ok"] is True


def test_move_z_none_on_degenerate():
    flat = sig.baseline_stats(mkseries([100.0] * 70))     # std=0
    assert sig.move_z(0.01, flat) is None
    assert sig.is_big_move(None) is False


# ── 베타 제거: 리스크오프 공동변동을 개별 이동으로 오인하지 않는다 ──────────────
def test_beta_removed_excess_filters_comovement():
    # 자산이 시장을 베타 2로 그대로 추종(공동변동) → 창에서도 같이 움직이면 초과수익≈0.
    market = [100.0]
    for i in range(71):
        market.append(market[-1] * (1 + (0.01 if i % 2 else -0.01)))
    asset = _scale_asset(market, 2.0)
    ms, as_ = mkseries(market), mkseries(asset)
    b = sig.beta(as_, ms)
    assert b is not None and abs(b - 2.0) < 0.15          # 베타 회수
    start, end = as_[-2]["t"], as_[-1]["t"]               # 마지막 하루 창(공동변동)
    ex = sig.excess_return(as_, ms, start, end)
    assert ex is not None
    assert not sig.excess_is_big(ex["excess"], sig.baseline_stats(as_))   # 공동변동=초과 없음


def test_beta_removed_excess_keeps_idiosyncratic_move():
    # 베이스라인은 공동변동(베타2)으로 잡되, 창에서 시장은 멈추고 자산만 급등 → 초과수익 큼.
    market = [100.0]
    for i in range(71):
        market.append(market[-1] * (1 + (0.01 if i % 2 else -0.01)))
    asset = _scale_asset(market, 2.0)
    market.append(market[-1])              # 창: 시장 변화 0
    asset.append(asset[-1] * 1.08)         # 창: 자산 +8% 개별 급등
    ms, as_ = mkseries(market), mkseries(asset)
    start, end = as_[-2]["t"], as_[-1]["t"]
    ex = sig.excess_return(as_, ms, start, end)
    assert ex is not None and ex["excess"] > 0
    assert sig.excess_is_big(ex["excess"], sig.baseline_stats(as_))       # 개별 이동은 통과


def test_excess_return_none_when_insufficient():
    s = mkseries([100.0, 101.0])
    assert sig.excess_return(s, s, "2099-01-01", "2099-12-31") is None    # 창에 점 없음


def test_beta_none_below_min_overlap():
    # 소표본 베타(잡음) 방지 — 겹치는 거래일이 표본 게이트 미만이면 None(초과수익 오염 차단).
    short = mkseries([100.0 + i for i in range(sig.BETA_MIN_OVERLAP - 5)])
    assert sig.beta(short, short) is None
    long = mkseries([100.0 * (1 + 0.001 * (i % 3)) for i in range(sig.BETA_MIN_OVERLAP + 10)])
    assert sig.beta(long, long) is not None       # 충분히 겹치면 산출(자기상관 베타≈1)


# ── entity_resolve: 결정론 keywords 매칭 ───────────────────────────────────
def test_entity_resolve_matches_watch_keywords():
    watch = topics.watch_lenses(topics.load_topics())
    r = sig.entity_resolve(["엔비디아 실적 서프라이즈", "NVIDIA"], watch)
    assert any(m["ticker"] == "NVDA" for m in r)
    assert sig.entity_resolve(["관련 없는 일반 뉴스"], watch) == []
    assert sig.entity_resolve([], watch) == []


def test_entity_resolve_dedups_and_is_deterministic():
    watch = topics.watch_lenses(topics.load_topics())
    r1 = sig.entity_resolve(["삼성전자", "Samsung Electronics", "삼성전자"], watch)
    r2 = sig.entity_resolve(["삼성전자", "Samsung Electronics", "삼성전자"], watch)
    tickers = [m["ticker"] for m in r1]
    assert tickers == [m["ticker"] for m in r2]           # 결정론
    assert tickers.count("005930") == 1                   # 중복 제거


# ── 거래량 확인: 주식만(그 외 None) ─────────────────────────────────────────
def test_volume_confirmed_stock_only():
    vols = [100.0] * (sig.BASELINE_MIN_SAMPLE + 4) + [5000.0]     # 마지막 거래량 급증
    closes = [100.0 + i * 0.01 for i in range(len(vols))]
    s = mkseries(closes, vols=vols)
    assert sig.volume_confirmed(s, is_stock=True) is True
    assert sig.volume_confirmed(s, is_stock=False) is None        # 비주식=None(무의미)


def test_volume_confirmed_none_when_thin_or_absent():
    thin = mkseries([100.0, 101.0], vols=[1.0, 2.0])
    assert sig.volume_confirmed(thin, is_stock=True) is None      # 표본 부족
    novol = mkseries([100.0 + i for i in range(sig.BASELINE_MIN_SAMPLE + 2)])
    assert sig.volume_confirmed(novol, is_stock=True) is None     # 거래량 미수신


def test_volume_confirmed_excludes_zero_volume_days():
    # 지수 0거래량 오염 방지: 0을 표본에서 빼므로, 0이 태반이면 유효표본 미달로 None(가짜 스파이크 X).
    n = sig.BASELINE_MIN_SAMPLE + 4
    vols = [0.0] * (n - 3) + [100.0, 100.0, 100.0]               # 유효(비0) 거래일 3개뿐
    closes = [100.0 + i * 0.01 for i in range(n)]
    assert sig.volume_confirmed(mkseries(closes, vols=vols), is_stock=True) is None
    # 최근 거래량이 0이면 확인 불가(None)
    vols2 = [100.0] * (n - 1) + [0.0]
    assert sig.volume_confirmed(mkseries(closes, vols=vols2), is_stock=True) is None
