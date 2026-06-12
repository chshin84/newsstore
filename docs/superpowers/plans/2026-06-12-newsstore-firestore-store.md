# FirestoreStore Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Firestore-backed implementation of the existing `Store` Protocol and an env-driven switch (`NEWSSTORE_BACKEND=sqlite|firestore`, default `sqlite`), so the collector can write to either backend from one codebase.

**Architecture:** `FirestoreStore` mirrors `SqliteStore`'s 7-method `Store` Protocol. It takes an injected Firestore client (real `google.cloud.firestore.Client` in production, in-memory `MockFirestore` in tests). Dedup uses read-then-create so re-seen items never overwrite `processed`/`tags`. A `make_store()` factory selects the backend by env var; `run.py` calls the factory. SQLite stays the default for local/Docker tests.

**Tech Stack:** Python 3.12, `google-cloud-firestore` (prod, `[gcp]` extra, lazy-imported), `mock-firestore` (tests, `[dev]` extra), pytest, Docker.

**Scope note:** This plan is ONLY the storage backend + switch. Containerizing for Cloud Run, Cloud Scheduler, security rules/indexes, and the website are a separate plan (`*-gcp-deploy.md`, written next). Spec: `docs/superpowers/specs/2026-06-12-newsstore-gcp-deploy-design.md`.

**Spec deviation (intentional):** Spec §3 said dedup via `create()`/`AlreadyExists`. This plan uses read-then-`set` (get-exists → skip, else write) instead — functionally identical for a single-writer 5-min collector, and testable against `mock-firestore` without depending on its `create()`/exception behavior. No `merge=` is used anywhere (full-doc writes) for maximum mock compatibility.

---

## File Structure

- **Create** `src/newsstore/store/firestore_store.py` — `FirestoreStore` + doc⇄RawItem mappers. NO top-level `google` import (client is injected).
- **Create** `src/newsstore/store/factory.py` — `make_store()` backend selector (lazy-imports google only on the firestore branch).
- **Modify** `src/newsstore/run.py` — build the store via `make_store()` instead of hard-coding `SqliteStore`.
- **Modify** `pyproject.toml` — add `[gcp]` extra (`google-cloud-firestore`) and `mock-firestore` to `[dev]`.
- **Modify** `infra/requirements.lock` — regenerate after deps change.
- **Modify** `README.md` — document `NEWSSTORE_BACKEND`.
- **Create** `tests/test_firestore_store.py` — FirestoreStore behavior (MockFirestore).
- **Create** `tests/test_store_factory.py` — factory selection.
- **Modify** `tests/test_run.py` — run.py uses the factory.

**Test loop (Docker, host has no Python).** Build once per dependency change; iterate by bind-mounting source so edits apply without rebuilds (deps live in the image, not `/app`):

```
docker build -f infra/Dockerfile -t newsstore .
docker run --rm -v "${PWD}:/app" newsstore pytest -q
```

---

## Task 1: Add dependencies

**Files:**
- Modify: `pyproject.toml:9-19`
- Modify: `infra/requirements.lock`

- [ ] **Step 1: Add the `[gcp]` extra and `mock-firestore` dev dep**

In `pyproject.toml`, replace the `[project.optional-dependencies]` block:

```toml
[project.optional-dependencies]
dev = ["pytest>=8.2", "mock-firestore>=0.11.0"]
gcp = ["google-cloud-firestore>=2.16"]
```

- [ ] **Step 2: Rebuild the image so `mock-firestore` is installed**

Run: `docker build -f infra/Dockerfile -t newsstore .`
Expected: build succeeds; `mock-firestore` resolves (the `-c infra/requirements.lock` constraints file does not block new packages).

- [ ] **Step 3: Verify the test dep imports**

Run: `docker run --rm newsstore python -c "import mockfirestore; print('ok')"`
Expected: prints `ok`. (PyPI package `mock-firestore` imports as `mockfirestore`.)

- [ ] **Step 4: Regenerate the lock and pin the new packages**

Run: `docker run --rm newsstore pip freeze | grep -v "^-e " > infra/requirements.lock`
Expected: `infra/requirements.lock` now contains `mock-firestore==…` (and its deps). `google-cloud-firestore` is NOT present (the `[gcp]` extra isn't installed in the dev image — correct).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml infra/requirements.lock
git commit -m "build: add mock-firestore (dev) and google-cloud-firestore ([gcp] extra)"
```

---

## Task 2: FirestoreStore — constructor, upsert/dedup, count, context manager

**Files:**
- Create: `src/newsstore/store/firestore_store.py`
- Test: `tests/test_firestore_store.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_firestore_store.py`:

```python
from datetime import datetime, timezone
from mockfirestore import MockFirestore
from newsstore.models import RawItem
from newsstore.store.firestore_store import FirestoreStore

NOW = datetime(2026, 6, 12, 7, 0, tzinfo=timezone.utc)

def _item(i):
    return RawItem(id=i, feed_id="f1", source="S", url=f"https://e/{i}",
                   title=f"t{i}", body="b", fetched_at=NOW)

def _store():
    return FirestoreStore(MockFirestore())

def test_upsert_dedups_by_id():
    s = _store()
    assert s.upsert_items([_item("a"), _item("b")]) == 2
    assert s.upsert_items([_item("a"), _item("c")]) == 1   # only "c" is new
    assert s.count() == 3

def test_context_manager_yields_store():
    with _store() as s:
        assert s.upsert_items([_item("a")]) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker run --rm -v "${PWD}:/app" newsstore pytest -q tests/test_firestore_store.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'newsstore.store.firestore_store'`.

- [ ] **Step 3: Create the module with constructor, mappers, upsert, count, context manager**

Create `src/newsstore/store/firestore_store.py`:

```python
from __future__ import annotations
from datetime import datetime, timezone
from ..models import RawItem

_ITEMS = "items"
_FEED_STATE = "feed_state"


def _to_doc(item: RawItem) -> dict:
    return {
        "feed_id": item.feed_id, "source": item.source,
        "asset_hint": item.asset_hint, "language": item.language,
        "url": item.url, "title": item.title, "body": item.body,
        "published_at": item.published_at, "fetched_at": item.fetched_at,
        "processed": False, "processed_at": None, "tags": [],
    }


def _from_doc(doc_id: str, d: dict) -> RawItem:
    return RawItem(
        id=doc_id, feed_id=d.get("feed_id", ""), source=d.get("source", ""),
        asset_hint=d.get("asset_hint") or "", language=d.get("language") or "en",
        url=d.get("url", ""), title=d.get("title", ""), body=d.get("body") or "",
        published_at=d.get("published_at"), fetched_at=d.get("fetched_at"),
    )


class FirestoreStore:
    """Store Protocol over Firestore. Client is injected (real Client in prod,
    MockFirestore in tests) so the class has no hard google dependency."""

    def __init__(self, client):
        self.db = client

    def upsert_items(self, items: list[RawItem]) -> int:
        new = 0
        col = self.db.collection(_ITEMS)
        for it in items:
            ref = col.document(it.id)
            if ref.get().exists:          # already stored -> never overwrite
                continue
            ref.set(_to_doc(it))
            new += 1
        return new

    def count(self) -> int:
        return sum(1 for _ in self.db.collection(_ITEMS).stream())

    def close(self) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        self.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker run --rm -v "${PWD}:/app" newsstore pytest -q tests/test_firestore_store.py`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/newsstore/store/firestore_store.py tests/test_firestore_store.py
git commit -m "feat: FirestoreStore upsert/dedup/count over injected client"
```

---

## Task 3: FirestoreStore — feed_state roundtrip

**Files:**
- Modify: `src/newsstore/store/firestore_store.py`
- Test: `tests/test_firestore_store.py`

- [ ] **Step 1: Add the failing test**

Append to `tests/test_firestore_store.py`:

```python
def test_feed_state_roundtrip():
    s = _store()
    assert s.get_feed_state("f1") == {}
    s.set_feed_state("f1", etag='W/"x"', last_modified="Mon", last_fetched=NOW)
    st = s.get_feed_state("f1")
    assert st["etag"] == 'W/"x"' and st["last_fetched"] == NOW

def test_set_feed_state_merges_existing_fields():
    s = _store()
    s.set_feed_state("f1", etag="e1", last_fetched=NOW)
    s.set_feed_state("f1", last_modified="Tue")   # must not wipe etag
    st = s.get_feed_state("f1")
    assert st["etag"] == "e1" and st["last_modified"] == "Tue"
```

- [ ] **Step 2: Run to verify it fails**

Run: `docker run --rm -v "${PWD}:/app" newsstore pytest -q tests/test_firestore_store.py::test_feed_state_roundtrip`
Expected: FAIL — `AttributeError: 'FirestoreStore' object has no attribute 'get_feed_state'`.

- [ ] **Step 3: Add feed_state methods**

Add these methods to `FirestoreStore` (after `count`):

```python
    def get_feed_state(self, feed_id: str) -> dict:
        snap = self.db.collection(_FEED_STATE).document(feed_id).get()
        if not snap.exists:
            return {}
        d = snap.to_dict()
        return {"etag": d.get("etag"), "last_modified": d.get("last_modified"),
                "last_fetched": d.get("last_fetched")}

    def set_feed_state(self, feed_id: str, **fields) -> None:
        cur = self.get_feed_state(feed_id)        # read-modify-write (no merge=)
        cur.update(fields)
        self.db.collection(_FEED_STATE).document(feed_id).set({
            "etag": cur.get("etag"),
            "last_modified": cur.get("last_modified"),
            "last_fetched": cur.get("last_fetched"),
        })
```

- [ ] **Step 4: Run to verify pass**

Run: `docker run --rm -v "${PWD}:/app" newsstore pytest -q tests/test_firestore_store.py`
Expected: PASS (all tests so far).

- [ ] **Step 5: Commit**

```bash
git add src/newsstore/store/firestore_store.py tests/test_firestore_store.py
git commit -m "feat: FirestoreStore feed_state roundtrip"
```

---

## Task 4: FirestoreStore — get_unprocessed, mark_processed, preserve-on-resee

**Files:**
- Modify: `src/newsstore/store/firestore_store.py`
- Test: `tests/test_firestore_store.py`

- [ ] **Step 1: Add the failing tests**

Append to `tests/test_firestore_store.py`:

```python
def test_get_unprocessed_and_mark_processed():
    s = _store()
    s.upsert_items([_item("a"), _item("b"), _item("c")])
    assert {i.id for i in s.get_unprocessed()} == {"a", "b", "c"}
    assert len(s.get_unprocessed(limit=2)) == 2
    one = s.get_unprocessed(limit=1)[0]                 # round-trips to a RawItem
    assert one.fetched_at == NOW and one.feed_id == "f1"
    assert s.mark_processed(["a", "b"], processed_at=NOW) == 2
    assert {i.id for i in s.get_unprocessed()} == {"c"}
    assert s.mark_processed(["a", "b"]) == 0            # idempotent
    assert s.mark_processed([]) == 0

def test_upsert_preserves_processed_on_resee():
    s = _store()
    s.upsert_items([_item("a")])
    assert s.mark_processed(["a"], processed_at=NOW) == 1
    assert s.upsert_items([_item("a")]) == 0            # re-seen, not re-written
    assert s.get_unprocessed() == []                    # still processed
```

- [ ] **Step 2: Run to verify it fails**

Run: `docker run --rm -v "${PWD}:/app" newsstore pytest -q tests/test_firestore_store.py::test_get_unprocessed_and_mark_processed`
Expected: FAIL — `AttributeError: 'FirestoreStore' object has no attribute 'get_unprocessed'`.

- [ ] **Step 3: Add the queue methods**

Add to `FirestoreStore` (after `set_feed_state`):

```python
    def get_unprocessed(self, limit: int | None = None) -> list[RawItem]:
        # processed==False + order_by(fetched_at) needs a composite index in
        # real Firestore (created in the deploy plan); MockFirestore needs none.
        q = (self.db.collection(_ITEMS)
             .where("processed", "==", False)
             .order_by("fetched_at"))
        if limit is not None:
            q = q.limit(int(limit))
        return [_from_doc(s.id, s.to_dict()) for s in q.stream()]

    def mark_processed(self, ids: list[str], processed_at: datetime | None = None) -> int:
        if not ids:
            return 0
        ts = processed_at or datetime.now(timezone.utc)
        changed = 0
        col = self.db.collection(_ITEMS)
        for _id in ids:
            ref = col.document(_id)
            snap = ref.get()
            if snap.exists:
                d = snap.to_dict()
                if d.get("processed") is False:
                    d["processed"] = True
                    d["processed_at"] = ts
                    ref.set(d)              # full-doc write, no merge=
                    changed += 1
        return changed
```

- [ ] **Step 4: Run the full file to verify pass**

Run: `docker run --rm -v "${PWD}:/app" newsstore pytest -q tests/test_firestore_store.py`
Expected: PASS (all FirestoreStore tests green). FirestoreStore now satisfies all 7 `Store` Protocol methods.

- [ ] **Step 5: Commit**

```bash
git add src/newsstore/store/firestore_store.py tests/test_firestore_store.py
git commit -m "feat: FirestoreStore get_unprocessed/mark_processed (Step-2 contract)"
```

---

## Task 5: Store factory (backend selector)

**Files:**
- Create: `src/newsstore/store/factory.py`
- Test: `tests/test_store_factory.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_store_factory.py`:

```python
import pytest
from newsstore.store.factory import make_store
from newsstore.store.sqlite_store import SqliteStore

def test_default_is_sqlite(tmp_path, monkeypatch):
    monkeypatch.delenv("NEWSSTORE_BACKEND", raising=False)
    s = make_store(db_path=str(tmp_path / "db.sqlite"))
    assert isinstance(s, SqliteStore)

def test_explicit_sqlite(tmp_path):
    s = make_store("sqlite", db_path=str(tmp_path / "db.sqlite"))
    assert isinstance(s, SqliteStore)

def test_env_var_selects_backend(tmp_path, monkeypatch):
    monkeypatch.setenv("NEWSSTORE_BACKEND", "sqlite")
    s = make_store(db_path=str(tmp_path / "db.sqlite"))
    assert isinstance(s, SqliteStore)

def test_unknown_backend_raises():
    with pytest.raises(ValueError):
        make_store("redis")
```

- [ ] **Step 2: Run to verify it fails**

Run: `docker run --rm -v "${PWD}:/app" newsstore pytest -q tests/test_store_factory.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'newsstore.store.factory'`.

- [ ] **Step 3: Create the factory**

Create `src/newsstore/store/factory.py`:

```python
from __future__ import annotations
import os
from .sqlite_store import SqliteStore


def make_store(backend: str | None = None, *,
               db_path: str = "data/newsstore.db",
               project: str | None = None):
    """Select a Store backend. `backend` arg overrides $NEWSSTORE_BACKEND
    (default 'sqlite'). The firestore branch lazy-imports google so sqlite/test
    runs never need the cloud SDK."""
    backend = (backend or os.environ.get("NEWSSTORE_BACKEND", "sqlite")).lower()
    if backend == "sqlite":
        return SqliteStore(db_path)
    if backend == "firestore":
        from google.cloud import firestore
        from .firestore_store import FirestoreStore
        client = firestore.Client(project=project or os.environ.get("GOOGLE_CLOUD_PROJECT"))
        return FirestoreStore(client)
    raise ValueError(f"unknown NEWSSTORE_BACKEND: {backend!r}")
```

- [ ] **Step 4: Run to verify pass**

Run: `docker run --rm -v "${PWD}:/app" newsstore pytest -q tests/test_store_factory.py`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/newsstore/store/factory.py tests/test_store_factory.py
git commit -m "feat: store factory selecting sqlite|firestore by env"
```

---

## Task 6: Wire run.py to the factory

**Files:**
- Modify: `src/newsstore/run.py:5-7,30-33`
- Test: `tests/test_run.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_run.py` (create the file with this content if it does not exist):

```python
from newsstore import run as run_mod

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
```

- [ ] **Step 2: Run to verify it fails**

Run: `docker run --rm -v "${PWD}:/app" newsstore pytest -q tests/test_run.py::test_run_uses_factory_with_env_backend`
Expected: FAIL — `AttributeError: module 'newsstore.run' has no attribute 'make_store'` (run.py still imports SqliteStore directly).

- [ ] **Step 3: Switch run.py to the factory**

In `src/newsstore/run.py`, change the imports (lines 5-7) from:

```python
from .config import load_feeds
from .ssl_config import make_client
from .store.sqlite_store import SqliteStore
from .collector import collect_once
```

to:

```python
from .config import load_feeds
from .ssl_config import make_client
from .store.factory import make_store
from .collector import collect_once
```

Then change the store setup (lines 30-33) from:

```python
    os.makedirs(os.path.dirname(args.db) or ".", exist_ok=True)
    feeds = load_feeds(args.feeds)
    client = make_client()
    with SqliteStore(args.db) as store:
```

to:

```python
    backend = os.environ.get("NEWSSTORE_BACKEND", "sqlite").lower()
    if backend == "sqlite":
        os.makedirs(os.path.dirname(args.db) or ".", exist_ok=True)
    feeds = load_feeds(args.feeds)
    client = make_client()
    with make_store(backend, db_path=args.db) as store:
```

- [ ] **Step 4: Run the new test plus the full suite**

Run: `docker run --rm -v "${PWD}:/app" newsstore pytest -q`
Expected: PASS — the new test passes and all previously-passing tests (sqlite store, collector, run, registry, etc.) stay green. No regression because `sqlite` is still the default.

- [ ] **Step 5: Commit**

```bash
git add src/newsstore/run.py tests/test_run.py
git commit -m "feat: run.py selects store backend via factory (default sqlite)"
```

---

## Task 7: Document the backend switch

**Files:**
- Modify: `README.md:5-16`

- [ ] **Step 1: Update the Run section**

In `README.md`, under "### Run (Docker only — host has no Python)", add after the existing code block:

```markdown
### Storage backend

Default is SQLite (`data/newsstore.db`). To write to Firestore instead, build with the `[gcp]` extra and set env vars — the collector code is identical:

```
# local/tests: SQLite (default), nothing to set
# cloud: Firestore
NEWSSTORE_BACKEND=firestore
GOOGLE_CLOUD_PROJECT=<your-gcp-project>
```

Firestore auth uses Application Default Credentials (on Cloud Run, the job's service account — no key file). See the GCP deploy plan.
```

- [ ] **Step 2: Verify the full suite still passes**

Run: `docker run --rm -v "${PWD}:/app" newsstore pytest -q`
Expected: PASS (docs-only change; tests unaffected).

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document NEWSSTORE_BACKEND switch"
```

---

## Done / Handoff

After Task 7, FirestoreStore is a drop-in `Store` with full unit coverage and `run.py` selects it via `NEWSSTORE_BACKEND`. The real Firestore client is exercised only in the **next plan** (`*-gcp-deploy.md`): build the `[gcp]` image, deploy as a Cloud Run Job, and run a live smoke pass against a real Firestore project (verify items appear, second pass reports 0 new / preserves processed), then Cloud Scheduler, security rules, composite index (`processed ==` + `fetched_at`, and `tags array-contains` + `published_at` for the site), and the static viewer site.
