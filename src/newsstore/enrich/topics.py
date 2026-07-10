"""topics.yaml 렌즈 SSOT 로더 + registry. 분류·UI·정렬이 전부 여기서 도출."""
from __future__ import annotations
import functools
import yaml

_TYPES = {"standing", "development", "sector", "watch", "risk"}


@functools.lru_cache(maxsize=4)
def load_topics(path: str = "config/topics.yaml") -> dict:
    t = yaml.safe_load(open(path, encoding="utf-8"))
    bad = [l["id"] for l in t["lenses"] if l["type"] not in _TYPES]
    if bad:                       # FAIL-LOUD: 미지정 type 즉시 폭발
        raise ValueError(f"topics.yaml unknown type for: {bad}")
    return t


def valid_ids(t: dict) -> set[str]:
    return {l["id"] for l in t["lenses"]}


def lens_type(t: dict, lens_id: str) -> str:
    for l in t["lenses"]:
        if l["id"] == lens_id:
            return l["type"]
    raise KeyError(f"unknown lens id: {lens_id}")


def lens_labels(t: dict) -> dict[str, str]:
    """렌즈 id → 한국어 라벨(UI 표기용, SSOT). label.ko 없으면 id 폴백."""
    out = {}
    for l in t["lenses"]:
        lab = l.get("label") if isinstance(l.get("label"), dict) else {}
        out[l["id"]] = (lab.get("ko") if lab else None) or l["id"]
    return out


def report_lens_ids(t: dict) -> list[str]:
    """리포트 대상 렌즈 id(등장 순서) = 금융 자산(type=standing)만(사용자 결정 2026-07-04).
    리스크(type=risk)·경제·정치·정책(type=development)은 리포트로 만들지 않고, 그 뉴스는
    context_lens_ids 풀로 자산 리포트(백드롭·시장프레임)에 녹인다(#2). watch·sector도 제외."""
    return [l["id"] for l in t["lenses"] if l["type"] == "standing"]


def context_lens_ids(t: dict) -> list[str]:
    """시장프레임·백드롭 입력 풀 = watch·sector 외 렌즈 전부(자산 + 리스크·경제·정치·정책).
    리포트는 안 만들지만 비자산 뉴스를 자산 리포트로 녹이려면 이 풀에 남아야 한다(#2 fold-in)."""
    return [l["id"] for l in t["lenses"] if l["type"] not in ("watch", "sector")]


def watch_lenses(t: dict) -> list[dict]:
    """watch 렌즈(개별 종목) 전체 → [{ticker, symbol, label, keywords}].
    Yahoo 심볼: 한국 티커(전부 숫자)면 `.KS` 접미(예 005930→005930.KS), 그 외 그대로(NVDA 등).
    keywords는 signals.entity_resolve가 스토리→티커 결정론 매칭에 쓴다(watch_tickers는 안 씀)."""
    out = []
    for l in t["lenses"]:
        if l.get("type") != "watch":
            continue
        tk = str(l.get("ticker") or "").strip()
        if not tk:
            continue
        sym = f"{tk}.KS" if tk.isdigit() else tk
        lab = (l.get("label") or {}).get("ko") if isinstance(l.get("label"), dict) else None
        out.append({"id": l["id"], "ticker": tk, "symbol": sym, "label": lab or l["id"],
                    "keywords": [str(k) for k in (l.get("keywords") or []) if str(k).strip()]})
    return out


def watch_tickers(t: dict) -> list[dict]:
    """watch 렌즈(개별 종목) → 종목 히스토리 수집 대상 [{ticker, symbol, label}].
    watch_lenses에서 도출(SSOT — keywords만 뺀 뷰)."""
    return [{"ticker": w["ticker"], "symbol": w["symbol"], "label": w["label"]}
            for w in watch_lenses(t)]


def price_key_for(t: dict, lens_id: str) -> str | None:
    """렌즈 → 교차검증용 1차 가격키(prices/{key}). 없으면 None(가격 없는 렌즈=교차검증 스킵).
    뉴스는 지연될 수 있어, 실제 가격을 리포트의 '현재 상태' 우선 근거로 쓰기 위한 매핑(SSOT).
    리포트 교차검증은 이 1차 키만 쓴다(부가 계열은 signals 전용 — price_keys_for)."""
    for l in t["lenses"]:
        if l["id"] == lens_id:
            return l.get("price_key")
    return None


def price_keys_for(t: dict, lens_id: str) -> list[str]:
    """렌즈 → signals가 소비하는 **모든** 가격키(1차 price_key + 부가 extra_price_keys).
    리포트는 price_key(1차)만 쓰지만, signals(WB2·WB4·WB5)는 렌즈에 딸린 부가 계열
    (예 us_equity의 nasdaq, us_rates의 us2y·us30y, fx의 usdjpy)까지 이동탐지에 쓴다.
    리포트 생성 경로(price_key_for)는 불변 — 이 함수는 부가 계열을 additive로만 노출."""
    for l in t["lenses"]:
        if l["id"] == lens_id:
            keys = []
            pk = l.get("price_key")
            if pk:
                keys.append(pk)
            for k in (l.get("extra_price_keys") or []):
                if k and k not in keys:
                    keys.append(k)
            return keys
    return []


def all_lens_price_keys(t: dict) -> dict[str, list[str]]:
    """standing 렌즈 → 그 렌즈가 소유한 모든 가격키(1차+부가). signals 스캔 대상 도출(SSOT).
    드리프트 가드: 반환 키는 전부 prices.yaml에 실재해야 한다(테스트가 강제)."""
    out = {}
    for l in t["lenses"]:
        if l.get("type") != "standing":
            continue
        keys = price_keys_for(t, l["id"])
        if keys:
            out[l["id"]] = keys
    return out


def report_groups(t: dict) -> dict[str, list[str]]:
    """report_group → [lens_id...] (yaml 등장 순서 보존). UI 섹션 앵커 도출(SSOT).
    자산(standing) 렌즈만 — 리포트 대상과 일치(report_lens_ids). report_group 누락 시 KeyError."""
    out: dict[str, list[str]] = {}
    for l in t["lenses"]:
        if l["type"] != "standing":
            continue
        out.setdefault(l["report_group"], []).append(l["id"])
    return out
