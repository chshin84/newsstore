from datetime import datetime, timezone
import httpx
from newsstore.collect import fmp_news
from newsstore.collect.fmp_news import map_standard_row, _parse_dt, _clean
from newsstore.collect.fmp_news import map_article_row, _first_ticker
from newsstore.collect.fmp_news import run_fmp_news_pass, _fetch_all_pages, PAGE_LIMIT

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


# --- run_fmp_news_pass 오케스트레이션(고정 lookback·429·건강·격리) ---

class FakeStore:
    def __init__(self): self.state = {}; self.saved = []
    def get_feed_state(self, fid): return dict(self.state.get(fid, {}))
    def set_feed_state(self, fid, **f): self.state.setdefault(fid, {}).update(f)
    def upsert_items_batched(self, items):
        ids = {i.id for i in items} - {i.id for i in self.saved}
        self.saved.extend(i for i in items if i.id in ids)
        return len(ids)

def _row(u): return {"symbol":"AAPL","publishedDate":"2026-07-18 22:45:00",
                     "publisher":"P","title":"t","text":"b","url":u}
NOW = datetime(2026,7,19,tzinfo=timezone.utc)

def test_pass_collects_and_marks_health():
    store = FakeStore()
    def fetch(frm,to,page): return [_row(f"http://x/{n}") for n in range(3)] if page==0 else []
    summary = run_fmp_news_pass(store, {"stock-latest": fetch}, ["stock-latest"], now=NOW, delay_s=0)
    assert summary["fmp:stock-latest"] == 3
    assert store.state["fmp:stock-latest"]["consecutive_failures"] == 0
    assert store.state["fmp:stock-latest"]["last_success"] == NOW

def test_pass_idempotent_rescan():
    # poll_minutes=0 → 항상 due. 2차 패스가 dedup 경로에 실제 도달해 멱등 불변식을 검증(리뷰 AA1).
    store = FakeStore()
    def fetch(frm,to,page): return [_row("http://x/1")] if page==0 else []
    run_fmp_news_pass(store, {"stock-latest": fetch}, ["stock-latest"], now=NOW, poll_minutes=0, delay_s=0)
    s2 = run_fmp_news_pass(store, {"stock-latest": fetch}, ["stock-latest"], now=NOW, poll_minutes=0, delay_s=0)
    assert s2["fmp:stock-latest"] == 0        # 재스캔 무-write(불변식)

def test_pass_isolates_endpoint_failure():
    store = FakeStore()
    def ok(frm,to,page): return [_row("http://ok/1")] if page==0 else []
    def boom(frm,to,page): raise RuntimeError("connection reset")
    summary = run_fmp_news_pass(store, {"stock-latest": ok, "forex-latest": boom},
                                ["stock-latest","forex-latest"], now=NOW, delay_s=0)
    assert summary["fmp:stock-latest"] == 1 and summary["fmp:forex-latest"] == -1
    assert store.state["fmp:forex-latest"]["consecutive_failures"] == 1

def test_pass_separate_feed_state_keys():
    store = FakeStore()
    def fetch(frm,to,page): return [_row("http://x/1")] if page==0 else []
    run_fmp_news_pass(store, {"stock-latest": fetch, "general-latest": fetch},
                      ["stock-latest","general-latest"], now=NOW, delay_s=0)
    assert "fmp:stock-latest" in store.state and "fmp:general-latest" in store.state

def test_pass_respects_poll_not_due():
    store = FakeStore()
    store.state["fmp:stock-latest"] = {"last_fetched": datetime(2026,7,19,tzinfo=timezone.utc)}
    def fetch(frm,to,page): raise AssertionError("should not fetch")
    later = datetime(2026,7,19,0,30,tzinfo=timezone.utc)   # 30분 < poll 1440 → 스킵
    summary = run_fmp_news_pass(store, {"stock-latest": fetch}, ["stock-latest"],
                                now=later, poll_minutes=1440, delay_s=0)
    assert "fmp:stock-latest" not in summary

def test_fetch_all_pages_flags_truncation():
    # 매 페이지 가득(PAGE_LIMIT) → max_pages 소진 → truncated True(리뷰 CC1).
    def full(frm,to,page): return [_row(f"http://x/{page}/{n}") for n in range(PAGE_LIMIT)]
    rows, truncated = _fetch_all_pages(full, "a","b", max_pages=2, delay_s=0)
    assert truncated is True and len(rows) == 2*PAGE_LIMIT

def test_fetch_all_pages_stops_on_short_page():
    def short(frm,to,page): return [_row("http://x/1")] if page==0 else []
    rows, truncated = _fetch_all_pages(short, "a","b", max_pages=5, delay_s=0)
    assert truncated is False and len(rows) == 1

def test_pass_fmp_articles_cap_is_not_error():
    # fmp-articles(PAGE_CAP=2)가 매 페이지 가득이어도 절단을 건강 이상으로 기록하지 않는다(리뷰 AA5).
    store = FakeStore()
    def full(frm,to,page): return [{"title":"t","date":"2026-07-18 22:45:00","content":"c",
                                    "tickers":"NASDAQ:META","link":f"https://fmp/{page}/{n}"} for n in range(PAGE_LIMIT)]
    run_fmp_news_pass(store, {"fmp-articles": full}, ["fmp-articles"], now=NOW, delay_s=0)
    assert store.state["fmp:fmp-articles"].get("last_error") in (None,)   # 오탐 없음

def test_get_page_retries_on_429(monkeypatch):
    # 실제 httpx.HTTPStatusError(429) 경로가 재시도되는지(리뷰 AA4).
    monkeypatch.setattr(fmp_news.time, "sleep", lambda *_: None)
    req = httpx.Request("GET", "http://x")
    calls = {"n": 0}
    def fetch(frm,to,page):
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.HTTPStatusError("429", request=req, response=httpx.Response(429, request=req))
        return [_row("http://x/1")] if page == 0 else []
    rows, _ = _fetch_all_pages(fetch, "a","b", max_pages=1, delay_s=0, retries=2)
    assert calls["n"] == 2 and len(rows) == 1
