"""신호 엔진 (pure) — 뉴스×가격 신호의 공유 수학. Firestore·네트워크 없음(전부 주입).

세 기능(WB3 착지·WB4 설명안됨·WB5 브레드스)이 이 위에 앉는다. 여기엔 순수 함수만:
- move_detector: **긴 베이스라인**(range=1y 일봉) 대비 최근 수익률의 z(분포 상대) + (주식)상대거래량.
- entity_resolve: 스토리 텍스트 → watch 티커(topics.yaml keywords→ticker, **결정론**).
- beta/excess_return: 시장 베타 제거 후 초과수익(리스크오프 공동변동을 브레드스/착지로 오인 방지).

임계 SSOT(매직넘버 금지):
  MOVE_Z — '큰 이동'의 **유일한** 기준(WB4·WB5 공용, 기능별 재발명 금지). 절대 가격%가 아니라
  각 자산의 자기 히스토리 표준편차로 정규화한 **분포 상대** 임계라 자산별 변동성에 자동 적응한다.
  BASELINE_MIN_SAMPLE — 유효 거래일이 이보다 적으면 통계 불신(min_sample_ok=False → 정밀% 억제).
테스트는 이 상수의 '값'을 박지 말고 **불변식**(정규화·베타제거·표본게이트 거동)을 검증한다.
"""
from __future__ import annotations

# ── 임계 SSOT (분포 불변식 — 매직넘버 아님) ─────────────────────────────────
# MOVE_Z: 자기 히스토리 std로 정규화한 z. |z|>=MOVE_Z면 '이 자산 기준 드문 이동'.
#   std 정규화라 변동성 큰 자산(크립토)·작은 자산(환율)에 같은 규칙이 스케일에 맞게 적용된다.
MOVE_Z = 2.0
# 유효 거래일 최소 표본. 긴 베이스라인(range=1y≈250거래일)이면 여유 충족. 미달=통계 불신 노출.
BASELINE_MIN_SAMPLE = 60
# 베타 추정 최소 겹침(자산·시장 공통 거래일). 표본 SSOT 재사용 — 소표본 베타(잡음)로 초과수익을
# 오염시키지 않게(리뷰: 2쌍 베타 방지). 긴 베이스라인이면 ≈250 겹쳐 여유 충족.
BETA_MIN_OVERLAP = BASELINE_MIN_SAMPLE
# 브레드스는 '여럿'이 정의 — 최소 앵커 수(구조적 정의이지 측정 임계 아님).
BREADTH_MIN_ANCHOR = 2
# WB4 랭킹에서 watch 종목 가중(매크로 상시이동 도배 방지). 순위 선호이지 측정 임계 아님.
WATCH_RANK_WEIGHT = 1.5


def daily_returns(series: list[dict]) -> list[float]:
    """series(오래된→최신, [{t,c,...}]) → 일간 수익률(분수) 리스트. null close·0분모는 건너뜀."""
    out, prev = [], None
    for p in series:
        c = p.get("c")
        if c is None:
            continue
        if prev is not None and prev != 0:
            out.append((c - prev) / prev)
        prev = c
    return out


def _mean_std(xs: list[float]) -> tuple[float, float, int]:
    """(평균, 표본표준편차, n). n<2면 std=0.0(불정)."""
    n = len(xs)
    if n == 0:
        return 0.0, 0.0, 0
    m = sum(xs) / n
    if n < 2:
        return m, 0.0, n
    var = sum((x - m) ** 2 for x in xs) / (n - 1)
    return m, var ** 0.5, n


def baseline_stats(series: list[dict]) -> dict:
    """긴 베이스라인 series → 수익률 분포 요약. min_sample_ok로 표본 충분성 노출(정직 게이트)."""
    rets = daily_returns(series)
    m, s, n = _mean_std(rets)
    return {"mean": m, "std": s, "n": n, "min_sample_ok": n >= BASELINE_MIN_SAMPLE}


def move_z(recent_return: float | None, stats: dict) -> float | None:
    """최근 일간 수익률의 z((r-mean)/std). std=0(불정)·입력 None이면 None(fail-soft)."""
    if recent_return is None:
        return None
    s = stats.get("std") or 0.0
    if s == 0:
        return None
    return (recent_return - stats.get("mean", 0.0)) / s


def is_big_move(z: float | None) -> bool:
    """분포 상대 '큰 이동' 판정 — 단일 SSOT(MOVE_Z). WB4·WB5가 공용."""
    return z is not None and abs(z) >= MOVE_Z


def latest_return(series: list[dict]) -> float | None:
    """series 마지막 일간 수익률(가장 최근 하루 이동). 2점 미만이면 None."""
    rets = daily_returns(series)
    return rets[-1] if rets else None


def latest_volume(series: list[dict]) -> float | None:
    """series 마지막 점의 거래량('v'). 없으면 None(비주식·거래량 미수신)."""
    for p in reversed(series):
        v = p.get("v")
        if v is not None:
            return v
    return None


def volume_confirmed(series: list[dict], *, is_stock: bool) -> bool | None:
    """상대거래량 확인 — **주식만**. 최근 거래량이 자기 히스토리 대비 큰가(z>=MOVE_Z, 단측).
    비주식(FX·수익률지수·선물)=None(거래량 무의미 — 정직). 표본 부족·무거래량=None."""
    if not is_stock:
        return None
    # 0·None 거래량 제외 — 지수(^GSPC 등)는 휴장/불완전 봉에 0을 끼워 평균을 왜곡(오염).
    vols = [p["v"] for p in series if p.get("v")]
    if len(vols) < BASELINE_MIN_SAMPLE:
        return None
    recent = latest_volume(series)
    if not recent:                               # 0·None 최근 거래량 → 확인 불가
        return None
    m, s, n = _mean_std(vols)
    if s == 0:
        return None
    return (recent - m) / s >= MOVE_Z


# ── 베타 제거(WB3·WB5) — 리스크오프 공동변동을 개별 신호로 오인 방지 ────────────
def _aligned_returns(a: list[dict], b: list[dict]) -> tuple[list[float], list[float]]:
    """두 series를 **공통 날짜**로 정렬해 각자의 일간 수익률 짝을 만든다.
    zip 무음절단 회피 — 공통 날짜 집합에서만 도출(길이 항상 동일)."""
    ma = {p["t"]: p["c"] for p in a if p.get("c") is not None and p.get("t")}
    mb = {p["t"]: p["c"] for p in b if p.get("c") is not None and p.get("t")}
    dates = sorted(set(ma) & set(mb))
    ar, br = [], []
    for i in range(1, len(dates)):
        a0, a1 = ma[dates[i - 1]], ma[dates[i]]
        b0, b1 = mb[dates[i - 1]], mb[dates[i]]
        if a0 and b0:
            ar.append((a1 - a0) / a0)
            br.append((b1 - b0) / b0)
    return ar, br


def beta(asset_series: list[dict], market_series: list[dict]) -> float | None:
    """시장 대비 베타 = cov(asset, market)/var(market) (공통날짜 일간수익률). 불정=None."""
    ar, br = _aligned_returns(asset_series, market_series)
    if len(br) < BETA_MIN_OVERLAP:               # 소표본 베타=잡음 → 초과수익 오염 방지(fail-soft)
        return None
    mb = sum(br) / len(br)
    ma = sum(ar) / len(ar)
    var = sum((x - mb) ** 2 for x in br)
    if var == 0:
        return None
    cov = sum((a - ma) * (b - mb) for a, b in zip(ar, br))
    return cov / var


def window_return(series: list[dict], start_date: str, end_date: str) -> tuple[float | None, int]:
    """[start_date, end_date](ISO 날짜문자열, 포함) 구간 누적 수익률·거래일 수.
    2점 미만이면 (None, n). 날짜문자열 비교라 tz 무관(datetime 3축 회피)."""
    pts = [p for p in series
           if p.get("c") is not None and p.get("t") and start_date <= p["t"] <= end_date]
    n = len(pts)
    if n < 2 or not pts[0]["c"]:
        return None, n
    return (pts[-1]["c"] - pts[0]["c"]) / pts[0]["c"], n


def excess_return(asset_series: list[dict], market_series: list[dict],
                  start_date: str, end_date: str) -> dict | None:
    """스토리 창 동안 자산의 **시장 베타 제거 초과수익** = r_asset - beta*r_market.
    베타/구간수익률 하나라도 불정이면 None(해소 실패 → 폴백). 값은 분수(×100=%)."""
    b = beta(asset_series, market_series)
    ar, na = window_return(asset_series, start_date, end_date)
    mr, nm = window_return(market_series, start_date, end_date)
    if b is None or ar is None or mr is None:
        return None
    return {"excess": ar - b * mr, "beta": b, "asset_ret": ar, "mkt_ret": mr,
            "window_days": min(na, nm)}


def excess_is_big(excess: float | None, stats: dict) -> bool:
    """초과수익이 '큰가' — WB4와 **같은 SSOT**(MOVE_Z)로: |excess| >= MOVE_Z * 일간std.
    자산 자기 변동성(std)에 스케일 맞춤 → 별도 deadband 매직넘버 불필요. 베타제거 후라
    리스크오프 공동하락은 excess≈0으로 걸러진다(개별적 이동만 통과)."""
    if excess is None:
        return False
    s = stats.get("std") or 0.0
    if s == 0:
        return False
    return abs(excess) >= MOVE_Z * s


# ── entity_resolve (WB3) — 스토리 → watch 티커 (결정론) ──────────────────────
def entity_resolve(text_parts, watch_lenses: list[dict]) -> list[dict]:
    """스토리 텍스트(entities+제목 등) → 매칭된 watch 티커 [{ticker,label}] (**결정론**).
    topics.yaml watch 렌즈의 keywords 부분일치(대소문자 무시). watch_tickers는 이 매칭을 안 함.
    미매칭이면 빈 리스트(호출자가 자산군 폴백)."""
    hay = " ".join(str(x) for x in (text_parts or []) if x).lower()
    if not hay.strip():
        return []
    out, seen = [], set()
    for w in watch_lenses:
        tk = w.get("ticker")
        if not tk or tk in seen:
            continue
        for kw in (w.get("keywords") or []):
            if kw and str(kw).lower() in hay:
                out.append({"ticker": tk, "label": w.get("label") or tk})
                seen.add(tk)
                break
    return out
