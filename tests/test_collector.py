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
