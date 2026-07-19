"""PIT 유니버스 도출 — S&P500 ∪ Nasdaq-100 ∪ Dow의 현재 구성종목에서 수집 대상을 도출한다.

목록을 하드코딩하지 않는다(SSOT = FMP constituent 엔드포인트). 과거 시점 모집단은 편입·편출
변경 로그 + 상장폐지 목록으로 재구성한다(생존편향 보정). 계약 SSOT: docs/firestore-contract.md.

저장:
  - index_members/{index}   : 현재 구성종목(덮어쓰기) — 유니버스 도출 SSOT.
  - index_changes/{index}   : 편입·편출 변경 로그 전체(덮어쓰기, 바운드 — 배열이지만 느리게 자람).
  - delisted/{symbol}        : 상장폐지 종목(심볼별 문서).
HTTP는 주입(테스트 fake). 인덱스 키는 FMP 엔드포인트 접두(sp500·nasdaq·dowjones).
"""
from __future__ import annotations
import logging

log = logging.getLogger("newsstore.collect.universe")

# 인덱스 키 → (현재 constituent 엔드포인트, 변경로그 엔드포인트). 계약의 유니버스 SSOT.
INDEX_ENDPOINTS = {
    "sp500": ("sp500-constituent", "historical-sp500-constituent"),
    "nasdaq": ("nasdaq-constituent", "historical-nasdaq-constituent"),
    "dowjones": ("dowjones-constituent", "historical-dowjones-constituent"),
}


def collect_universe_screener(store, fetch_screener, *, limit: int, fetched_at: str) -> list[str]:
    """company-screener(시총 상위)에서 유니버스를 도출한다 — 지수 구성 대신 시총 상위 N.
    생존편향 PIT는 그 시점 스크린 명단을 index_members/screener 스냅샷으로 보존해 constituent와 같은
    방식으로 재구성한다(편입·편출은 스냅샷 간 diff). 반환 = 정렬된 티커.

    fetch_screener() -> [{symbol,companyName,marketCap,sector,...}]  (시총 내림차순)
    개별 실패는 예외로 전파(유니버스 없이 팩터 수집은 무의미 — fail-loud)."""
    rows = fetch_screener()
    members = [{"symbol": r["symbol"], "name": r.get("companyName"),
                "sector": r.get("sector"), "marketCap": r.get("marketCap")}
               for r in (rows or []) if isinstance(r, dict) and r.get("symbol")]
    # 엔드포인트가 시총 내림차순을 주지만, 방어적으로 재정렬 후 상위 N(무순서 회귀 대비).
    members.sort(key=lambda m: (m.get("marketCap") or 0), reverse=True)
    members = members[:limit]
    store.save_snapshot("index_members", "screener",
                        {"index": "screener", "members": members, "limit": limit,
                         "source": "fmp", "fetched_at": fetched_at})
    out = sorted({m["symbol"] for m in members})
    log.info("universe(screener): %d symbols (top %d by market cap)", len(out), limit)
    return out


def collect_universe(store, fetch_current, fetch_changes, fetch_delisted,
                     indices: list[str], *, fetched_at: str) -> list[str]:
    """indices의 현재 구성종목에서 유니버스(중복 제거·정렬)를 도출하고 PIT 컬렉션을 적재한다.
    반환 = 정렬된 티커 리스트.

    fetch_current(index_key)  -> [{symbol,name,sector,...}]  (현재 구성)
    fetch_changes(index_key)  -> [{dateAdded,addedSecurity,removedTicker,...}]  (변경 로그)
    fetch_delisted()          -> [{symbol,companyName,delistedDate,...}]  (상장폐지)
    개별 인덱스 실패는 스킵(fail-soft) — 한 인덱스가 다른 인덱스·유니버스를 막지 않는다."""
    universe: set[str] = set()
    for idx in indices:
        if idx not in INDEX_ENDPOINTS:
            raise ValueError(f"모르는 인덱스 {idx!r} — {sorted(INDEX_ENDPOINTS)} 중 하나여야 한다")
        try:
            cur = fetch_current(idx)
        except Exception as e:
            log.warning("universe %s 현재 구성 실패: %s", idx, e)
            continue
        members = [r for r in (cur or []) if isinstance(r, dict) and r.get("symbol")]
        for r in members:
            universe.add(r["symbol"])
        store.save_snapshot("index_members", idx,
                            {"index": idx, "members": members, "source": "fmp", "fetched_at": fetched_at})
        try:
            changes = fetch_changes(idx)
        except Exception as e:                       # 변경 로그 실패해도 현재 구성·유니버스는 유지
            log.warning("universe %s 변경 로그 실패: %s", idx, e)
            changes = None
        if changes is not None:
            store.save_snapshot("index_changes", idx,
                                {"index": idx, "changes": changes, "source": "fmp", "fetched_at": fetched_at})

    # 상장폐지 — 심볼별 문서(생존편향 보정). 배치 write(save_docs, 멱등 덮어쓰기).
    try:
        delisted = fetch_delisted()
        docs = [{"id": r["symbol"], "source": "fmp", "fetched_at": fetched_at, **r}
                for r in (delisted or []) if isinstance(r, dict) and r.get("symbol")]
        if docs:
            store.save_docs("delisted", docs)
    except Exception as e:
        log.warning("universe delisted 수집 실패: %s", e)

    out = sorted(universe)
    log.info("universe: %d symbols across %s", len(out), indices)
    return out
