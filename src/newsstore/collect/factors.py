"""팩터·펀더멘털 수집 엔진 — 다운스트림 백테스트 seam(계약 SSOT: docs/firestore-contract.md).

계약의 per-symbol 컬렉터 14개는 구조가 셋 중 하나다. 그래서 컬렉터마다 모듈을 만들지 않고
**선언적 스펙(FactorSpec) + 제네릭 엔진**으로 짠다(DRY). HTTP는 주입(테스트 fake) — 이 모듈은
FMP 응답을 계약 문서 shape로 옮기는 것만 한다(파생 지표는 다운스트림 몫 — 스키마 그대로 저장).

shape:
  - history  : 응답 리스트의 각 행 = 문서 1개. id={symbol}__{행의 date}. 백필 히스토리(재무제표·
               비율·배당조정가·시총·등급이력). 새 행만 write(filter_new_ids_in).
  - asof     : 응답 전체 = 문서 1개. id={symbol}__{캡처일}. §2 백필 불가(추정치·목표가·등급분포)를
               '지금 as-of' 캡처. FMP는 과거값을 안 줘 주간 스냅샷해야 velocity가 산다.
  - snapshot : 응답 전체 = 문서 1개. id={symbol} 덮어쓰기. 현재값(profile).
"""
from __future__ import annotations
import logging
import re
import time
from dataclasses import dataclass, field

log = logging.getLogger("newsstore.collect.factors")


@dataclass(frozen=True)
class FactorSpec:
    key: str                        # Firestore 컬렉션명 = 계약의 컬렉션
    endpoint: str                   # FMP /stable/ 뒤 경로
    shape: str                      # "history" | "asof" | "snapshot"
    cadence: str                    # "daily" | "weekly" — 엔트리포인트가 선택
    params: dict = field(default_factory=dict)   # 심볼 외 고정 파라미터(period=annual 등)
    date_field: str = "date"        # history에서 행의 날짜 필드


# 계약(docs/firestore-contract.md §1·§2)을 코드로 — 이 리스트가 수집 대상 SSOT.
SPECS: list[FactorSpec] = [
    # §1 백필 가능 — history(행별 문서)
    FactorSpec("ratios", "ratios", "history", "weekly", {"period": "annual"}),
    FactorSpec("income", "income-statement", "history", "weekly", {"period": "annual"}),
    FactorSpec("balance", "balance-sheet-statement", "history", "weekly", {"period": "annual"}),
    FactorSpec("cashflow", "cash-flow-statement", "history", "weekly", {"period": "annual"}),
    FactorSpec("prices_eod", "historical-price-eod/dividend-adjusted", "history", "daily"),
    FactorSpec("market_cap", "historical-market-capitalization", "history", "weekly"),
    FactorSpec("grades_history", "grades-historical", "history", "weekly"),
    # §1 백필 가능 — snapshot(현재값)
    FactorSpec("profiles", "profile", "snapshot", "weekly"),
    # §2 백필 불가 — asof(캡처일 스냅샷). 지금부터 축적해야 영영 안 빈다.
    FactorSpec("estimates", "analyst-estimates", "asof", "weekly", {"period": "annual"}),
    FactorSpec("price_targets", "price-target-consensus", "asof", "weekly"),
    FactorSpec("grades_consensus", "grades-consensus", "asof", "weekly"),
]

ALLOWED_SHAPES = {"history", "asof", "snapshot"}
ALLOWED_CADENCES = {"daily", "weekly"}


def specs_for(cadence: str) -> list[FactorSpec]:
    """cadence('daily'|'weekly'|'all') 로 스펙을 고른다. 'all'=전체."""
    if cadence == "all":
        return list(SPECS)
    if cadence not in ALLOWED_CADENCES:
        raise ValueError(f"cadence는 daily|weekly|all 중 하나여야 한다 — {cadence!r}")
    return [s for s in SPECS if s.cadence == cadence]


def _date_key(v) -> str | None:
    """FMP date('2026-07-10' 또는 '2026-07-10 16:00:00')에서 숫자만 뽑아 문서 id 조각으로."""
    digits = re.sub(r"\D", "", v)[:14] if isinstance(v, str) else ""
    return digits or None


def build_docs(spec: FactorSpec, symbol: str, raw, *, capture_date: str,
               fetched_at: str) -> list[dict]:
    """FMP 응답을 계약 shape의 문서 리스트로. 각 문서는 'id' + symbol·source·fetched_at + 페이로드.
    - history : 행별 문서(id={symbol}__{행 date}). 날짜 없는 행은 드롭(fail-soft).
    - asof    : 전체를 한 문서(id={symbol}__{capture_date}), payload=응답 그대로.
    - snapshot: 전체를 한 문서(id={symbol}), payload=응답 그대로.
    capture_date는 숫자만(YYYYMMDD) 넘어온다고 가정(엔트리포인트가 부여)."""
    base = {"symbol": symbol, "source": "fmp", "fetched_at": fetched_at}
    if spec.shape == "history":
        rows = raw if isinstance(raw, list) else []
        out = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            dk = _date_key(row.get(spec.date_field))
            if dk is None:
                continue
            out.append({"id": f"{symbol}__{dk}", **base, **row})   # 스키마 그대로 + 메타
        return out
    if spec.shape == "asof":
        if not raw:                                  # 빈 응답은 스냅샷 안 만듦(velocity에 빈 행 금지)
            return []
        return [{"id": f"{symbol}__{capture_date}", **base, "as_of": capture_date, "data": raw}]
    if spec.shape == "snapshot":
        if not raw:
            return []
        return [{"id": symbol, **base, "data": raw}]
    raise ValueError(f"unknown shape {spec.shape!r}")   # SPECS 상수라 실무상 도달 안 함


def run_factor_pass(store, fetch, universe: list[str], specs: list[FactorSpec],
                    *, capture_date: str, fetched_at: str, delay_s: float = 0.0) -> dict:
    """universe × specs를 돌며 fetch→build_docs→store 적재. 반환={컬렉션: 쓴 수}.

    fetch(spec, symbol) -> 파싱된 JSON(주입 HTTP). 개별 (spec, symbol) 실패는 스킵(fail-soft).
    - history : 새 id만 save_docs(filter_new_ids_in로 dedup — 백필 write 비용 절감).
    - asof    : save_docs(같은 캡처일 id 덮어씀 — 하루 중 재실행 멱등).
    - snapshot: save_snapshot(symbol 덮어쓰기).
    delay_s: 콜 간 지연(FMP 750콜/분 레이트리밋 대응 — 엔트리포인트가 주입)."""
    counts: dict[str, int] = {}
    calls = 0
    for spec in specs:
        n = 0
        for symbol in universe:
            if delay_s and calls:
                time.sleep(delay_s)
            calls += 1
            try:
                raw = fetch(spec, symbol)
            except Exception as e:                   # 네트워크/타임아웃/응답 이상 — 그 (spec,symbol)만 스킵
                log.warning("factor fetch %s/%s 실패: %s", spec.key, symbol, e)
                continue
            docs = build_docs(spec, symbol, raw, capture_date=capture_date, fetched_at=fetched_at)
            if not docs:
                continue
            if spec.shape == "snapshot":
                for d in docs:
                    store.save_snapshot(spec.key, d["id"], {k: v for k, v in d.items() if k != "id"})
                    n += 1
            elif spec.shape == "history":
                new = set(store.filter_new_ids_in(spec.key, [d["id"] for d in docs]))
                n += store.save_docs(spec.key, [d for d in docs if d["id"] in new])
            else:                                    # asof
                n += store.save_docs(spec.key, docs)
        counts[spec.key] = n
        log.info("factor %s: %d doc(s) across %d symbols", spec.key, n, len(universe))
    return counts
