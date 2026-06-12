import httpx
from newsstore import run
from newsstore import run as run_mod

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
    rc = run.main(["--feeds", str(_write_feeds(tmp_path)),
                   "--db", str(tmp_path / "db.sqlite"), "--force"])
    assert rc == 0

def test_main_returns_nonzero_when_all_feeds_fail(tmp_path, monkeypatch):
    _patch_client(monkeypatch, lambda r: httpx.Response(500))
    rc = run.main(["--feeds", str(_write_feeds(tmp_path)),
                   "--db", str(tmp_path / "db.sqlite"), "--force"])
    assert rc == 1   # systemic outage must not look like success to the scheduler


def test_run_uses_factory_with_env_backend(monkeypatch, tmp_path):
    captured = {}

    class FakeStore:
        def __enter__(self): return self
        def __exit__(self, *exc): pass
        def count(self): return 0          # run.main logs store.count()

    def fake_make_store(backend, **kw):
        captured["backend"] = backend
        return FakeStore()

    monkeypatch.setenv("NEWSSTORE_BACKEND", "sqlite")
    monkeypatch.setattr(run_mod, "make_store", fake_make_store)
    monkeypatch.setattr(run_mod, "make_client", lambda: object())
    monkeypatch.setattr(run_mod, "load_feeds", lambda p: [])
    monkeypatch.setattr(run_mod, "collect_once", lambda *a, **k: {})

    rc = run_mod.main(["--db", str(tmp_path / "db.sqlite")])
    assert rc == 0
    assert captured["backend"] == "sqlite"
