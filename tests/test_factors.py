"""팩터·펀더멘털 수집 엔진 — 스펙 선택·문서 빌드·shape별 디스패치. HTTP 주입(fake)이라 네트워크 불요."""
import json
from pathlib import Path

import pytest

from newsstore.collect.factors import (FactorSpec, SPECS, specs_for, build_docs,
                                       run_factor_pass)

REPO = Path(__file__).resolve().parents[1]
FIX = REPO / "tests" / "fixtures"
FA = "2026-07-13T00:00:00+00:00"
CAP = "20260713"


def _fix(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


# ─────────────────────────────── SPECS / specs_for ───────────────────────────────

def test_specs_cover_contract_collections():
    # 계약(§1·§2)의 per-symbol 컬렉션이 전부 스펙에 있다 — 이름이 조용히 빠지면 안 된다.
    keys = {s.key for s in SPECS}
    assert {"ratios", "income", "balance", "cashflow", "prices_eod", "market_cap",
            "grades_history", "profiles", "estimates", "price_targets", "grades_consensus"} == keys


def test_specs_shapes_and_cadences_are_valid():
    for s in SPECS:
        assert s.shape in {"history", "asof", "snapshot"}
        assert s.cadence in {"daily", "weekly"}
    # 비용 규칙(불변식): 백필 불가 §2(asof)만 daily — 매일 캡처가 필요하고 dedup-read가 없어 저렴.
    # backfillable(history/snapshot)는 전부 weekly — 매일 전체이력 재조회 = Firestore read 비용 폭탄 회피.
    assert {s.key for s in SPECS if s.cadence == "daily"} == {s.key for s in SPECS if s.shape == "asof"}
    assert all(s.cadence == "weekly" for s in SPECS if s.shape != "asof")


def test_specs_for_selects_by_cadence():
    # daily = §2 asof 캡처만(저렴). weekly = backfillable 전부.
    assert {s.key for s in specs_for("daily")} == {s.key for s in SPECS if s.shape == "asof"}
    assert all(s.shape == "asof" for s in specs_for("daily"))
    assert "ratios" in {s.key for s in specs_for("weekly")}
    assert len(specs_for("all")) == len(SPECS)


def test_specs_for_fails_loud_on_bad_cadence():
    with pytest.raises(ValueError, match="cadence"):
        specs_for("hourly")


# ─────────────────────────────── build_docs ───────────────────────────────

INCOME = FactorSpec("income", "income-statement", "history", "weekly", {"period": "annual"})
ESTIMATES = FactorSpec("estimates", "analyst-estimates", "asof", "weekly", {"period": "annual"})
PROFILE = FactorSpec("profiles", "profile", "snapshot", "weekly")


def test_build_docs_history_one_doc_per_row_with_date_id():
    docs = build_docs(INCOME, "AAPL", _fix("fmp_income_aapl.json"), capture_date=CAP, fetched_at=FA)
    ids = [d["id"] for d in docs]
    assert "AAPL__20250927" in ids and "AAPL__20240928" in ids      # id = {symbol}__{행 date}
    d0 = next(d for d in docs if d["id"] == "AAPL__20250927")
    assert d0["symbol"] == "AAPL" and d0["source"] == "fmp" and d0["fetched_at"] == FA
    assert d0["revenue"] == 416200000000                            # FMP 스키마 그대로 실림


def test_build_docs_history_drops_rows_without_date():
    raw = [{"date": "2025-09-27", "revenue": 1}, {"revenue": 2}, {"date": None, "revenue": 3}]
    docs = build_docs(INCOME, "AAPL", raw, capture_date=CAP, fetched_at=FA)
    assert [d["id"] for d in docs] == ["AAPL__20250927"]


def test_build_docs_asof_whole_response_keyed_by_capture_date():
    raw = [{"date": "2030-09-27", "epsAvg": 8.1}, {"date": "2031-09-27", "epsAvg": 8.9}]
    docs = build_docs(ESTIMATES, "AAPL", raw, capture_date=CAP, fetched_at=FA)
    assert len(docs) == 1
    assert docs[0]["id"] == "AAPL__20260713" and docs[0]["as_of"] == CAP
    assert docs[0]["data"] == raw and docs[0]["symbol"] == "AAPL"   # 응답 전체 보존(velocity 캡처)


def test_build_docs_asof_empty_response_makes_no_doc():
    assert build_docs(ESTIMATES, "AAPL", [], capture_date=CAP, fetched_at=FA) == []
    assert build_docs(ESTIMATES, "AAPL", None, capture_date=CAP, fetched_at=FA) == []


def test_build_docs_snapshot_keyed_by_symbol():
    raw = [{"symbol": "AAPL", "sector": "Technology"}]
    docs = build_docs(PROFILE, "AAPL", raw, capture_date=CAP, fetched_at=FA)
    assert docs == [{"id": "AAPL", "symbol": "AAPL", "source": "fmp",
                     "fetched_at": FA, "data": raw}]
    assert build_docs(PROFILE, "AAPL", [], capture_date=CAP, fetched_at=FA) == []


# ─────────────────────────────── run_factor_pass (shape 디스패치) ───────────────────────────────

class _Store:
    def __init__(self):
        self.docs = {}          # collection -> {id: doc}
        self.snaps = {}         # collection -> {id: doc}
    def filter_new_ids_in(self, col, ids):
        have = self.docs.get(col, {})
        return [i for i in ids if i not in have]
    def save_docs(self, col, docs):
        d = self.docs.setdefault(col, {})
        for x in docs:
            d[x["id"]] = x
        return len(docs)
    def save_snapshot(self, col, doc_id, data):
        self.snaps.setdefault(col, {})[doc_id] = data


def _fetch(mapping):
    # mapping: spec.key -> raw. 없으면 [].
    def f(spec, symbol):
        return mapping.get(spec.key, [])
    return f


def test_run_factor_pass_dispatches_by_shape():
    store = _Store()
    specs = [INCOME, ESTIMATES, PROFILE]
    fetch = _fetch({
        "income": [{"date": "2025-09-27", "revenue": 1}],
        "estimates": [{"date": "2030-09-27", "epsAvg": 8.1}],
        "profiles": [{"symbol": "AAPL", "sector": "Tech"}],
    })
    counts = run_factor_pass(store, fetch, ["AAPL"], specs, capture_date=CAP, fetched_at=FA)
    assert counts == {"income": 1, "estimates": 1, "profiles": 1}
    assert "AAPL__20250927" in store.docs["income"]          # history → save_docs
    assert "AAPL__20260713" in store.docs["estimates"]       # asof → save_docs(캡처일 키)
    assert store.snaps["profiles"]["AAPL"]["data"][0]["sector"] == "Tech"   # snapshot → save_snapshot


def test_run_factor_pass_history_writes_only_new_rows():
    store = _Store()
    fetch = _fetch({"income": [{"date": "2025-09-27", "revenue": 1}]})
    first = run_factor_pass(store, fetch, ["AAPL"], [INCOME], capture_date=CAP, fetched_at=FA)
    second = run_factor_pass(store, fetch, ["AAPL"], [INCOME], capture_date=CAP, fetched_at=FA)
    assert first == {"income": 1} and second == {"income": 0}    # dedup — 같은 행 재적재 안 함


def test_run_factor_pass_one_failure_does_not_block_others():
    store = _Store()

    def fetch(spec, symbol):
        if symbol == "BAD":
            raise RuntimeError("network")
        return [{"date": "2025-09-27", "revenue": 1}]

    counts = run_factor_pass(store, fetch, ["BAD", "AAPL"], [INCOME], capture_date=CAP, fetched_at=FA)
    assert counts == {"income": 1}                              # BAD 실패가 AAPL을 막지 않음


def test_run_factor_pass_iterates_universe_times_specs():
    store = _Store()
    fetch = _fetch({"income": [{"date": "2025-09-27", "revenue": 1}],
                    "profiles": [{"symbol": "X", "sector": "S"}]})
    counts = run_factor_pass(store, fetch, ["AAPL", "MSFT"], [INCOME, PROFILE],
                             capture_date=CAP, fetched_at=FA)
    assert counts == {"income": 2, "profiles": 2}              # 2 심볼 × 2 스펙
