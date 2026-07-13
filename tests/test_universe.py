"""PIT 유니버스 도출 — constituent에서 종목 도출 + index_members/index_changes/delisted 적재. HTTP 주입."""
import pytest

from newsstore.collect.universe import collect_universe, INDEX_ENDPOINTS

FA = "2026-07-13T00:00:00+00:00"


class _Store:
    def __init__(self):
        self.snaps = {}         # collection -> {id: doc}
        self.docs = {}          # collection -> {id: doc}
    def save_snapshot(self, col, doc_id, data):
        self.snaps.setdefault(col, {})[doc_id] = data
    def save_docs(self, col, docs):
        d = self.docs.setdefault(col, {})
        for x in docs:
            d[x["id"]] = x
        return len(docs)


def _members(*syms):
    return [{"symbol": s, "name": s, "sector": "X"} for s in syms]


def test_index_endpoints_cover_three_indices():
    assert set(INDEX_ENDPOINTS) == {"sp500", "nasdaq", "dowjones"}


def test_collect_universe_unions_and_dedups_symbols():
    store = _Store()
    current = {"sp500": _members("AAPL", "MSFT"), "nasdaq": _members("MSFT", "NVDA")}
    uni = collect_universe(
        store,
        fetch_current=lambda idx: current[idx],
        fetch_changes=lambda idx: [{"dateAdded": "June 29, 2026", "addedSecurity": "X"}],
        fetch_delisted=lambda: [{"symbol": "OLDCO", "delistedDate": "2020-01-01"}],
        indices=["sp500", "nasdaq"], fetched_at=FA)
    assert uni == ["AAPL", "MSFT", "NVDA"]                       # 합집합·중복제거·정렬


def test_collect_universe_stores_pit_collections():
    store = _Store()
    collect_universe(
        store,
        fetch_current=lambda idx: _members("AAPL"),
        fetch_changes=lambda idx: [{"dateAdded": "June 29, 2026", "addedSecurity": "X", "removedTicker": "Y"}],
        fetch_delisted=lambda: [{"symbol": "OLDCO", "companyName": "Old Co", "delistedDate": "2020-01-01"}],
        indices=["sp500"], fetched_at=FA)
    assert store.snaps["index_members"]["sp500"]["members"][0]["symbol"] == "AAPL"
    assert store.snaps["index_changes"]["sp500"]["changes"][0]["removedTicker"] == "Y"
    assert store.docs["delisted"]["OLDCO"]["delistedDate"] == "2020-01-01"   # 심볼별 문서


def test_collect_universe_one_index_failure_does_not_block_others():
    store = _Store()

    def fetch_current(idx):
        if idx == "nasdaq":
            raise RuntimeError("down")
        return _members("AAPL")

    uni = collect_universe(store, fetch_current,
                           fetch_changes=lambda idx: [], fetch_delisted=lambda: [],
                           indices=["nasdaq", "sp500"], fetched_at=FA)
    assert uni == ["AAPL"]                                       # nasdaq 실패해도 sp500 유지


def test_collect_universe_fails_loud_on_unknown_index():
    with pytest.raises(ValueError, match="인덱스"):
        collect_universe(_Store(), lambda idx: [], lambda idx: [], lambda: [],
                         indices=["russell2000"], fetched_at=FA)
