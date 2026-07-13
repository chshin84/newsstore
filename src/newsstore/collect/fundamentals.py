"""펀더멘털(재무제표) 수집 — FMP income/balance/cashflow(annual)를 fundamentals/{symbol}에 저장.

목적: 고정 관심 티커의 연간 재무제표 스냅샷. SSOT는 config/fundamentals.yaml(고정 티커 목록).
HTTP는 주입(테스트 fake) — 이 모듈은 FMP 응답 취합·오케스트레이션만. run_fundamentals가 FMP
client(헤더 apikey)를 배선한다. 신선도(fetched_at)를 저장 dict에 실고, 만료(expire_at)는 store가 주입.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Callable

import yaml

log = logging.getLogger("newsstore.collect.fundamentals")

STATEMENTS = ("income", "balance", "cashflow")   # 저장 dict 키 = FMP 세 재무제표


def load_fundamental_tickers(path: str) -> list[str]:
    """config/fundamentals.yaml 로드 + fail-loud(빈 목록·비문자열·중복). 티커는 대문자로 정규화."""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    rows = raw.get("tickers")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{path}: 'tickers' 리스트가 필요하다")
    out, seen = [], set()
    for t in rows:
        if not (isinstance(t, str) and t.strip()):
            raise ValueError(f"{path}: 티커는 비어있지 않은 문자열이어야 한다 — {t!r}")
        tk = t.strip().upper()
        if tk in seen:
            raise ValueError(f"{path}: 티커 중복 {tk!r}")
        seen.add(tk)
        out.append(tk)
    return out


def _now_iso() -> str:
    """신선도(fetched_at) — 조회 시각(UTC ISO). 스케줄러가 조용히 멈춰도 낡은 값을 걸러내게."""
    return datetime.now(timezone.utc).isoformat()


def run_fundamentals_pass(store, fetch: Callable[[str, str], list], tickers: list[str],
                          *, save: Callable[[str, dict], None] | None = None) -> int:
    """각 티커에 income/balance/cashflow(annual)를 fetch→save_fundamental. 반환=저장 수.

    fetch(ticker, statement) -> list(FMP 응답). statement ∈ STATEMENTS(income·balance·cashflow).
    저장 dict = {income:[...], balance:[...], cashflow:[...], fetched_at}. expire_at은 store가 주입.
    개별 티커 실패는 스킵(fail-soft). mock vs 실클라이언트 None 차이는 `x or []`로 가드.
    세 문서가 모두 비면(응답 이상) 저장하지 않는다(비파괴 — 기존 값 유지)."""
    save = save or store.save_fundamental
    n = 0
    for tk in tickers:
        try:
            docs = {stmt: (fetch(tk, stmt) or []) for stmt in STATEMENTS}
        except Exception as e:                       # 네트워크/타임아웃/응답 이상 — 그 티커만 스킵
            log.warning("fundamental fetch %s 실패: %s", tk, e)
            continue
        if not any(docs.values()):
            log.warning("fundamental %s: 세 문서 모두 무효 — 스킵", tk)
            continue
        save(tk, {**docs, "fetched_at": _now_iso()})
        n += 1
    log.info("fundamentals pass: %d/%d saved", n, len(tickers))
    return n
