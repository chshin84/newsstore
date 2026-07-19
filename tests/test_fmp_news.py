from datetime import datetime, timezone
from newsstore.collect import fmp_news
from newsstore.collect.fmp_news import map_standard_row, _parse_dt, _clean
from newsstore.collect.fmp_news import map_article_row, _first_ticker

def test_parse_dt_converts_et_to_utc():
    # FMP publishedDate는 미 동부시간(2026-07-19 실측: 저장 UTC 대비 +4h=EDT). 값(offset)으로 검증.
    assert _parse_dt("2026-07-18 22:45:00") == datetime(2026, 7, 19, 2, 45, tzinfo=timezone.utc)   # EDT +4h
    # 겨울(EST=UTC-5) DST 전환도 ZoneInfo가 처리 — 고정 오프셋이면 이 케이스가 어긋난다.
    assert _parse_dt("2026-01-15 22:45:00") == datetime(2026, 1, 16, 3, 45, tzinfo=timezone.utc)   # EST +5h

def test_parse_dt_bad_returns_none():
    assert _parse_dt("") is None and _parse_dt("nonsense") is None

def test_clean_strips_html():
    assert _clean("<p>hi <b>there</b></p>") == "hi there"

def test_map_standard_row_full():
    row = {"symbol": "AAPL", "publishedDate": "2026-07-18 22:45:00",
           "publisher": "The Motley Fool", "site": "fool.com",
           "title": "Apple x", "text": "lead para", "url": "https://fool.com/a"}
    item = map_standard_row(row, "stock-latest", datetime(2026, 7, 19, tzinfo=timezone.utc))
    assert item.symbol == "AAPL"
    assert item.url == "https://fool.com/a"
    assert item.body == "lead para"
    assert item.feed_id == "fmp:stock-latest"

def test_map_standard_row_empty_symbol_ok():
    row = {"symbol": None, "publishedDate": "2026-07-18 22:03:55",
           "publisher": "Reuters", "title": "macro", "text": "", "url": "https://r/1"}
    item = map_standard_row(row, "general-latest", datetime(2026,7,19,tzinfo=timezone.utc))
    assert item.symbol == ""

def test_map_standard_row_no_basis_returns_none():
    assert map_standard_row({"url": "", "title": ""}, "stock-latest",
                            datetime(2026,7,19,tzinfo=timezone.utc)) is None

def test_first_ticker_strips_exchange():
    assert _first_ticker("NASDAQ:META") == "META"
    assert _first_ticker("NASDAQ:META,NYSE:GS") == "META"
    assert _first_ticker("") == ""

def test_map_article_row_variant_fields():
    row = {"title": "Meta downgrade", "date": "2026-06-05 20:23:22",
           "content": "<ul><li><strong>Citigroup</strong> cut META</li></ul>",
           "tickers": "NASDAQ:META", "link": "https://fmp/meta", "site": "Financial Modeling Prep"}
    item = map_article_row(row, datetime(2026,7,19,tzinfo=timezone.utc))
    assert item.url == "https://fmp/meta"
    assert item.symbol == "META"
    assert "Citigroup cut META" in item.body
    assert item.feed_id == "fmp:fmp-articles"


# --- FakeDb로 upsert_items_batched의 get_all 배치 read 경로 검증(리뷰 CC6) ---

class _FakeRef:
    def __init__(self, id): self.id = id
class _FakeCol:
    def document(self, i): return _FakeRef(i)
class _FakeBatch:
    def set(self, ref, doc): pass
    def commit(self): pass
class _FakeDb:
    def __init__(self): self.get_all_calls = 0; self.per_item_gets = 0
    def collection(self, name): return _FakeCol()
    def get_all(self, refs): self.get_all_calls += 1; return []   # 아무것도 없음 → 전부 신규
    def batch(self): return _FakeBatch()

def test_upsert_batched_uses_get_all_not_per_item():
    from newsstore.store.firestore_store import FirestoreStore
    from newsstore.contracts.models import RawItem
    db = _FakeDb(); store = FirestoreStore(db)
    now = datetime(2026,7,19,tzinfo=timezone.utc)
    items = [RawItem(id=str(i), feed_id="fmp:stock-latest", source="X",
                     url=f"http://x/{i}", title="t", fetched_at=now) for i in range(5)]
    assert store.upsert_items_batched(items) == 5
    assert db.get_all_calls >= 1 and db.per_item_gets == 0        # 배치 read, per-item get 없음
