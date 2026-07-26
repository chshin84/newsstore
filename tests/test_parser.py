from datetime import datetime, timezone
from pathlib import Path
from newsstore.collect.feeds import FeedConfig, make_id
from newsstore.collect.parser import parse_feed

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

def test_non_feed_content_raises_parse_error():
    # WAF 차단·Cloudflare 챌린지·HTML 오류 페이지는 HTTP 200으로 오지만 피드가
    # 아니다 — '0건 수집 성공'으로 삼키지 말고 fail-loud(#collect 조용한 무수집 방지).
    import pytest
    from newsstore.collect.parser import FeedParseError
    waf = (b'<!DOCTYPE html><html><head><title>Just a moment...</title></head>'
           b'<body>Checking your browser</body></html>')
    with pytest.raises(FeedParseError):
        parse_feed(waf, FEED, fetched_at=NOW)

def test_wellformed_html_page_still_raises_parse_error():
    # 정상형(well-formed) XML인 차단 페이지는 bozo=0이라 bozo만으론 못 잡는다 —
    # 피드 포맷 미인식(version 없음)도 실패로 분류해야 한다.
    import pytest
    from newsstore.collect.parser import FeedParseError
    html = b'<html><body>Access denied</body></html>'
    with pytest.raises(FeedParseError):
        parse_feed(html, FEED, fetched_at=NOW)

def test_empty_body_raises_parse_error():
    # 본문이 0바이트인 200 응답에서는 feedparser 결과에 version 키가 **아예 없다**
    # (bozo=0). 속성 접근으로 읽으면 가드가 스스로 AttributeError로 터져 원인이
    # 'parse/store error'로 뭉개진다 — 2026-07-25 프로덕션에서 15분마다 재발했다.
    # 가드는 죽지 말고 이 응답을 FeedParseError로 분류해야 한다.
    import pytest
    from newsstore.collect.parser import FeedParseError
    with pytest.raises(FeedParseError):
        parse_feed(b"", FEED, fetched_at=NOW)

def test_valid_empty_feed_is_legitimate_zero():
    # 인식된 피드 포맷의 항목 0건은 합법(신규 없음) — 실패가 아니다.
    raw = (b'<?xml version="1.0"?><rss version="2.0"><channel>'
           b'<title>Empty</title></channel></rss>')
    assert parse_feed(raw, FEED, fetched_at=NOW) == []

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
