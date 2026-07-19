from datetime import datetime, timezone, timedelta
import httpx
from newsstore.collect.feeds import FeedConfig
from newsstore.store.firestore_store import FirestoreStore
from newsstore.collect.collector import is_due, collect_once

NOW = datetime(2026, 6, 12, 7, 0, tzinfo=timezone.utc)
RSS = (b'<?xml version="1.0"?><rss version="2.0"><channel>'
       b'<item><title>A</title><link>https://e/a</link>'
       b'<pubDate>Fri, 12 Jun 2026 06:00:00 GMT</pubDate></item></channel></rss>')

def test_is_due():
    assert is_due({}, 60, NOW) is True
    assert is_due({"last_fetched": NOW - timedelta(minutes=61)}, 60, NOW) is True
    assert is_due({"last_fetched": NOW - timedelta(minutes=10)}, 60, NOW) is False

def test_body_mode_rejects_unknown():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):     # calendar(미구현)·typo는 설정 로드 시 fail-loud
        FeedConfig(feed_id="f", url="https://e/x", source="S", body_mode="calendar")

def test_collect_once_stores_items_and_skips_not_due(store):
    feed = FeedConfig(feed_id="f1", url="https://e/x.rss", source="S", poll_minutes=60)
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=RSS)))
    s1 = collect_once(client, store, [feed], now=NOW, force=True)
    assert s1 == {"f1": 1} and store.count() == 1
    # second run, not due (last_fetched just set) -> skipped
    s2 = collect_once(client, store, [feed], now=NOW + timedelta(minutes=5))
    assert s2 == {} and store.count() == 1

def test_collect_once_304_is_zero_new(store):
    feed = FeedConfig(feed_id="f1", url="https://e/x.rss", source="S", poll_minutes=0)
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(304)))
    s = collect_once(client, store, [feed], now=NOW, force=True)
    assert s == {"f1": 0}

def test_collect_once_isolates_feed_failure(fsclient):
    # 한 피드의 저장 예외가 다른 피드 수집을 막지 않아야 한다.
    class FlakyStore(FirestoreStore):
        def upsert_items(self, items):
            if items and items[0].feed_id == "bad":
                raise RuntimeError("db boom")
            return super().upsert_items(items)

    bad = FeedConfig(feed_id="bad", url="https://e/b.rss", source="S", poll_minutes=0)
    good = FeedConfig(feed_id="good", url="https://e/g.rss", source="S", poll_minutes=0)
    store = FlakyStore(fsclient)
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=RSS)))
    s = collect_once(client, store, [bad, good], now=NOW, force=True)
    assert s["bad"] == -1          # 실패는 격리되어 -1
    assert s["good"] == 1          # 나머지 피드는 정상 수집
    assert store.count() == 1


def test_collect_once_blocked_page_is_failure_not_zero(store):
    # HTTP 200 + 차단 페이지 응답은 -1(실패)로 집계되고, 그 응답의 ETag·last_fetched를
    # 피드 상태에 저장하지 않아야 한다(차단 페이지에 304 받아 무수집 고착 방지).
    feed = FeedConfig(feed_id="f1", url="https://e/x.rss", source="S", poll_minutes=0)
    html = b"<html><body>Access denied</body></html>"
    client = httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, content=html, headers={"ETag": 'W/"waf"'})))
    s = collect_once(client, store, [feed], now=NOW, force=True)
    assert s == {"f1": -1}
    state = store.get_feed_state("f1")
    assert not state.get("etag") and not state.get("last_fetched")


def test_collect_once_records_feed_health(store):
    # 성공 시 last_success + 연속실패 리셋, 실패 시 연속실패 누적 · last_error 기록(커서 불변).
    feed = FeedConfig(feed_id="h1", url="https://e/g.rss", source="S", poll_minutes=0)
    ok = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=RSS)))
    bad = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500)))

    collect_once(ok, store, [feed], now=NOW, force=True)
    st = store.get_feed_state("h1")
    assert st["last_success"] is not None and st["consecutive_failures"] == 0

    collect_once(bad, store, [feed], now=NOW + timedelta(minutes=1), force=True)
    st = store.get_feed_state("h1")
    assert st["consecutive_failures"] == 1 and st["last_error"]         # 실패 1회 + 에러 기록

    collect_once(bad, store, [feed], now=NOW + timedelta(minutes=2), force=True)
    assert store.get_feed_state("h1")["consecutive_failures"] == 2       # 누적

    collect_once(ok, store, [feed], now=NOW + timedelta(minutes=3), force=True)
    assert store.get_feed_state("h1")["consecutive_failures"] == 0       # 성공 시 리셋


def test_collect_once_fills_hankyung_body(monkeypatch, store):
    from newsstore.collect import body_fetch
    monkeypatch.setitem(body_fetch.BODY_SELECTORS, "한국경제", ".article-body")   # 본문만 가지치기로 프로덕션 맵은 비었음 — 메커니즘은 주입으로 검증
    monkeypatch.setattr(body_fetch.time, "sleep", lambda *_: None)

    RSS_HK = ("<rss><channel><item><title>제목</title>"
              "<link>https://www.hankyung.com/article/1</link>"
              "<guid>https://www.hankyung.com/article/1</guid>"
              "</item></channel></rss>")
    ART = "<div class='article-body'>" + "한경 본문 내용. " * 10 + "</div>"
    def handler(req):
        return httpx.Response(200, text=ART if "article" in str(req.url) else RSS_HK)
    client = httpx.Client(transport=httpx.MockTransport(handler))

    feeds = [FeedConfig(feed_id="hk_economy", url="https://www.hankyung.com/feed/economy",
                        source="한국경제", language="ko", body_mode="headline")]
    collect_once(client, store, feeds, force=True)
    saved = [d.to_dict() for d in store.db.collection("items").stream()]
    hk = [d for d in saved if d.get("feed_id") == "hk_economy"][0]
    assert "한경 본문" in hk["body"]
