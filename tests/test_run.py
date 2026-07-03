import types
import httpx
from newsstore.entrypoints import run_collect as run

FEEDS_YAML = (
    "feeds:\n"
    "  - {feed_id: f1, url: 'https://e/1.rss', source: S, poll_minutes: 0}\n"
    "  - {feed_id: f2, url: 'https://e/2.rss', source: S, poll_minutes: 0}\n"
)
RSS = (b'<?xml version="1.0"?><rss version="2.0"><channel>'
       b'<item><title>A</title><link>https://e/a</link>'
       b'<pubDate>Fri, 12 Jun 2026 06:00:00 GMT</pubDate></item></channel></rss>')

def _write_feeds(tmp_path):
    p = tmp_path / "feeds.yaml"
    p.write_text(FEEDS_YAML, encoding="utf-8")
    return p

def _patch_client(monkeypatch, handler):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(run, "make_client", lambda: client)

def test_main_returns_zero_on_success(tmp_path, monkeypatch):
    _patch_client(monkeypatch, lambda r: httpx.Response(200, content=RSS))
    monkeypatch.setattr(run, "make_store", lambda *a, **k: _FakeStore())
    rc = run.main(["--feeds", str(_write_feeds(tmp_path)), "--force"])
    assert rc == 0

def test_main_returns_nonzero_when_all_feeds_fail(tmp_path, monkeypatch):
    _patch_client(monkeypatch, lambda r: httpx.Response(500))
    monkeypatch.setattr(run, "make_store", lambda *a, **k: _FakeStore())
    rc = run.main(["--feeds", str(_write_feeds(tmp_path)), "--force"])
    assert rc == 1   # systemic outage must not look like success to the scheduler


class _FakeStore:
    def __enter__(self): return self
    def __exit__(self, *exc): pass
    def count(self): return 0          # run.main logs store.count()
    def set_meta(self, k, v): pass     # run.main writes meta sources
    def upsert_items(self, items): return len(items)
    def get_feed_state(self, fid): return {}
    def set_feed_state(self, fid, **kw): pass


def test_run_enrich_mode_report_wires_frame_then_report(monkeypatch, store):
    # --mode report가 (1) 그룹 발행 → (2) 프레임 패스 → (3) 리포트 패스 순서로 배선되는지 검증
    import newsstore.entrypoints.run_enrich as re_mod
    calls = []
    monkeypatch.setattr("newsstore.enrich.frames.run_frame_pass",
                        lambda *a, **k: calls.append("frames") or 0)
    monkeypatch.setattr("newsstore.enrich.report.run_report_pass",
                        lambda *a, **k: calls.append("report") or {"reported": 0})
    monkeypatch.setattr(re_mod, "make_store", lambda: store)
    monkeypatch.setattr(re_mod, "GeminiClient", lambda *a, **k: object())
    monkeypatch.setenv("GEMINI_API_KEY", "dummy")
    assert re_mod.main(["--mode", "report"]) == 0
    assert calls == ["frames", "report"]                # 프레임 선행(§4)
    # report 모드는 UI 앵커용 그룹 매핑을 발행한다(topics.yaml SSOT → meta/report_groups).
    # m1: Firestore map은 키가 정렬돼 순서를 잃으므로 순서 보존 배열([{name, lens_ids}])로 발행.
    doc = store.db.collection("meta").document("report_groups").get().to_dict() or {}
    assert {"name": "주식", "lens_ids": ["kr_equity", "us_equity"]} in (doc.get("groups") or [])


def test_run_uses_injected_store(monkeypatch):
    used = {}

    def fake_make_store(*a, **k):
        used["called"] = True
        return _FakeStore()

    monkeypatch.setattr(run, "make_store", fake_make_store)
    monkeypatch.setattr(run, "make_client", lambda: types.SimpleNamespace(close=lambda: None))
    monkeypatch.setattr(run, "load_feeds", lambda p: [])
    monkeypatch.setattr(run, "collect_once", lambda *a, **k: {})

    rc = run.main([])
    assert rc == 0 and used["called"] is True
