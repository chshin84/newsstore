import httpx
from newsstore.collect.feeds import FeedConfig
from newsstore.collect.fetcher import fetch_feed, DEFAULT_HEADERS

FEED = FeedConfig(feed_id="f1", url="https://e/x.rss", source="S")

def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))

def test_200_returns_content_and_validators():
    def handler(req):
        return httpx.Response(200, content=b"<rss/>",
                              headers={"ETag": "W/\"v1\"", "Last-Modified": "Mon"})
    with _client(handler) as c:
        res = fetch_feed(c, FEED)
        assert res.status == 200 and res.content == b"<rss/>"
        assert res.etag == "W/\"v1\"" and res.last_modified == "Mon"

def test_fetch_sends_browser_user_agent():
    seen = {}
    def handler(req):
        seen["ua"] = req.headers.get("user-agent", "")
        return httpx.Response(200, content=b"<rss/>")
    with _client(handler) as c:
        fetch_feed(c, FEED)
    assert seen["ua"].startswith("Mozilla/"), f"Got UA: {seen['ua']!r}"


def test_conditional_headers_sent_and_304_handled():
    seen = {}
    def handler(req):
        seen["inm"] = req.headers.get("If-None-Match")
        seen["ims"] = req.headers.get("If-Modified-Since")
        return httpx.Response(304)
    with _client(handler) as c:
        res = fetch_feed(c, FEED, etag="W/\"v1\"", last_modified="Mon")
        assert res.status == 304 and res.content == b""
        assert seen["inm"] == "W/\"v1\"" and seen["ims"] == "Mon"
