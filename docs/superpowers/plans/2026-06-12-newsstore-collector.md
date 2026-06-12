# newsstore Collector (Step 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone news collector that polls a registry of RSS feeds, deduplicates items, and stores them in a durable raw store — with NO LLM/tagging (that is Step 2).

**Architecture:** Decoupled collector. A scheduler (external: Cloud Scheduler/cron) invokes `run.py` periodically. For each feed whose poll interval is due, the collector does a conditional HTTP GET (ETag/Last-Modified), parses entries with `feedparser`, normalizes to a `RawItem`, and upserts by URL-hash id into a `Store`. The `Store` is an interface with a SQLite implementation (dev/verification, runs in Docker with no cloud creds) and a later Firestore implementation (same interface). Runs in the existing Python 3.12 Docker image with the ePrism `office|home` SSL split.

**Tech Stack:** Python 3.12, httpx (HTTP + ePrism SSL verify), feedparser (RSS/Atom), beautifulsoup4+lxml (HTML strip), pydantic v2 (models), pyyaml (feed registry), sqlite3 (stdlib store), pytest (TDD). Everything runs via Docker (`no-local-python`).

---

## File Structure

```
pyproject.toml                     # package + deps (replaces placeholder)
config/feeds.yaml                  # the feed registry (data)
src/newsstore/__init__.py
src/newsstore/models.py            # FeedConfig, RawItem, make_id()
src/newsstore/ssl_config.py        # get_verify()/make_client() — office|home
src/newsstore/config.py            # load_feeds(yaml) -> list[FeedConfig]
src/newsstore/parser.py            # parse_feed(bytes, feed, fetched_at) -> list[RawItem]
src/newsstore/fetcher.py           # fetch_feed(client, feed, etag, last_modified) -> FetchResult
src/newsstore/store/__init__.py
src/newsstore/store/base.py        # Store Protocol
src/newsstore/store/sqlite_store.py# SqliteStore
src/newsstore/collector.py         # is_due(), collect_once()
src/newsstore/run.py               # CLI entrypoint
tests/conftest.py
tests/fixtures/sample_rss.xml
tests/test_models.py
tests/test_config.py
tests/test_parser.py
tests/test_fetcher.py
tests/test_sqlite_store.py
tests/test_collector.py
infra/Dockerfile                   # office|home conditional cert (modify)
infra/.env.example                 # APP_ENV + NEWSSTORE_DB (modify)
```

Each file has one responsibility: models (data shapes), ssl_config (transport security), config (registry loading), parser (bytes→items), fetcher (HTTP), store (persistence behind an interface), collector (orchestration), run (CLI). Files that change together stay together (e.g., store implementations under `store/`).

**Run everything in Docker.** The repo image is built once; tests and the collector run inside it:
```
docker build -f infra/Dockerfile -t newsstore .
docker run --rm -v ${PWD}:/app newsstore pytest -q          # tests
docker run --rm -v ${PWD}:/app newsstore python -m newsstore.run --force   # one collection pass
```
(On Windows PowerShell use `-v ${PWD}:/app`.)

---

## Task 1: Project scaffolding + green pipeline

**Files:**
- Create: `pyproject.toml`
- Create: `src/newsstore/__init__.py`
- Create: `tests/test_smoke.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_smoke.py
import newsstore

def test_package_imports():
    assert newsstore.__name__ == "newsstore"
```

- [ ] **Step 2: Create pyproject.toml**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "newsstore"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "httpx>=0.27",
    "feedparser>=6.0",
    "beautifulsoup4>=4.12",
    "lxml>=5.2",
    "pydantic>=2.7",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.2"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 3: Create the package marker**

```python
# src/newsstore/__init__.py
```
(empty file)

- [ ] **Step 4: Build image and run test to verify it passes**

Run:
```
docker build -f infra/Dockerfile -t newsstore .
docker run --rm -v ${PWD}:/app newsstore pytest tests/test_smoke.py -q
```
Expected: 1 passed. (If the build fails on the cert COPY, do Task 9 first — but the image already exists from earlier spikes; this should pass.)

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/newsstore/__init__.py tests/test_smoke.py
git commit -m "chore: scaffold newsstore package"
```

---

## Task 2: Data models (`FeedConfig`, `RawItem`, `make_id`)

**Files:**
- Create: `src/newsstore/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
from datetime import datetime, timezone
from newsstore.models import FeedConfig, RawItem, make_id

def test_make_id_is_stable_and_url_based():
    a = make_id("https://x.com/a?utm=1")
    b = make_id("https://x.com/a?utm=1")
    assert a == b and len(a) == 40

def test_make_id_falls_back_to_title_when_no_link():
    assert make_id("", fallback="Some Title") == make_id("", fallback="Some Title")
    assert make_id("", fallback="A") != make_id("", fallback="B")

def test_feedconfig_defaults():
    f = FeedConfig(feed_id="bz_news", url="https://e/x.rss", source="Benzinga")
    assert f.poll_minutes == 60 and f.body_mode == "summary" and f.language == "en"

def test_rawitem_roundtrips():
    now = datetime(2026, 6, 12, tzinfo=timezone.utc)
    it = RawItem(id="abc", feed_id="bz_news", source="Benzinga", url="https://e/a",
                 title="T", body="B", published_at=now, fetched_at=now)
    assert it.id == "abc" and it.published_at == now
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker run --rm -v ${PWD}:/app newsstore pytest tests/test_models.py -q`
Expected: FAIL (ModuleNotFoundError: newsstore.models)

- [ ] **Step 3: Write minimal implementation**

```python
# src/newsstore/models.py
from __future__ import annotations
import hashlib
from datetime import datetime
from pydantic import BaseModel

def make_id(link: str, fallback: str = "") -> str:
    basis = (link or fallback).strip()
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()

class FeedConfig(BaseModel):
    feed_id: str
    url: str
    source: str
    asset_hint: str = ""
    language: str = "en"
    poll_minutes: int = 60
    body_mode: str = "summary"   # full | summary | headline | calendar

class RawItem(BaseModel):
    id: str
    feed_id: str
    source: str
    asset_hint: str = ""
    language: str = "en"
    url: str
    title: str
    body: str = ""
    published_at: datetime | None = None
    fetched_at: datetime
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker run --rm -v ${PWD}:/app newsstore pytest tests/test_models.py -q`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/newsstore/models.py tests/test_models.py
git commit -m "feat: add FeedConfig and RawItem models"
```

---

## Task 3: SSL config (office|home split)

**Files:**
- Create: `src/newsstore/ssl_config.py`
- Test: `tests/test_ssl_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ssl_config.py
import importlib, os
from newsstore import ssl_config

def test_home_uses_default_verify(monkeypatch):
    monkeypatch.setenv("APP_ENV", "home")
    assert ssl_config.get_verify() is True

def test_office_uses_ca_bundle(monkeypatch):
    monkeypatch.setenv("APP_ENV", "office")
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", "/etc/ssl/certs/ca-certificates.crt")
    assert ssl_config.get_verify() == "/etc/ssl/certs/ca-certificates.crt"

def test_make_client_has_browser_ua_and_timeout(monkeypatch):
    monkeypatch.setenv("APP_ENV", "home")
    c = ssl_config.make_client()
    assert "Mozilla" in c.headers["User-Agent"]
    c.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker run --rm -v ${PWD}:/app newsstore pytest tests/test_ssl_config.py -q`
Expected: FAIL (cannot import name ssl_config)

- [ ] **Step 3: Write minimal implementation**

```python
# src/newsstore/ssl_config.py
import os
import httpx

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

def get_verify():
    """office(사내 ePrism) -> CA 번들 경로, home -> 기본 검증(True)."""
    if os.environ.get("APP_ENV", "home").lower() == "office":
        return os.environ.get("REQUESTS_CA_BUNDLE", "/etc/ssl/certs/ca-certificates.crt")
    return True

def make_client(**kwargs) -> httpx.Client:
    kwargs.setdefault("timeout", 90.0)        # 사내 프록시 첫 연결 지연 대비
    kwargs.setdefault("follow_redirects", True)
    headers = {"User-Agent": _UA}
    headers.update(kwargs.pop("headers", {}))
    return httpx.Client(verify=get_verify(), headers=headers, **kwargs)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker run --rm -v ${PWD}:/app newsstore pytest tests/test_ssl_config.py -q`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/newsstore/ssl_config.py tests/test_ssl_config.py
git commit -m "feat: office|home SSL verify + httpx client factory"
```

---

## Task 4: Feed registry loader

**Files:**
- Create: `src/newsstore/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
from newsstore.config import load_feeds

def test_load_feeds(tmp_path):
    p = tmp_path / "feeds.yaml"
    p.write_text(
        "feeds:\n"
        "  - feed_id: bz_news\n"
        "    url: https://www.benzinga.com/news/feed\n"
        "    source: Benzinga\n"
        "    asset_hint: us_stock\n"
        "    poll_minutes: 5\n"
        "    body_mode: summary\n",
        encoding="utf-8",
    )
    feeds = load_feeds(p)
    assert len(feeds) == 1
    assert feeds[0].feed_id == "bz_news" and feeds[0].poll_minutes == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker run --rm -v ${PWD}:/app newsstore pytest tests/test_config.py -q`
Expected: FAIL (No module named newsstore.config)

- [ ] **Step 3: Write minimal implementation**

```python
# src/newsstore/config.py
from pathlib import Path
import yaml
from .models import FeedConfig

def load_feeds(path) -> list[FeedConfig]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return [FeedConfig(**entry) for entry in data["feeds"]]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker run --rm -v ${PWD}:/app newsstore pytest tests/test_config.py -q`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add src/newsstore/config.py tests/test_config.py
git commit -m "feat: YAML feed-registry loader"
```

---

## Task 5: Parser (RSS bytes -> RawItem list)

**Files:**
- Create: `src/newsstore/parser.py`
- Create: `tests/fixtures/sample_rss.xml`
- Test: `tests/test_parser.py`

- [ ] **Step 1: Create the fixture**

```xml
<!-- tests/fixtures/sample_rss.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>Sample</title>
  <item>
    <title>Banks Curb Hedge Fund Bets on SK Hynix</title>
    <link>https://example.com/a</link>
    <description><![CDATA[<p>Global banks are <b>curbing</b> leveraged bets.</p>]]></description>
    <pubDate>Fri, 12 Jun 2026 06:41:00 GMT</pubDate>
  </item>
  <item>
    <title>No Link Item</title>
    <description>plain text body</description>
    <pubDate>Fri, 12 Jun 2026 05:00:00 GMT</pubDate>
  </item>
</channel></rss>
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_parser.py
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `docker run --rm -v ${PWD}:/app newsstore pytest tests/test_parser.py -q`
Expected: FAIL (No module named newsstore.parser)

- [ ] **Step 4: Write minimal implementation**

```python
# src/newsstore/parser.py
from __future__ import annotations
import time
from datetime import datetime, timezone
import feedparser
from bs4 import BeautifulSoup
from .models import FeedConfig, RawItem, make_id

def _clean(html: str) -> str:
    text = BeautifulSoup(html or "", "lxml").get_text(" ", strip=True)
    return " ".join(text.split())

def _published(entry) -> datetime | None:
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    if not t:
        return None
    return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc)

def parse_feed(raw: bytes, feed: FeedConfig, fetched_at: datetime) -> list[RawItem]:
    fp = feedparser.parse(raw)
    items: list[RawItem] = []
    for e in fp.entries:
        link = (e.get("link") or "").strip()
        title = (e.get("title") or "").strip()
        body_html = e["content"][0]["value"] if e.get("content") else e.get("summary", "")
        items.append(RawItem(
            id=make_id(link, fallback=title),
            feed_id=feed.feed_id, source=feed.source, asset_hint=feed.asset_hint,
            language=feed.language, url=link, title=title,
            body=_clean(body_html), published_at=_published(e), fetched_at=fetched_at,
        ))
    return items
```

- [ ] **Step 5: Run test to verify it passes**

Run: `docker run --rm -v ${PWD}:/app newsstore pytest tests/test_parser.py -q`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add src/newsstore/parser.py tests/test_parser.py tests/fixtures/sample_rss.xml
git commit -m "feat: RSS parser to normalized RawItem"
```

---

## Task 6: Store interface + SQLite implementation

**Files:**
- Create: `src/newsstore/store/__init__.py` (empty)
- Create: `src/newsstore/store/base.py`
- Create: `src/newsstore/store/sqlite_store.py`
- Test: `tests/test_sqlite_store.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sqlite_store.py
from datetime import datetime, timezone
from newsstore.models import RawItem
from newsstore.store.sqlite_store import SqliteStore

NOW = datetime(2026, 6, 12, 7, 0, tzinfo=timezone.utc)

def _item(i):
    return RawItem(id=i, feed_id="f1", source="S", url=f"https://e/{i}",
                   title=f"t{i}", body="b", fetched_at=NOW)

def test_upsert_dedups_by_id(tmp_path):
    s = SqliteStore(tmp_path / "db.sqlite")
    assert s.upsert_items([_item("a"), _item("b")]) == 2
    assert s.upsert_items([_item("a"), _item("c")]) == 1   # only "c" is new
    assert s.count() == 3

def test_feed_state_roundtrip(tmp_path):
    s = SqliteStore(tmp_path / "db.sqlite")
    assert s.get_feed_state("f1") == {}
    s.set_feed_state("f1", etag="W/\"x\"", last_modified="Mon", last_fetched=NOW)
    st = s.get_feed_state("f1")
    assert st["etag"] == "W/\"x\"" and st["last_fetched"] == NOW
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker run --rm -v ${PWD}:/app newsstore pytest tests/test_sqlite_store.py -q`
Expected: FAIL (No module named newsstore.store.sqlite_store)

- [ ] **Step 3: Write the Store protocol**

```python
# src/newsstore/store/base.py
from __future__ import annotations
from typing import Protocol
from ..models import RawItem

class Store(Protocol):
    def upsert_items(self, items: list[RawItem]) -> int:
        """Insert items, skipping ids already present. Returns count of NEW items."""
        ...
    def get_feed_state(self, feed_id: str) -> dict:
        """Return {} or {'etag','last_modified','last_fetched'(datetime)}."""
        ...
    def set_feed_state(self, feed_id: str, **fields) -> None: ...
    def count(self) -> int: ...
```

- [ ] **Step 4: Write the SQLite implementation**

```python
# src/newsstore/store/sqlite_store.py
from __future__ import annotations
import sqlite3
from datetime import datetime
from ..models import RawItem

_SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_items (
  id TEXT PRIMARY KEY, feed_id TEXT, source TEXT, asset_hint TEXT, language TEXT,
  url TEXT, title TEXT, body TEXT, published_at TEXT, fetched_at TEXT
);
CREATE TABLE IF NOT EXISTS feed_state (
  feed_id TEXT PRIMARY KEY, etag TEXT, last_modified TEXT, last_fetched TEXT
);
"""

class SqliteStore:
    def __init__(self, path):
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)

    def upsert_items(self, items: list[RawItem]) -> int:
        new = 0
        for it in items:
            cur = self.conn.execute(
                "INSERT OR IGNORE INTO raw_items "
                "(id,feed_id,source,asset_hint,language,url,title,body,published_at,fetched_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (it.id, it.feed_id, it.source, it.asset_hint, it.language, it.url, it.title,
                 it.body,
                 it.published_at.isoformat() if it.published_at else None,
                 it.fetched_at.isoformat()),
            )
            new += cur.rowcount
        self.conn.commit()
        return new

    def get_feed_state(self, feed_id: str) -> dict:
        row = self.conn.execute(
            "SELECT etag,last_modified,last_fetched FROM feed_state WHERE feed_id=?",
            (feed_id,)).fetchone()
        if not row:
            return {}
        return {
            "etag": row["etag"],
            "last_modified": row["last_modified"],
            "last_fetched": datetime.fromisoformat(row["last_fetched"]) if row["last_fetched"] else None,
        }

    def set_feed_state(self, feed_id: str, **fields) -> None:
        cur = self.get_feed_state(feed_id)
        etag = fields.get("etag", cur.get("etag"))
        last_modified = fields.get("last_modified", cur.get("last_modified"))
        lf = fields.get("last_fetched", cur.get("last_fetched"))
        lf_s = lf.isoformat() if isinstance(lf, datetime) else lf
        self.conn.execute(
            "INSERT INTO feed_state (feed_id,etag,last_modified,last_fetched) VALUES (?,?,?,?) "
            "ON CONFLICT(feed_id) DO UPDATE SET etag=excluded.etag,"
            "last_modified=excluded.last_modified,last_fetched=excluded.last_fetched",
            (feed_id, etag, last_modified, lf_s))
        self.conn.commit()

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM raw_items").fetchone()[0]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `docker run --rm -v ${PWD}:/app newsstore pytest tests/test_sqlite_store.py -q`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add src/newsstore/store/
git add tests/test_sqlite_store.py
git commit -m "feat: Store protocol + SQLite raw store with id dedup and feed state"
```

---

## Task 7: Fetcher (conditional GET)

**Files:**
- Create: `src/newsstore/fetcher.py`
- Test: `tests/test_fetcher.py`

- [ ] **Step 1: Write the failing test** (uses httpx.MockTransport — no network)

```python
# tests/test_fetcher.py
import httpx
from newsstore.models import FeedConfig
from newsstore.fetcher import fetch_feed

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker run --rm -v ${PWD}:/app newsstore pytest tests/test_fetcher.py -q`
Expected: FAIL (No module named newsstore.fetcher)

- [ ] **Step 3: Write minimal implementation**

```python
# src/newsstore/fetcher.py
from __future__ import annotations
from dataclasses import dataclass
import httpx
from .models import FeedConfig

@dataclass
class FetchResult:
    status: int
    content: bytes
    etag: str | None
    last_modified: str | None

def fetch_feed(client: httpx.Client, feed: FeedConfig,
               etag: str | None = None, last_modified: str | None = None) -> FetchResult:
    headers = {}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    try:
        r = client.get(feed.url, headers=headers)
    except httpx.HTTPError:
        return FetchResult(status=-1, content=b"", etag=None, last_modified=None)
    content = b"" if r.status_code == 304 else r.content
    return FetchResult(status=r.status_code, content=content,
                       etag=r.headers.get("ETag"), last_modified=r.headers.get("Last-Modified"))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker run --rm -v ${PWD}:/app newsstore pytest tests/test_fetcher.py -q`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/newsstore/fetcher.py tests/test_fetcher.py
git commit -m "feat: conditional-GET feed fetcher"
```

---

## Task 8: Collector orchestration

**Files:**
- Create: `src/newsstore/collector.py`
- Test: `tests/test_collector.py`

- [ ] **Step 1: Write the failing test** (fake client via MockTransport + real SqliteStore)

```python
# tests/test_collector.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker run --rm -v ${PWD}:/app newsstore pytest tests/test_collector.py -q`
Expected: FAIL (No module named newsstore.collector)

- [ ] **Step 3: Write minimal implementation**

```python
# src/newsstore/collector.py
from __future__ import annotations
from datetime import datetime, timezone, timedelta
import httpx
from .models import FeedConfig
from .store.base import Store
from .fetcher import fetch_feed
from .parser import parse_feed

def is_due(state: dict, poll_minutes: int, now: datetime) -> bool:
    last = state.get("last_fetched")
    if not last:
        return True
    return (now - last) >= timedelta(minutes=poll_minutes)

def collect_once(client: httpx.Client, store: Store, feeds: list[FeedConfig],
                 now: datetime | None = None, force: bool = False) -> dict:
    now = now or datetime.now(timezone.utc)
    summary: dict[str, int] = {}
    for feed in feeds:
        state = store.get_feed_state(feed.feed_id)
        if not force and not is_due(state, feed.poll_minutes, now):
            continue
        res = fetch_feed(client, feed, state.get("etag"), state.get("last_modified"))
        if res.status == 304:
            store.set_feed_state(feed.feed_id, last_fetched=now)
            summary[feed.feed_id] = 0
            continue
        if res.status != 200:
            summary[feed.feed_id] = -1     # transient failure; retried next pass
            continue
        items = parse_feed(res.content, feed, fetched_at=now)
        new = store.upsert_items(items)
        store.set_feed_state(feed.feed_id, etag=res.etag,
                             last_modified=res.last_modified, last_fetched=now)
        summary[feed.feed_id] = new
    return summary
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker run --rm -v ${PWD}:/app newsstore pytest tests/test_collector.py -q`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/newsstore/collector.py tests/test_collector.py
git commit -m "feat: collector orchestration with due-check and conditional GET"
```

---

## Task 9: CLI runner + Dockerfile office|home cert

**Files:**
- Create: `src/newsstore/run.py`
- Modify: `infra/Dockerfile`
- Modify: `infra/.env.example`

- [ ] **Step 1: Write the runner**

```python
# src/newsstore/run.py
from __future__ import annotations
import argparse
import os
from .config import load_feeds
from .ssl_config import make_client
from .store.sqlite_store import SqliteStore
from .collector import collect_once

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="newsstore collector (one pass)")
    ap.add_argument("--feeds", default="config/feeds.yaml")
    ap.add_argument("--db", default=os.environ.get("NEWSSTORE_DB", "data/newsstore.db"))
    ap.add_argument("--force", action="store_true", help="ignore poll intervals (fetch all)")
    args = ap.parse_args(argv)

    os.makedirs(os.path.dirname(args.db) or ".", exist_ok=True)
    feeds = load_feeds(args.feeds)
    store = SqliteStore(args.db)
    client = make_client()
    try:
        summary = collect_once(client, store, feeds, force=args.force)
    finally:
        client.close()

    total_new = sum(v for v in summary.values() if v > 0)
    failed = [k for k, v in summary.items() if v == -1]
    print(f"collected {total_new} new item(s); store total = {store.count()}")
    for fid, n in sorted(summary.items()):
        print(f"  {fid}: {'FAIL' if n == -1 else n}")
    if failed:
        print(f"failed feeds: {', '.join(failed)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Replace `infra/Dockerfile` with office|home conditional cert**

```dockerfile
# infra/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# 의존성 먼저 (캐시)
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install -e ".[dev]"

# 소스
COPY . .

# APP_ENV=office(사내 ePrism)면 루트 CA 설치, home이면 파일이 없어 스킵 → 동일 이미지로 양쪽 빌드.
# (.crt 는 .gitignore/.dockerignore로 git 제외; office 로컬에는 파일이 존재해 COPY . . 로 포함됨)
RUN if [ -f ePrism-SSL-ROOT-CA.crt ]; then \
      cp ePrism-SSL-ROOT-CA.crt /usr/local/share/ca-certificates/ && update-ca-certificates ; \
    fi
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    PYTHONUNBUFFERED=1

CMD ["python", "-m", "newsstore.run", "--force"]
```

- [ ] **Step 3: Replace `infra/.env.example`**

```bash
# infra/.env.example  → 복사해서 .env 로 쓰고 값 채우기 (.env는 git 제외)
# 실행 환경: office(사내망/ePrism 프록시) | home(집)
APP_ENV=office
# 수집 DB 경로 (컨테이너 내). 볼륨 마운트해서 영속화 권장.
NEWSSTORE_DB=data/newsstore.db
```

- [ ] **Step 4: Rebuild and run the collector end-to-end (real feeds)**

Run:
```
docker build -f infra/Dockerfile -t newsstore .
docker run --rm -e APP_ENV=office -v ${PWD}:/app newsstore python -m newsstore.run --force
```
Expected: prints `collected N new item(s); store total = N` with per-feed counts > 0 for live feeds (e.g. `bz_news`, `infomax_bond_fx`, `bbg_markets`). A `data/newsstore.db` file appears.

- [ ] **Step 5: Verify persistence + dedup across runs**

Run the same command again:
```
docker run --rm -e APP_ENV=office -v ${PWD}:/app newsstore python -m newsstore.run --force
```
Expected: second run shows mostly `0` new (already stored) — proving dedup. `store total` grows only by genuinely new items.

- [ ] **Step 6: Commit**

```bash
git add src/newsstore/run.py infra/Dockerfile infra/.env.example
git commit -m "feat: CLI runner + office|home conditional-cert Dockerfile"
```

---

## Task 10: Populate the feed registry

**Files:**
- Create: `config/feeds.yaml`
- Test: `tests/test_registry_valid.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_registry_valid.py
from newsstore.config import load_feeds

def test_registry_loads_and_is_unique():
    feeds = load_feeds("config/feeds.yaml")
    assert len(feeds) >= 20
    ids = [f.feed_id for f in feeds]
    assert len(ids) == len(set(ids)), "duplicate feed_id"
    for f in feeds:
        assert f.url.startswith("http")
        assert f.body_mode in {"full", "summary", "headline", "calendar"}
        assert f.poll_minutes >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker run --rm -v ${PWD}:/app newsstore pytest tests/test_registry_valid.py -q`
Expected: FAIL (FileNotFoundError config/feeds.yaml)

- [ ] **Step 3: Create the registry** (verified sources from spec; all free, confirmed reachable from KR IP)

```yaml
# config/feeds.yaml — verified 2026-06-12 (KR IP, Docker)
feeds:
  # ── 한국 (연합인포맥스 = 연합뉴스 금융단말 자회사) ──
  - {feed_id: infomax_bond_fx,  url: "https://news.einfomax.co.kr/rss/S1N16.xml", source: 인포맥스, asset_hint: "kr_bond,kr_fx", language: ko, poll_minutes: 60, body_mode: summary}
  - {feed_id: infomax_stock,    url: "https://news.einfomax.co.kr/rss/S1N2.xml",  source: 인포맥스, asset_hint: kr_stock, language: ko, poll_minutes: 60, body_mode: summary}
  - {feed_id: infomax_overseas, url: "https://news.einfomax.co.kr/rss/S1N21.xml", source: 인포맥스, asset_hint: us_stock, language: ko, poll_minutes: 60, body_mode: summary}
  - {feed_id: infomax_intl,     url: "https://news.einfomax.co.kr/rss/S1N23.xml", source: 인포맥스, asset_hint: macro, language: ko, poll_minutes: 60, body_mode: summary}
  - {feed_id: infomax_policy,   url: "https://news.einfomax.co.kr/rss/S1N15.xml", source: 인포맥스, asset_hint: kr_macro, language: ko, poll_minutes: 60, body_mode: summary}
  # ── 한국 독립 경제지 (연합 계열 밖) ──
  - {feed_id: hankyung,   url: "https://www.hankyung.com/feed/finance",  source: 한국경제, asset_hint: kr_market, language: ko, poll_minutes: 30, body_mode: summary}
  - {feed_id: mk_stock,   url: "https://www.mk.co.kr/rss/50200011/",     source: 매일경제, asset_hint: kr_stock, language: ko, poll_minutes: 30, body_mode: summary}
  # ── 미국 주식/크립토/원자재 (Benzinga: /feed 열림, 요약 풍부) ──
  - {feed_id: bz_news,     url: "https://www.benzinga.com/news/feed",                   source: Benzinga, asset_hint: us_stock, poll_minutes: 5,  body_mode: summary}
  - {feed_id: bz_markets,  url: "https://www.benzinga.com/markets/feed",                source: Benzinga, asset_hint: us_market, poll_minutes: 5,  body_mode: summary}
  - {feed_id: bz_movers,   url: "https://www.benzinga.com/movers/feed",                 source: Benzinga, asset_hint: us_stock, poll_minutes: 5,  body_mode: summary}
  - {feed_id: bz_crypto,   url: "https://www.benzinga.com/markets/cryptocurrency/feed", source: Benzinga, asset_hint: crypto, poll_minutes: 60, body_mode: summary}
  - {feed_id: bz_commod,   url: "https://www.benzinga.com/markets/commodities/feed",    source: Benzinga, asset_hint: commodity, poll_minutes: 60, body_mode: summary}
  # ── 크립토 전용 ──
  - {feed_id: coindesk,      url: "https://www.coindesk.com/arc/outboundfeeds/rss/", source: CoinDesk, asset_hint: crypto, poll_minutes: 60, body_mode: summary}
  - {feed_id: cointelegraph, url: "https://cointelegraph.com/rss",                   source: Cointelegraph, asset_hint: crypto, poll_minutes: 60, body_mode: summary}
  # ── FX / 금리·중앙은행 ──
  - {feed_id: forexlive,    url: "https://www.forexlive.com/feed/news",       source: ForexLive, asset_hint: fx, poll_minutes: 60, body_mode: full}
  - {feed_id: forexlive_cb, url: "https://www.forexlive.com/feed/centralbank", source: ForexLive, asset_hint: "rates,central_bank", poll_minutes: 60, body_mode: full}
  - {feed_id: fxstreet,     url: "https://www.fxstreet.com/rss/news",          source: FXStreet, asset_hint: fx, poll_minutes: 30, body_mode: summary}
  - {feed_id: investing_fx, url: "https://www.investing.com/rss/news_1.rss",   source: Investing, asset_hint: fx, poll_minutes: 60, body_mode: summary}
  # ── 채권/매크로/정책 ──
  - {feed_id: fed,           url: "https://www.federalreserve.gov/feeds/press_all.xml", source: Fed, asset_hint: us_policy, poll_minutes: 60, body_mode: summary}
  - {feed_id: ecb,           url: "https://www.ecb.europa.eu/rss/press.html",            source: ECB, asset_hint: eu_policy, poll_minutes: 60, body_mode: summary}
  - {feed_id: investing_bond, url: "https://www.investing.com/rss/bonds.rss",            source: Investing, asset_hint: us_bond, poll_minutes: 60, body_mode: summary}
  # ── Bloomberg 퍼스트파티 RSS (feed 엔드포인트 열림, 원본 스쿱 포착) ──
  - {feed_id: bbg_markets,    url: "https://feeds.bloomberg.com/markets/news.rss",    source: Bloomberg, asset_hint: global_market, poll_minutes: 15, body_mode: headline}
  - {feed_id: bbg_technology, url: "https://feeds.bloomberg.com/technology/news.rss", source: Bloomberg, asset_hint: tech, poll_minutes: 15, body_mode: headline}
  - {feed_id: bbg_economics,  url: "https://feeds.bloomberg.com/economics/news.rss",  source: Bloomberg, asset_hint: macro, poll_minutes: 15, body_mode: headline}
  - {feed_id: bbg_korea,      url: "https://flipboard.com/@bloomberg/korea-gaa61f1tz.rss", source: Bloomberg, asset_hint: kr_market, poll_minutes: 15, body_mode: summary}
  # ── 매크로/루머 헤드라인 (Google News 쿼리; 본문 없음) ──
  - {feed_id: gn_macro_reuters, url: "https://news.google.com/rss/search?q=site:reuters.com+(inflation+OR+economy+OR+Fed)+when:12h&hl=en-US&gl=US&ceid=US:en", source: GoogleNews, asset_hint: macro, poll_minutes: 30, body_mode: headline}
  - {feed_id: gn_rumor,         url: "https://news.google.com/rss/search?q=(reportedly+OR+%22in+talks%22+OR+%22sources+say%22)+(stock+OR+merger+OR+acquisition+OR+raise)+when:12h&hl=en-US&gl=US&ceid=US:en", source: GoogleNews, asset_hint: rumor, poll_minutes: 30, body_mode: headline}
  - {feed_id: gn_kr_chips,      url: "https://news.google.com/rss/search?q=(%22SK+Hynix%22+OR+Samsung)+(hedge+fund+OR+leverage+OR+chip)+when:12h&hl=en-US&gl=US&ceid=US:en", source: GoogleNews, asset_hint: kr_stock, poll_minutes: 30, body_mode: headline}
  # ── 특수: 트럼프 원문 / Axios ──
  - {feed_id: trump_truth, url: "https://trumpstruth.org/feed",        source: TruthSocial, asset_hint: "trump,policy", poll_minutes: 15, body_mode: full}
  - {feed_id: axios,       url: "https://www.axios.com/feeds/feed.rss", source: Axios, asset_hint: "policy,scoop", poll_minutes: 60, body_mode: summary}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker run --rm -v ${PWD}:/app newsstore pytest tests/test_registry_valid.py -q`
Expected: 1 passed.

- [ ] **Step 5: Run the full collector against the real registry**

Run: `docker run --rm -e APP_ENV=office -v ${PWD}:/app newsstore python -m newsstore.run --force`
Expected: most feeds report > 0 new items; note any feed printing `FAIL` for follow-up (URL drift). Confirm `bbg_korea` / `gn_kr_chips` appear (the SK Hynix-scoop catchers).

- [ ] **Step 6: Commit**

```bash
git add config/feeds.yaml tests/test_registry_valid.py
git commit -m "feat: populate verified feed registry"
```

---

## Task 11: Full test sweep + README note

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Run the entire suite**

Run: `docker run --rm -v ${PWD}:/app newsstore pytest -q`
Expected: all tests pass (models, ssl, config, parser, sqlite_store, fetcher, collector, registry, smoke).

- [ ] **Step 2: Write README usage section**

```markdown
## newsstore collector (Step 1)

Polls free RSS feeds (`config/feeds.yaml`) and stores deduplicated raw items in SQLite. No LLM (that is Step 2).

### Run (Docker only — host has no Python)
```
docker build -f infra/Dockerfile -t newsstore .
# one collection pass (office = behind corporate ePrism proxy)
docker run --rm -e APP_ENV=office -v ${PWD}:/app newsstore python -m newsstore.run --force
# tests
docker run --rm -v ${PWD}:/app newsstore pytest -q
```
`APP_ENV=home` skips the ePrism cert. Data persists in `data/newsstore.db` (volume-mounted).
Scheduling (every 5 min) is external (Cloud Scheduler / cron) — the runner does one pass per invocation.
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: collector usage"
```

---

## Out of Scope (Step 2 / later)
- Gemini importance tagging + card/body split into `news`/`news_body` (Step 2 plan).
- Firestore store implementation (drop-in `Store` behind the same protocol; swap `SqliteStore` in `run.py`).
- TradingView economic-calendar connector (non-RSS; `body_mode: calendar`).
- Near-duplicate clustering across publishers (belongs in the Step 2 processor).
- Cloud Run / Cloud Scheduler deployment + GCP egress-IP verification for einfomax.
