from newsstore.radar import localdb


def _mkitem(i, ts):
    return {"id": f"it{i}", "feed_id": "f1", "source": "src", "asset_hint": "kr_stock",
            "language": "ko", "url": f"http://x/{i}", "title": f"제목 {i}", "body": "본문",
            "published_at": ts, "fetched_at": ts, "kind": "story"}


def test_items_upsert_idempotent(tmp_path):
    db = localdb.connect_items(str(tmp_path / "local.db"))
    rows = [_mkitem(1, "2026-07-01T00:00:00Z"), _mkitem(2, "2026-07-02T00:00:00Z")]
    localdb.upsert_items(db, rows)
    localdb.upsert_items(db, rows)
    assert localdb.count_items(db) == len(rows)


def test_watermark_roundtrip(tmp_path):
    db = localdb.connect_items(str(tmp_path / "local.db"))
    assert localdb.get_watermark(db) is None
    localdb.set_watermark(db, "2026-07-02T00:00:00Z")
    assert localdb.get_watermark(db) == "2026-07-02T00:00:00Z"


def test_kst_day_conversion():
    assert localdb.kst_day("2026-07-09T16:00:00Z") == "2026-07-10"   # UTC 16시 = KST 익일 01시
    assert localdb.kst_day("2026-07-10T02:00:00Z") == "2026-07-10"


def test_prices_upsert_and_flag(tmp_path):
    db = localdb.connect_prices(str(tmp_path / "prices.db"))
    rows = [{"ticker": "000660.KS", "date": "2026-07-09", "open": 100, "high": 110,
             "low": 90, "close": 105, "adj_close": 105, "volume": 1000}]
    localdb.upsert_prices(db, rows, source="yfinance")
    localdb.upsert_prices(db, rows, source="yfinance")
    assert localdb.count_prices(db, "000660.KS") == 1
    localdb.flag_price(db, "000660.KS", "2026-07-09", "high<low")
    assert len(localdb.load_closes(db, "000660.KS", include_flagged=True)) == 1
    assert localdb.load_closes(db, "000660.KS") == []


def test_flag_cleared_by_correction_upsert(tmp_path):
    """정정값 upsert는 flagged를 리셋한다(자가 치유 — ingest가 upsert 직후 재검사)."""
    db = localdb.connect_prices(str(tmp_path / "prices.db"))
    rows = [{"ticker": "000660.KS", "date": "2026-07-09", "open": 100, "high": 110,
             "low": 90, "close": 105, "adj_close": 105, "volume": 1000}]
    localdb.upsert_prices(db, rows, source="yfinance")
    localdb.flag_price(db, "000660.KS", "2026-07-09", "high<low")
    assert localdb.load_closes(db, "000660.KS") == []
    corrected = [{"ticker": "000660.KS", "date": "2026-07-09", "open": 100, "high": 112,
                  "low": 90, "close": 106, "adj_close": 106, "volume": 1000}]
    localdb.upsert_prices(db, corrected, source="yfinance")
    assert localdb.load_closes(db, "000660.KS") == [("2026-07-09", 106.0)]
