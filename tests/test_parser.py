from datetime import datetime, timezone
from pathlib import Path
from newsstore.models import FeedConfig, make_id
from newsstore.parser import parse_feed

FEED = FeedConfig(feed_id="f1", url="u", source="Sample", asset_hint="us_stock", language="en")
NOW = datetime(2026, 6, 12, 7, 0, tzinfo=timezone.utc)

def _raw():
    return Path("tests/fixtures/sample_rss.xml").read_bytes()

def test_parses_items_and_strips_html():
    items = parse_feed(_raw(), FEED, fetched_at=NOW)
    assert len(items) == 2
    first = items[0]
    assert first.title == "Banks Curb Hedge Fund Bets on SK Hynix"
    assert first.url == "https://example.com/a"
    assert "curbing leveraged bets" in first.body and "<b>" not in first.body
    assert first.published_at == datetime(2026, 6, 12, 6, 41, tzinfo=timezone.utc)
    assert first.id == make_id("https://example.com/a")
    assert first.fetched_at == NOW

def test_item_without_link_uses_title_fallback_id():
    items = parse_feed(_raw(), FEED, fetched_at=NOW)
    assert items[1].id == make_id("", fallback="No Link Item")
