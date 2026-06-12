from datetime import datetime, timezone, timedelta
import httpx
from newsstore.models import FeedConfig
from newsstore.store.sqlite_store import SqliteStore
from newsstore.collector import is_due, collect_once

NOW = datetime(2026, 6, 12, 7, 0, tzinfo=timezone.utc)
RSS = (b'<?xml version="1.0"?><rss version="2.0"><channel>'
       b'<item><title>A</title><link>https://e/a</link>'
       b'<pubDate>Fri, 12 Jun 2026 06:00:00 GMT</pubDate></item></channel></rss>')

def test_is_due():
    assert is_due({}, 60, NOW) is True
    assert is_due({"last_fetched": NOW - timedelta(minutes=61)}, 60, NOW) is True
    assert is_due({"last_fetched": NOW - timedelta(minutes=10)}, 60, NOW) is False

def test_collect_once_stores_items_and_skips_not_due(tmp_path):
    feed = FeedConfig(feed_id="f1", url="https://e/x.rss", source="S", poll_minutes=60)
    store = SqliteStore(tmp_path / "db.sqlite")
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=RSS)))
    s1 = collect_once(client, store, [feed], now=NOW, force=True)
    assert s1 == {"f1": 1} and store.count() == 1
    # second run, not due (last_fetched just set) -> skipped
    s2 = collect_once(client, store, [feed], now=NOW + timedelta(minutes=5))
    assert s2 == {} and store.count() == 1

def test_collect_once_304_is_zero_new(tmp_path):
    feed = FeedConfig(feed_id="f1", url="https://e/x.rss", source="S", poll_minutes=0)
    store = SqliteStore(tmp_path / "db.sqlite")
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(304)))
    s = collect_once(client, store, [feed], now=NOW, force=True)
    assert s == {"f1": 0}
