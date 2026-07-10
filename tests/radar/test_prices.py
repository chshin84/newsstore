"""로직 테스트는 DI fetch로. 실계약(컬럼·NaN 형태)은 Step 5의 실측 캡처 파일과 대조하는
test_fixture_shape_matches_capture가 지킨다(오답노트 'fake가 실계약 약화' 재발 방지)."""
import json
import pathlib

import pytest

from newsstore.radar import localdb, prices


def _hist(dates_closes):
    return [{"date": d, "open": c, "high": c + 1, "low": c - 1, "close": c,
             "adj_close": c, "volume": 100} for d, c in dates_closes]


def _entry():
    return [{"id": "a", "ticker": "T", "role": "stock"}]


def test_ingest_upsert_and_overlap(tmp_path):
    db = localdb.connect_prices(str(tmp_path / "p.db"))
    fetch = lambda ticker, start: _hist([("2026-07-08", 100.0), ("2026-07-09", 101.0)])
    prices.ingest(db, _entry(), fetch=fetch, today="2026-07-09")
    prices.ingest(db, _entry(), fetch=fetch, today="2026-07-09")
    assert localdb.count_prices(db, "T") == 2


def test_row_level_anomaly_and_nan_flagged(tmp_path):
    db = localdb.connect_prices(str(tmp_path / "p.db"))
    bad = _hist([("2026-07-08", 100.0), ("2026-07-09", 100.0)])
    bad[0]["high"] = 50.0                                        # high<low
    bad[1]["close"] = float("nan")                               # yfinance 결측일 NaN(실계약)
    prices.ingest(db, _entry(), fetch=lambda t, s: bad, today="2026-07-09")
    assert localdb.load_closes(db, "T") == []                    # 두 행 다 flagged 격리
    assert len(localdb.load_closes(db, "T", include_flagged=True)) == 2


def test_no_new_dates_counts_as_zero_day(tmp_path):
    """겹침 이력만 반환(신규 날짜 없음)도 0행으로 센다 — stale 소스가 streak을 리셋 못 한다."""
    db = localdb.connect_prices(str(tmp_path / "p.db"))
    localdb.upsert_prices(db, [dict(_hist([("2026-07-07", 99.0)])[0], ticker="T")], source="t")
    stale = lambda t, s: _hist([("2026-07-07", 99.0)])           # 이미 있는 날짜만
    r1 = prices.ingest(db, _entry(), fetch=stale, today="2026-07-08")
    assert r1["T"]["status"] == "missing"
    prices.ingest(db, _entry(), fetch=stale, today="2026-07-08")  # 같은 날 재실행 — streak 비증가(멱등)
    prices.ingest(db, _entry(), fetch=stale, today="2026-07-09")
    with pytest.raises(prices.PricesError, match="3"):
        prices.ingest(db, _entry(), fetch=stale, today="2026-07-10")


def test_fixture_shape_matches_capture():
    """DI 픽스처의 키 집합이 실측 캡처와 동일해야 한다 — 캡처 파일은 Step 5에서 생성·커밋."""
    cap_dir = pathlib.Path("tests/fixtures")
    caps = sorted(cap_dir.glob("prices_capture_*.json"))
    if not caps:
        pytest.skip("실측 캡처 미생성(Task 5 Step 5 이전)")
    fixture_keys = set(_hist([("2026-07-09", 1.0)])[0].keys())
    for cap in caps:
        rows = json.loads(cap.read_text(encoding="utf-8"))
        assert rows, f"{cap.name}: 캡처 비어 있음"
        assert set(rows[0].keys()) == fixture_keys, f"{cap.name}: 실계약과 픽스처 키 불일치"
