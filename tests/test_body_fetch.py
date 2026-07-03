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

def test_fetch_body_passes_article_timeout():
    # 스펙 §2.3·§6 회귀 가드: per-article 타임아웃 인자가 빠지면 클라이언트 기본(90s)을
    # 상속해 한 기사 hang이 Job 타임아웃까지 번진다 — 인자 전달 자체를 고정한다.
    from newsstore.collect.body_fetch import ARTICLE_TIMEOUT_S
    seen = {}

    class _Client:
        def get(self, url, **kw):
            seen.update(kw)
            raise httpx.ConnectError("stop")            # 전달 검증만 — 이후 경로 불필요
    assert fetch_body(_Client(), "https://e/a", ".b") == ""   # no-raise 계약 유지
    assert seen.get("timeout") == ARTICLE_TIMEOUT_S


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


def test_unexpected_error_logged_but_returns_empty(monkeypatch, caplog):
    # 비기대(파싱/코드) 예외는 ""로 위장하지 말고 표면화(로깅) — no-raise 계약은 유지
    def boom(*a, **k):
        raise ValueError("parse bug")
    monkeypatch.setattr(body_fetch, "BeautifulSoup", boom)
    c = _client(lambda req: httpx.Response(200, text=ARTICLE_HTML))
    with caplog.at_level("ERROR"):
        assert fetch_body(c, "https://e/x", ".article-body") == ""
    assert any("unexpected" in r.message for r in caplog.records)


# --- enrich_bodies tests ---

from datetime import datetime, timezone
from newsstore.contracts.models import RawItem
from newsstore.collect.body_fetch import enrich_bodies, MAX_FETCH_PER_FEED

NOW = datetime(2026, 6, 12, 7, 0, tzinfo=timezone.utc)

class FakeStore:
    def __init__(self, stored=()): self.stored = set(stored)
    def filter_new_ids(self, ids): return [i for i in ids if i not in self.stored]

def _hk(i, body=""):
    return RawItem(id=i, feed_id="hk", source="한국경제",
                   url=f"https://e/{i}", title=f"t{i}", body=body, fetched_at=NOW)

def test_enrich_fills_whitelisted_new_headline(monkeypatch):
    monkeypatch.setattr(body_fetch.time, "sleep", lambda *_: None)
    monkeypatch.setattr(body_fetch, "fetch_body", lambda c, u, s: "채운 본문 " * 5)
    items = [_hk("a"), _hk("b")]
    out = enrich_bodies(client=None, store=FakeStore(), items=items)
    assert all(it.body for it in out)
    assert out[0].title == "ta"                      # title 불변

def test_enrich_skips_non_whitelist_and_stored_and_has_body(monkeypatch):
    monkeypatch.setattr(body_fetch.time, "sleep", lambda *_: None)
    monkeypatch.setattr(body_fetch, "fetch_body", lambda c, u, s: "X" * 100)
    other = RawItem(id="o", feed_id="bz", source="Benzinga", url="https://e/o", title="o", fetched_at=NOW)
    stored = _hk("s"); hasbody = _hk("h", body="already")
    out = enrich_bodies(None, FakeStore(stored=["s"]), [other, stored, hasbody])
    assert other.body == "" and stored.body == "" and hasbody.body == "already"

def test_enrich_caps_per_feed(monkeypatch):
    monkeypatch.setattr(body_fetch.time, "sleep", lambda *_: None)
    calls = {"n": 0}
    def fb(c, u, s): calls["n"] += 1; return "Y" * 100
    monkeypatch.setattr(body_fetch, "fetch_body", fb)
    items = [_hk(str(i)) for i in range(MAX_FETCH_PER_FEED + 5)]
    enrich_bodies(None, FakeStore(), items)
    assert calls["n"] == MAX_FETCH_PER_FEED          # 상한만 fetch

def test_enrich_logs_error_on_high_empty_rate(monkeypatch, caplog):
    monkeypatch.setattr(body_fetch.time, "sleep", lambda *_: None)
    monkeypatch.setattr(body_fetch, "fetch_body", lambda c, u, s: "")   # 전부 빈본문
    with caplog.at_level("ERROR"):
        enrich_bodies(None, FakeStore(), [_hk("a"), _hk("b")])
    assert any(r.levelname == "ERROR" for r in caplog.records)
