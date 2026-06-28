import httpx
from newsstore.collect import body_fetch
from newsstore.collect.body_fetch import fetch_body

ARTICLE_HTML = (
    "<html><body>"
    "<div class='ad'>구독하세요 광고 " + "x" * 200 + "</div>"
    "<div class='article-body'>" + "한국 경제 본문 내용입니다. " * 8 + "</div>"
    "</body></html>"
)

def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))

def test_extracts_article_body_only():
    c = _client(lambda req: httpx.Response(200, text=ARTICLE_HTML))
    body = fetch_body(c, "https://e/x", ".article-body")
    assert "한국 경제 본문" in body
    assert "광고" not in body                       # .article-body 밖은 안 잡힘

def test_missing_selector_returns_empty():
    c = _client(lambda req: httpx.Response(200, text="<html><body><p>no</p></body></html>"))
    assert fetch_body(c, "https://e/x", ".article-body") == ""

def test_too_short_returns_empty():
    c = _client(lambda req: httpx.Response(200, text="<div class='article-body'>짧음</div>"))
    assert fetch_body(c, "https://e/x", ".article-body") == ""

def test_non_200_returns_empty():
    c = _client(lambda req: httpx.Response(403, text=ARTICLE_HTML))
    assert fetch_body(c, "https://e/x", ".article-body") == ""

def test_follows_redirect():
    def handler(req):
        if req.url.path == "/old":
            return httpx.Response(301, headers={"location": "https://e/new"})
        return httpx.Response(200, text=ARTICLE_HTML)
    assert "한국 경제 본문" in fetch_body(_client(handler), "https://e/old", ".article-body")

def test_exception_returns_empty():
    def handler(req):
        raise httpx.ConnectError("boom")
    assert fetch_body(_client(handler), "https://e/x", ".article-body") == ""
