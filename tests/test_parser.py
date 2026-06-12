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

_FULL_RSS = (
    b'<?xml version="1.0"?>'
    b'<rss xmlns:content="http://purl.org/rss/1.0/modules/content/" version="2.0">'
    b'<channel><item><title>T</title><link>https://e/a</link>'
    b'<description>short summary</description>'
    b'<content:encoded><![CDATA[<p>FULL body text here</p>]]></content:encoded>'
    b'</item></channel></rss>')

def _parse_with_mode(mode):
    feed = FeedConfig(feed_id="f1", url="u", source="S", body_mode=mode)
    return parse_feed(_FULL_RSS, feed, fetched_at=NOW)[0]

def test_body_mode_headline_stores_no_body():
    assert _parse_with_mode("headline").body == ""

def test_body_mode_summary_stores_description_not_full():
    assert _parse_with_mode("summary").body == "short summary"

def test_body_mode_full_stores_full_content():
    assert _parse_with_mode("full").body == "FULL body text here"

def test_guid_used_as_dedup_basis_when_no_link():
    raw = (b'<?xml version="1.0"?><rss version="2.0"><channel>'
           b'<item><title>T</title><guid>urn:news:abc-123</guid>'
           b'<description>body</description></item></channel></rss>')
    items = parse_feed(raw, FEED, fetched_at=NOW)
    assert len(items) == 1
    assert items[0].id == make_id("urn:news:abc-123")

def test_entry_without_link_guid_or_title_is_skipped():
    raw = (b'<?xml version="1.0"?><rss version="2.0"><channel>'
           b'<item><description>orphan body, no identity</description></item>'
           b'<item><title>Keep</title><link>https://e/k</link></item>'
           b'</channel></rss>')
    items = parse_feed(raw, FEED, fetched_at=NOW)
    # the identity-less item must be dropped (not collapsed onto sha1("")), the other kept
    assert [i.title for i in items] == ["Keep"]
    assert items[0].id == make_id("https://e/k")

def test_tz_offset_corrects_naive_local_pubdate():
    # infomax emits naive KST wall-clock with no offset; tz_offset=9 must
    # reinterpret it as KST and store the true UTC instant (19:56 KST -> 10:56 UTC).
    raw = (b'<?xml version="1.0"?><rss version="2.0"><channel>'
           b'<item><title>T</title><link>https://e/a</link>'
           b'<pubDate>2026-06-12 19:56:57</pubDate></item></channel></rss>')
    feed = FeedConfig(feed_id="infomax", url="u", source="S", tz_offset=9)
    items = parse_feed(raw, feed, fetched_at=NOW)
    assert items[0].published_at == datetime(2026, 6, 12, 10, 56, 57, tzinfo=timezone.utc)

def test_published_at_is_utc_regardless_of_host_tz(monkeypatch):
    # pubDate is "06:41:00 GMT" — must parse to 06:41 UTC even when the host
    # TZ is not UTC. Guards against time.mktime() (local-time) regressions.
    import os, time
    monkeypatch.setenv("TZ", "Asia/Seoul")
    if hasattr(time, "tzset"):
        time.tzset()
    try:
        items = parse_feed(_raw(), FEED, fetched_at=NOW)
        assert items[0].published_at == datetime(2026, 6, 12, 6, 41, tzinfo=timezone.utc)
    finally:
        os.environ.pop("TZ", None)
        if hasattr(time, "tzset"):
            time.tzset()
