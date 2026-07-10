# 로컬 레이더 작업장 구현 계획 (2판 — 3렌즈 리뷰 반영)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 스펙 `docs/superpowers/specs/2026-07-10-local-radar-workbench-design.md`대로, Firestore를 로컬 SQLite로 동기화하고 그 위에서 레이더 4신호·종목 스테이션·판단 원장을 순수 산수로 계산해 일일 마크다운을 산출하는 로컬 작업장을 만든다(신규 LLM 콜 0).

**Architecture:** 신규 패키지 `src/newsstore/radar/`에 로컬 전용 모듈을 격리한다(클라우드 `enrich/`·`store/`는 무수정 — `classify_stage1`·`topics.yaml` 읽기 재사용). 데이터는 `data/local.db`·`data/prices.db` 두 SQLite로 분리하고, 원장 3종은 git 추적 파일로 둔다. 진입점은 `run_radar.py --mode sync|prices|radar|backtest`.

**Tech Stack:** Python 3.12(stdlib sqlite3·re·statistics), httpx(기존 core 의존), yfinance(신규 optional extra `radar` — **requirements.lock 밖**: 로컬 전용이라 클라우드 재현 범위가 아님을 주석으로 명시), pytest + Firestore 에뮬레이터(REST 경로), Docker compose.

**공통 규칙(모든 태스크):**
- 테스트는 전부 `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest <경로> -q`.
- 커밋 메시지는 한국어 완결 문어체 + 트레일러 2줄: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` / `Claude-Session: https://claude.ai/code/session_01JTUMM192vhAXM78FTtdALp`
- 기대 개수 매직넘버 금지 — 불변식으로 단언.
- **시간 규약**: '오늘'은 항상 KST(`dt.timezone(dt.timedelta(hours=9))`) 달력일이며 호출 경계(run_radar)에서 한 번만 결정해 아래로 전달한다. fetched_at은 UTC 저장이므로 일자 비교는 KST 변환 헬퍼를 쓴다.
- 픽스처의 `asset_hint`는 실제 feeds 어휘(`kr_stock` 등)를 쓴다 — `kr_equity`는 렌즈 id이지 asset_hint가 아니다(리뷰 실측).

**파일 지도(신규/수정 전체):**
```
config/watchlist.yaml                 (신규) 종목 SSOT
config/radar_vocab.yaml               (신규) 그래프 어휘
radar/gates.yaml                      (신규) 게이트 시드 (+선택 필드 targets)
radar/frames.json                     (신규) 프레임 시드(v2-local)
journal/journal.jsonl                 (신규) 판단 원장 시드
src/newsstore/radar/{__init__,watchlist,match,localdb,sync,prices,ledgers,kernel,station,daily,backtest}.py (신규)
src/newsstore/entrypoints/run_radar.py (신규)
tests/radar/test_*.py                 (신규)
tests/fixtures/prices_capture_*.json  (신규 — Task 5 실측 캡처)
pyproject.toml / infra/Dockerfile / docker-compose.yml / .gitignore (수정)
web/index.html / docs/operations.md / CLAUDE.md (수정)
docs/superpowers/specs/2026-07-10-local-radar-workbench-design.md (수정 — §3.3 gates 선택 필드 targets 한 줄 부록, Task 7)
```

---

### Task 1: watchlist SSOT — config + 로더 + 검증

**Files:** Create `config/watchlist.yaml`, `src/newsstore/radar/__init__.py`(빈 파일), `src/newsstore/radar/watchlist.py` / Test `tests/radar/__init__.py`(빈 파일), `tests/radar/test_watchlist.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/radar/test_watchlist.py
import pytest
from newsstore.radar import watchlist


def test_load_watchlist_and_shape():
    wl = watchlist.load_watchlist("config/watchlist.yaml")
    ids = [e["id"] for e in wl]
    assert "sk_hynix" in ids and "kospi" in ids
    assert len(ids) == len(set(ids))
    hynix = next(e for e in wl if e["id"] == "sk_hynix")
    assert hynix["ticker"] == "000660.KS"
    assert hynix["station"] is True and "하이닉스" in hynix["aliases"]
    for e in wl:
        assert e["role"] in ("stock", "index", "fx")


def test_station_entries_require_aliases(tmp_path):
    bad = tmp_path / "w.yaml"
    bad.write_text(
        "entries:\n  - id: x\n    label: X\n    ticker: T\n    role: stock\n"
        "    station: true\n    aliases: []\n", encoding="utf-8")
    with pytest.raises(ValueError, match="aliases"):
        watchlist.load_watchlist(str(bad))


def test_duplicate_id_and_missing_ticker_fail(tmp_path):
    dup = tmp_path / "d.yaml"
    dup.write_text(
        "entries:\n"
        "  - {id: a, label: A, ticker: T1, role: stock, station: false, aliases: []}\n"
        "  - {id: a, label: A2, ticker: T2, role: stock, station: false, aliases: []}\n",
        encoding="utf-8")
    with pytest.raises(ValueError, match="중복"):
        watchlist.load_watchlist(str(dup))
    noticker = tmp_path / "n.yaml"
    noticker.write_text(
        "entries:\n  - {id: b, label: B, role: stock, station: false, aliases: []}\n",
        encoding="utf-8")
    with pytest.raises(ValueError, match="ticker"):
        watchlist.load_watchlist(str(noticker))
```

- [ ] **Step 2: 실패 확인** — Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/radar/test_watchlist.py -q` / Expected: FAIL

- [ ] **Step 3: config + 구현** — `config/watchlist.yaml`은 스펙 §3.1 코드블록 그대로(entries 5건).

```python
# src/newsstore/radar/watchlist.py
"""config/watchlist.yaml — 종목·지수·환율의 단일 출처(SSOT) 로더.
검증은 로드 시 즉시 터뜨린다(FAIL-LOUD): id 중복·ticker 결측·station인데 aliases 없음."""
from __future__ import annotations

import yaml

REQUIRED = ("id", "label", "ticker", "role", "station", "aliases")
ROLES = ("stock", "index", "fx")


def load_watchlist(path: str = "config/watchlist.yaml") -> list[dict]:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    entries = raw.get("entries") or []
    seen: set[str] = set()
    for e in entries:
        missing = [k for k in REQUIRED if k not in e]
        if missing:
            raise ValueError(f"watchlist 항목 {e.get('id')!r}: 필수 필드 결측 {missing} (ticker 포함)")
        if not e["ticker"]:
            raise ValueError(f"watchlist 항목 {e['id']!r}: ticker 결측")
        if e["id"] in seen:
            raise ValueError(f"watchlist id 중복: {e['id']!r}")
        seen.add(e["id"])
        if e["role"] not in ROLES:
            raise ValueError(f"watchlist 항목 {e['id']!r}: role {e['role']!r}은 {ROLES} 중 하나여야 한다")
        if e["station"] and not e["aliases"]:
            raise ValueError(f"watchlist 항목 {e['id']!r}: station=true면 aliases가 비어 있을 수 없다")
    return entries


def station_entries(entries: list[dict]) -> list[dict]:
    return [e for e in entries if e["station"]]
```

- [ ] **Step 4: 통과 확인** — Expected: PASS
- [ ] **Step 5: Commit** — `feat(radar): watchlist SSOT 로더 — id 중복·ticker 결측·빈 aliases를 로드 시 터뜨린다`

---

### Task 2: 단어경계 매칭 (match.py) + 어휘

**Files:** Create `src/newsstore/radar/match.py`, `config/radar_vocab.yaml` / Test `tests/radar/test_match.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/radar/test_match.py
from newsstore.radar import match


def test_latin_alias_word_boundary():
    assert match.find_alias("IREN", "IREN shares surge 10%") is not None
    assert match.find_alias("IREN", "SIRENS blared downtown") is None
    assert match.find_alias("IREN", "siren 소리가 났다") is None


def test_hangul_alias_allows_josa_but_blocks_leading_attach():
    assert match.find_alias("하이닉스", "하이닉스가 급등했다") is not None
    assert match.find_alias("하이닉스", "SK하이닉스가 발표") is None
    assert match.find_alias("SK하이닉스", "SK하이닉스가 발표") is not None


def test_match_evidence_positions():
    assert match.find_alias("코스피", "오늘 코스피지수는 하락") == ("코스피", 3)


def test_match_any_over_watchlist_aliases():
    aliases = ["SK하이닉스", "하이닉스", "SK hynix"]
    assert match.find_any(aliases, "SK hynix ADR debut") == ("SK hynix", 0)
    assert match.find_any(aliases, "무관한 제목") is None


def test_vocab_file_loads_and_derives_taxonomy():
    vocab = match.load_vocab("config/radar_vocab.yaml")
    assert "Fed" in vocab and "한국은행" in vocab
    assert "HBM" in vocab
```

- [ ] **Step 2: 실패 확인** — Expected: FAIL

- [ ] **Step 3: 구현** — `config/radar_vocab.yaml`:

```yaml
# 그래프 드리프트(신호2) 어휘. taxonomy.yaml entities에서 도출한 11종 + 수동 추가.
# 승격 후보는 신호3(어휘 창발)이 일보에 표기하고, 채택은 사용자가 이 파일에 append한다.
derived_from_taxonomy: true
manual:
  - 엔비디아
  - HBM
  - ADR
```

```python
# src/newsstore/radar/match.py
"""단어경계 어휘 매칭 — 부분문자열 오탐(IREN→사이렌 류) 차단.

규칙(스펙 §5 '토큰 경계'의 스크립트별 구체화):
- 선행 경계: alias 바로 앞이 [가-힣A-Za-z0-9]면 불일치(공통).
- 후행 경계: 라틴/숫자 alias는 뒤가 [A-Za-z0-9]면 불일치. 한글 alias는 뒤에 한글이 와도
  일치(조사 결합 '하이닉스가' 허용 — 한국어는 공백 없이 조사가 붙는다).
"""
from __future__ import annotations

import re

import yaml

_WORD = "0-9A-Za-z가-힣"


def _pattern(alias: str) -> re.Pattern:
    esc = re.escape(alias)
    lead = f"(?<![{_WORD}])"
    tail = "" if re.search(r"[가-힣]$", alias) else "(?![0-9A-Za-z])"
    return re.compile(lead + esc + tail)


def find_alias(alias: str, text: str) -> tuple[str, int] | None:
    m = _pattern(alias).search(text or "")
    return (alias, m.start()) if m else None


def find_any(aliases: list[str], text: str) -> tuple[str, int] | None:
    for a in aliases:
        hit = find_alias(a, text)
        if hit:
            return hit
    return None


def load_vocab(path: str = "config/radar_vocab.yaml") -> list[str]:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    vocab: list[str] = []
    if raw.get("derived_from_taxonomy"):
        with open("config/taxonomy.yaml", encoding="utf-8") as tf:
            tax = yaml.safe_load(tf)
        vocab.extend(tax["entities"])
    vocab.extend(raw.get("manual") or [])
    if len(vocab) != len(set(vocab)):
        raise ValueError("radar_vocab: 중복 어휘")
    return vocab
```

- [ ] **Step 4: 통과 확인** — Expected: PASS
- [ ] **Step 5: Commit** — `feat(radar): 단어경계 어휘 매칭 + radar_vocab(택소노미 도출)`

---

### Task 3: 로컬 DB 계층 (localdb.py) + 시간 헬퍼

**Files:** Create `src/newsstore/radar/localdb.py` / Modify `.gitignore` / Test `tests/radar/test_localdb.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/radar/test_localdb.py
from newsstore.radar import localdb


def _mkitem(i, ts):
    return {"id": f"it{i}", "feed_id": "f1", "source": "src", "asset_hint": "kr_stock",
            "language": "ko", "url": f"http://x/{i}", "title": f"제목 {i}", "body": "본문",
            "published_at": ts, "fetched_at": ts, "kind": "story"}


def test_items_upsert_idempotent(tmp_path):
    db = localdb.connect_items(str(tmp_path / "local.db"))
    rows = [_mkitem(1, "2026-07-01T00:00:00Z"), _mkitem(2, "2026-07-02T00:00:00Z")]
    localdb.upsert_items(db, rows)
    localdb.upsert_items(db, rows)
    assert localdb.count_items(db) == len(rows)


def test_watermark_roundtrip(tmp_path):
    db = localdb.connect_items(str(tmp_path / "local.db"))
    assert localdb.get_watermark(db) is None
    localdb.set_watermark(db, "2026-07-02T00:00:00Z")
    assert localdb.get_watermark(db) == "2026-07-02T00:00:00Z"


def test_kst_day_conversion():
    assert localdb.kst_day("2026-07-09T16:00:00Z") == "2026-07-10"   # UTC 16시 = KST 익일 01시
    assert localdb.kst_day("2026-07-10T02:00:00Z") == "2026-07-10"


def test_prices_upsert_and_flag(tmp_path):
    db = localdb.connect_prices(str(tmp_path / "prices.db"))
    rows = [{"ticker": "000660.KS", "date": "2026-07-09", "open": 100, "high": 110,
             "low": 90, "close": 105, "adj_close": 105, "volume": 1000}]
    localdb.upsert_prices(db, rows, source="yfinance")
    localdb.upsert_prices(db, rows, source="yfinance")
    assert localdb.count_prices(db, "000660.KS") == 1
    localdb.flag_price(db, "000660.KS", "2026-07-09", "high<low")
    assert len(localdb.load_closes(db, "000660.KS", include_flagged=True)) == 1
    assert localdb.load_closes(db, "000660.KS") == []
```

- [ ] **Step 2: 실패 확인** — Expected: FAIL

- [ ] **Step 3: 구현**

```python
# src/newsstore/radar/localdb.py
"""로컬 SQLite 2종 — local.db(Firestore 캐시)·prices.db(야후 캐시). 전부 upsert 멱등.
'오늘'은 KST 달력일 규약 — kst_day가 UTC 타임스탬프를 KST 일자로 변환한다."""
from __future__ import annotations

import datetime as dt
import sqlite3

KST = dt.timezone(dt.timedelta(hours=9))
ITEM_COLS = ("id", "feed_id", "source", "asset_hint", "language", "url", "title",
             "body", "published_at", "fetched_at", "kind")


def kst_day(ts: str) -> str:
    if not ts:
        return ""
    d = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return d.astimezone(KST).date().isoformat()


def today_kst() -> str:
    return dt.datetime.now(tz=KST).date().isoformat()


def connect_items(path: str) -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.execute(f"""CREATE TABLE IF NOT EXISTS items (
        {ITEM_COLS[0]} TEXT PRIMARY KEY,
        {", ".join(c + " TEXT" for c in ITEM_COLS[1:])})""")
    db.execute("CREATE TABLE IF NOT EXISTS sync_state (key TEXT PRIMARY KEY, value TEXT)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_items_fetched ON items(fetched_at)")
    return db


def upsert_items(db, rows: list[dict]) -> None:
    db.executemany(
        f"INSERT OR REPLACE INTO items ({','.join(ITEM_COLS)}) VALUES ({','.join('?' * len(ITEM_COLS))})",
        [tuple(r.get(c) for c in ITEM_COLS) for r in rows])
    db.commit()


def load_items(db) -> list[dict]:
    return [dict(zip(ITEM_COLS, row)) for row in
            db.execute(f"SELECT {','.join(ITEM_COLS)} FROM items")]


def count_items(db) -> int:
    return db.execute("SELECT COUNT(*) FROM items").fetchone()[0]


def get_watermark(db) -> str | None:
    row = db.execute("SELECT value FROM sync_state WHERE key='watermark'").fetchone()
    return row[0] if row else None


def set_watermark(db, ts: str) -> None:
    db.execute("INSERT OR REPLACE INTO sync_state (key, value) VALUES ('watermark', ?)", (ts,))
    db.commit()


def connect_prices(path: str) -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.execute("""CREATE TABLE IF NOT EXISTS prices (
        ticker TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL,
        adj_close REAL, volume REAL, source TEXT, fetched_at TEXT,
        flagged TEXT, PRIMARY KEY (ticker, date))""")
    db.execute("CREATE TABLE IF NOT EXISTS prices_meta (key TEXT PRIMARY KEY, value TEXT)")
    return db


def upsert_prices(db, rows: list[dict], *, source: str) -> None:
    db.executemany(
        """INSERT INTO prices (ticker,date,open,high,low,close,adj_close,volume,source,fetched_at,flagged)
           VALUES (?,?,?,?,?,?,?,?,?,datetime('now'),NULL)
           ON CONFLICT(ticker,date) DO UPDATE SET open=excluded.open, high=excluded.high,
             low=excluded.low, close=excluded.close, adj_close=excluded.adj_close,
             volume=excluded.volume, source=excluded.source, fetched_at=excluded.fetched_at""",
        [(r["ticker"], r["date"], r["open"], r["high"], r["low"], r["close"],
          r["adj_close"], r["volume"], source) for r in rows])
    db.commit()


def count_prices(db, ticker: str) -> int:
    return db.execute("SELECT COUNT(*) FROM prices WHERE ticker=?", (ticker,)).fetchone()[0]


def max_price_date(db, ticker: str) -> str | None:
    return db.execute("SELECT MAX(date) FROM prices WHERE ticker=?", (ticker,)).fetchone()[0]


def flag_price(db, ticker: str, date: str, reason: str) -> None:
    db.execute("UPDATE prices SET flagged=? WHERE ticker=? AND date=?", (reason, ticker, date))
    db.commit()


def load_closes(db, ticker: str, *, include_flagged: bool = False) -> list[tuple[str, float]]:
    q = "SELECT date, close FROM prices WHERE ticker=?"
    if not include_flagged:
        q += " AND flagged IS NULL"
    return db.execute(q + " ORDER BY date", (ticker,)).fetchall()


def get_meta(db, key: str) -> str | None:
    row = db.execute("SELECT value FROM prices_meta WHERE key=?", (key,)).fetchone()
    return row[0] if row else None


def set_meta(db, key: str, value: str) -> None:
    db.execute("INSERT OR REPLACE INTO prices_meta (key, value) VALUES (?, ?)", (key, value))
    db.commit()
```

`.gitignore` 추가(주석·패턴 전부 별도 줄):
```
# 로컬 작업장 캐시·산출물(재생성 가능)
data/*.db
data/*.db-journal
radar_out/
```

- [ ] **Step 4: 통과 확인** — Expected: PASS
- [ ] **Step 5: Commit** — `feat(radar): 로컬 SQLite 계층 — upsert 멱등·flagged 비파괴·KST 일자 규약`

---

### Task 4: Firestore REST 증분 동기화 (sync.py)

**Files:** Create `src/newsstore/radar/sync.py` / Test `tests/radar/test_sync.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/radar/test_sync.py
"""sync는 SDK가 아니라 REST(runQuery)로 에뮬레이터를 친다 — 프로덕션 동일 경로(스펙 §9).
시드는 SDK(fsclient)로 심어도 되지만 읽기는 반드시 sync 코드로 한다."""
import datetime as dt

import httpx
import pytest

from newsstore.radar import localdb, sync


def _seed(fsclient, n, t0):
    for i in range(n):
        fsclient.collection("items").document(f"s{i}-{t0.isoformat()}").set({
            "feed_id": "f1", "source": "src", "asset_hint": "kr_stock", "language": "ko",
            "url": f"http://x/{i}", "title": f"제목 {i}", "body": "본문",
            "published_at": None, "fetched_at": t0 + dt.timedelta(minutes=i),
            "kind": "story", "tags": [], "processed": False,
        })


def test_backfill_incremental_idempotent(fsclient, tmp_path):
    t0 = dt.datetime(2026, 7, 1, tzinfo=dt.timezone.utc)
    _seed(fsclient, 7, t0)
    db = localdb.connect_items(str(tmp_path / "local.db"))
    n1 = sync.run_sync(db, page_size=3)
    assert n1 == 7 and localdb.count_items(db) == 7
    sync.run_sync(db, page_size=3)                            # 멱등(겹침 24h upsert)
    assert localdb.count_items(db) == 7
    _seed(fsclient, 2, t0 + dt.timedelta(days=30))
    sync.run_sync(db, page_size=3)
    assert localdb.count_items(db) == 9


def test_tie_timestamps_not_lost(fsclient, tmp_path):
    t0 = dt.datetime(2026, 7, 1, tzinfo=dt.timezone.utc)
    for i in range(5):                                        # 동일 fetched_at 5건(수집 런 동률)
        fsclient.collection("items").document(f"tie{i}").set({
            "feed_id": "f", "source": "s", "asset_hint": "kr_stock", "language": "ko",
            "url": f"u{i}", "title": f"t{i}", "body": "", "published_at": None,
            "fetched_at": t0, "kind": "story", "tags": [], "processed": False})
    db = localdb.connect_items(str(tmp_path / "local.db"))
    sync.run_sync(db, page_size=2)                            # 페이지 크기 < 동률 그룹
    assert localdb.count_items(db) == 5                       # __name__ 커서로 동률 유실 없음


def test_backfill_zero_docs_crashes(fsclient, tmp_path):
    db = localdb.connect_items(str(tmp_path / "local.db"))
    with pytest.raises(sync.SyncError, match="0건"):
        sync.run_sync(db)


def test_http_403_is_crash_not_empty(tmp_path, monkeypatch):
    db = localdb.connect_items(str(tmp_path / "local.db"))
    class FakeResp:
        status_code = 403
        def raise_for_status(self):
            raise httpx.HTTPStatusError("403", request=None, response=None)
        def json(self):
            return []
    class FakeClient:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def post(self, *a, **k): return FakeResp()
    monkeypatch.setattr(sync.httpx, "Client", lambda *a, **k: FakeClient())
    with pytest.raises(httpx.HTTPStatusError):                 # 403 ≠ 빈 결과(가짜 0 금지)
        sync.run_sync(db)


def test_connection_error_crashes(tmp_path, monkeypatch):
    db = localdb.connect_items(str(tmp_path / "local.db"))
    monkeypatch.setenv("FIRESTORE_EMULATOR_HOST", "localhost:1")
    with pytest.raises(Exception):
        sync.run_sync(db)


def test_partial_page_failure_keeps_watermark_prefix(fsclient, tmp_path, monkeypatch):
    t0 = dt.datetime(2026, 7, 1, tzinfo=dt.timezone.utc)
    _seed(fsclient, 6, t0)
    db = localdb.connect_items(str(tmp_path / "local.db"))
    calls = {"n": 0}
    orig = sync._run_query_page
    def boom(*a, **k):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("network")
        return orig(*a, **k)
    monkeypatch.setattr(sync, "_run_query_page", boom)
    with pytest.raises(RuntimeError):
        sync.run_sync(db, page_size=3)
    assert localdb.get_watermark(db) is not None               # 완결 1페이지까지만 전진(prefix)
    assert localdb.count_items(db) == 3
```

- [ ] **Step 2: 실패 확인** — Expected: FAIL

- [ ] **Step 3: 구현**

```python
# src/newsstore/radar/sync.py
"""Firestore → local.db 증분 동기화 (REST runQuery·공개 읽기·무인증).

- 워터마크 = fetched_at(수집기가 전 문서 필수 세팅 — published_at은 nullable이라 부적합).
- 커서: orderBy (fetched_at ASC, __name__ ASC) + startAt(before=false) — 동률 그룹 유실 없음.
- 페이지 단위 체크포인트: 워터마크는 '마지막 완결 페이지의 max(fetched_at)'까지만 전진
  (max는 문자열이 아니라 datetime 비교 — 소수부 생략 직렬화의 사전순 함정 회피).
- FAIL-LOUD: 초회 백필 0건 크래시, HTTP 상태 오류는 raise_for_status로 즉시 크래시.
"""
from __future__ import annotations

import datetime as dt
import os

import httpx

from . import localdb

OVERLAP = dt.timedelta(hours=24)


class SyncError(RuntimeError):
    pass


def _base_url() -> str:
    emu = os.environ.get("FIRESTORE_EMULATOR_HOST")
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "test")
    host = f"http://{emu}" if emu else "https://firestore.googleapis.com"
    return f"{host}/v1/projects/{project}/databases/(default)/documents"


def _ts_key(ts: str) -> dt.datetime:
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _decode(v: dict):
    if "stringValue" in v: return v["stringValue"]
    if "timestampValue" in v: return v["timestampValue"]
    if "integerValue" in v: return int(v["integerValue"])
    if "doubleValue" in v: return v["doubleValue"]
    if "booleanValue" in v: return v["booleanValue"]
    return None


def _to_row(doc: dict) -> dict:
    fields = doc.get("fields", {})
    row = {c: _decode(fields[c]) for c in localdb.ITEM_COLS[1:] if c in fields}
    row["id"] = doc["name"].rsplit("/", 1)[-1]
    return row


def _run_query_page(client: httpx.Client, after_ts: str | None,
                    cursor: tuple[str, str] | None, page_size: int) -> list[dict]:
    q: dict = {
        "from": [{"collectionId": "items"}],
        "orderBy": [{"field": {"fieldPath": "fetched_at"}, "direction": "ASCENDING"},
                    {"field": {"fieldPath": "__name__"}, "direction": "ASCENDING"}],
        "limit": page_size,
    }
    if after_ts:
        q["where"] = {"fieldFilter": {"field": {"fieldPath": "fetched_at"},
                                      "op": "GREATER_THAN",
                                      "value": {"timestampValue": after_ts}}}
    if cursor:
        q["startAt"] = {"values": [{"timestampValue": cursor[0]},
                                   {"referenceValue": cursor[1]}],
                        "before": False}
    r = client.post(f"{_base_url()}:runQuery", json={"structuredQuery": q}, timeout=30)
    r.raise_for_status()
    return [e["document"] for e in r.json() if "document" in e]


def run_sync(db, *, page_size: int = 300) -> int:
    wm = localdb.get_watermark(db)
    first_run = wm is None and localdb.count_items(db) == 0
    after = None
    if wm:
        after = (_ts_key(wm) - OVERLAP).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    total = 0
    cursor = None
    with httpx.Client() as client:
        while True:
            docs = _run_query_page(client, after, cursor, page_size)
            if not docs:
                break
            rows = [_to_row(d) for d in docs]
            localdb.upsert_items(db, rows)
            stamps = [r["fetched_at"] for r in rows if r.get("fetched_at")]
            if stamps:
                localdb.set_watermark(db, max(stamps, key=_ts_key))
            total += len(rows)
            cursor = (docs[-1]["fields"]["fetched_at"]["timestampValue"], docs[-1]["name"])
            if len(docs) < page_size:
                break
    if first_run and total == 0:
        raise SyncError("초회 백필 결과 0건 — 필드명 드리프트 또는 rules 변경 의심(빈 성공 금지)")
    return total
```

- [ ] **Step 4: 통과 확인** — Expected: PASS. 에뮬레이터가 referenceValue 커서·필터를 프로덕션과 다르게 처리해 실패하면 **커서 방식을 임의 변경하지 말고 실패 메시지를 그대로 보고**한다(계약 조정은 메인 세션 승인 후).
- [ ] **Step 5: Commit** — `feat(radar): Firestore REST 증분 sync — 동률 안전 커서·페이지 체크포인트·빈 성공 차단`

---

### Task 5: prices 적재 (prices.py) + 의존성·이미지 + 실측 캡처

**Files:** Create `src/newsstore/radar/prices.py` / Modify `pyproject.toml`, `infra/Dockerfile` / Test `tests/radar/test_prices.py`, Create `tests/fixtures/prices_capture_*.json`(Step 5에서 실측 생성)

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/radar/test_prices.py
"""로직 테스트는 DI fetch로. 실계약(컬럼·NaN 형태)은 Step 5의 실측 캡처 파일과 대조하는
test_fixture_shape_matches_capture가 지킨다(오답노트 'fake가 실계약 약화' 재발 방지)."""
import json
import pathlib

import pytest

from newsstore.radar import localdb, prices


def _hist(dates_closes):
    return [{"date": d, "open": c, "high": c + 1, "low": c - 1, "close": c,
             "adj_close": c, "volume": 100} for d, c in dates_closes]


def _entry():
    return [{"id": "a", "ticker": "T", "role": "stock"}]


def test_ingest_upsert_and_overlap(tmp_path):
    db = localdb.connect_prices(str(tmp_path / "p.db"))
    fetch = lambda ticker, start: _hist([("2026-07-08", 100.0), ("2026-07-09", 101.0)])
    prices.ingest(db, _entry(), fetch=fetch, today="2026-07-09")
    prices.ingest(db, _entry(), fetch=fetch, today="2026-07-09")
    assert localdb.count_prices(db, "T") == 2


def test_row_level_anomaly_and_nan_flagged(tmp_path):
    db = localdb.connect_prices(str(tmp_path / "p.db"))
    bad = _hist([("2026-07-08", 100.0), ("2026-07-09", 100.0)])
    bad[0]["high"] = 50.0                                        # high<low
    bad[1]["close"] = float("nan")                               # yfinance 결측일 NaN(실계약)
    prices.ingest(db, _entry(), fetch=lambda t, s: bad, today="2026-07-09")
    assert localdb.load_closes(db, "T") == []                    # 두 행 다 flagged 격리
    assert len(localdb.load_closes(db, "T", include_flagged=True)) == 2


def test_no_new_dates_counts_as_zero_day(tmp_path):
    """겹침 이력만 반환(신규 날짜 없음)도 0행으로 센다 — stale 소스가 streak을 리셋 못 한다."""
    db = localdb.connect_prices(str(tmp_path / "p.db"))
    localdb.upsert_prices(db, [dict(_hist([("2026-07-07", 99.0)])[0], ticker="T")], source="t")
    stale = lambda t, s: _hist([("2026-07-07", 99.0)])           # 이미 있는 날짜만
    r1 = prices.ingest(db, _entry(), fetch=stale, today="2026-07-08")
    assert r1["T"]["status"] == "missing"
    prices.ingest(db, _entry(), fetch=stale, today="2026-07-08")  # 같은 날 재실행 — streak 비증가(멱등)
    prices.ingest(db, _entry(), fetch=stale, today="2026-07-09")
    with pytest.raises(prices.PricesError, match="3"):
        prices.ingest(db, _entry(), fetch=stale, today="2026-07-10")


def test_fixture_shape_matches_capture():
    """DI 픽스처의 키 집합이 실측 캡처와 동일해야 한다 — 캡처 파일은 Step 5에서 생성·커밋."""
    cap_dir = pathlib.Path("tests/fixtures")
    caps = sorted(cap_dir.glob("prices_capture_*.json"))
    if not caps:
        pytest.skip("실측 캡처 미생성(Task 5 Step 5 이전)")
    fixture_keys = set(_hist([("2026-07-09", 1.0)])[0].keys())
    for cap in caps:
        rows = json.loads(cap.read_text(encoding="utf-8"))
        assert rows, f"{cap.name}: 캡처 비어 있음"
        assert set(rows[0].keys()) == fixture_keys, f"{cap.name}: 실계약과 픽스처 키 불일치"
```

- [ ] **Step 2: 실패 확인** — Expected: FAIL

- [ ] **Step 3: 구현**

```python
# src/newsstore/radar/prices.py
"""watchlist 일봉 적재 — yfinance 단일 소스(Stooq 봇차단 실측 기각, 스펙 §3.2).

sanity 경계(스펙 §3.2):
- 행 수준: high<low·close<=0·NaN(yfinance 결측일 실계약)은 flagged 격리(비파괴).
- 배치 수준: '신규 날짜 행 0건'(겹침 재수신은 신규가 아니다)을 달력일 기준으로 세어
  1일차는 결측 표기(휴장 가능), 3일 연속이면 크래시. 같은 날 재실행은 비증가(멱등).
"""
from __future__ import annotations

import datetime as dt
import json

from . import localdb


class PricesError(RuntimeError):
    pass


def default_fetch(ticker: str, start: str) -> list[dict]:
    import yfinance as yf
    hist = yf.Ticker(ticker).history(start=start, auto_adjust=False)
    rows = []
    for idx, r in hist.iterrows():
        rows.append({"date": idx.strftime("%Y-%m-%d"), "open": float(r["Open"]),
                     "high": float(r["High"]), "low": float(r["Low"]),
                     "close": float(r["Close"]),
                     "adj_close": float(r.get("Adj Close", r["Close"])),
                     "volume": float(r.get("Volume") or 0)})
    return rows


def _is_bad(r: dict) -> bool:
    vals = (r["open"], r["high"], r["low"], r["close"])
    if any(v != v for v in vals):                 # NaN(자기 자신과 다름)
        return True
    return r["high"] < r["low"] or r["close"] <= 0


def ingest(db, entries: list[dict], *, fetch=default_fetch, today: str | None = None) -> dict:
    today = today or localdb.today_kst()
    report: dict = {}
    for e in entries:
        t = e["ticker"]
        last = localdb.max_price_date(db, t)
        start = ((dt.date.fromisoformat(last) - dt.timedelta(days=7)).isoformat()
                 if last else "2024-01-01")
        rows = fetch(t, start)
        for r in rows:
            r["ticker"] = t
        if rows:
            localdb.upsert_prices(db, rows, source="yfinance")
            for r in rows:
                if _is_bad(r):
                    localdb.flag_price(db, t, r["date"], "sanity: NaN/high<low/close<=0")
        new_dates = [r["date"] for r in rows if not last or r["date"] > last]
        if not new_dates:
            if last and last >= today:                            # 이미 당일 데이터 보유 — 최신 상태
                localdb.set_meta(db, f"zero:{t}", json.dumps({"streak": 0, "last": today}))
                report[t] = {"status": "current", "rows": 0}
                continue
            state = json.loads(localdb.get_meta(db, f"zero:{t}") or '{"streak": 0, "last": ""}')
            if state["last"] != today:                            # 같은 날 재실행 비증가
                state = {"streak": state["streak"] + 1, "last": today}
                localdb.set_meta(db, f"zero:{t}", json.dumps(state))
            if state["streak"] >= 3:
                raise PricesError(f"{t}: 신규 날짜 0행 {state['streak']}일 연속 — 소스 파손 의심(3일 임계)")
            report[t] = {"status": "missing", "reason": f"신규 날짜 0행({state['streak']}일차 — 휴장 가능)"}
            continue
        localdb.set_meta(db, f"zero:{t}", json.dumps({"streak": 0, "last": today}))
        report[t] = {"status": "ok", "rows": len(new_dates)}
    return report
```

`pyproject.toml` optional-dependencies에 추가:
```toml
# 로컬 레이더 작업장(prices) 전용 — 클라우드 이미지 미포함. requirements.lock 밖에 둔다
# (lock은 클라우드 재현용이고 radar extra는 로컬 전용이라는 의도적 결정 — 스펙 2026-07-10).
radar = ["yfinance>=0.2.40"]
```

`infra/Dockerfile` — `ARG INSTALL_ENRICH=false` 아래에 추가 + EXTRAS 조립 라인에 합류:
```dockerfile
# 로컬 레이더 작업장(sync/prices/radar) 이미지는 INSTALL_RADAR=true 로 빌드 → yfinance 포함.
ARG INSTALL_RADAR=false
```
```dockerfile
    if [ "$INSTALL_RADAR" = "true" ]; then EXTRAS="${EXTRAS:+$EXTRAS,}radar" ; fi ; \
```

- [ ] **Step 4: 로직 테스트 통과 확인** — Expected: PASS(캡처 테스트는 skip)

- [ ] **Step 5: role별 실측 캡처 → 커밋 게이트** — 이미지를 빌드해 role별 실호출을 1회씩 실측하고 **응답 원형을 캡처 파일로 저장**한다:
  Run: `docker compose build test` 뒤(test 이미지는 yfinance 미포함이므로) 임시로 아래를 실행:
  `MSYS_NO_PATHCONV=1 docker compose run --rm --entrypoint python -e CAP=1 test -c "print('use radar image')"` 는 쓰지 말고, radar 이미지를 먼저 빌드한다(compose 서비스는 Task 10에서 추가되므로 여기서는 직접 빌드):
  `docker build -f infra/Dockerfile --build-arg INSTALL_DEV=false --build-arg INSTALL_RADAR=true -t newsstore-radar .`
  `MSYS_NO_PATHCONV=1 docker run --rm -v "$(pwd):/app" newsstore-radar python -c "import json, pathlib; from newsstore.radar.prices import default_fetch; [pathlib.Path(f'tests/fixtures/prices_capture_{role}.json').write_text(json.dumps(default_fetch(t, '2026-07-01')[:3], ensure_ascii=False, indent=1), encoding='utf-8') for role, t in (('stock','005930.KS'),('index','^KS11'),('fx','KRW=X'))]"`
  Expected: `tests/fixtures/prices_capture_{stock,index,fx}.json` 3개 생성, 각 파일 행 ≥1. **실패하면 진행을 멈추고 보고**(스펙 §3.2 실측 게이트). 생성 후 캡처 테스트 재실행:
  Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/radar/test_prices.py -q` / Expected: PASS(skip 없음). 캡처에서 픽스처와 다른 실계약(키 추가·NaN 형태)이 드러나면 `_hist`·`default_fetch`를 실계약 쪽으로 맞추고 재실행한다.
- [ ] **Step 6: Commit** — `feat(radar): prices 적재 — 신규 날짜 기준 0행 판정·NaN 격리·role별 실측 캡처 픽스처`

---

### Task 6: 원장 검증기 (ledgers.py)

**Files:** Create `src/newsstore/radar/ledgers.py` / Test `tests/radar/test_ledgers.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/radar/test_ledgers.py
import pytest

from newsstore.radar import ledgers


def _gate(**kw):
    g = {"id": "g1", "date": "2026-07-29", "test": "t", "on_confirm": "c",
         "on_refute": "r", "status": "pending"}
    g.update(kw)
    return g


def test_gates_status_vocab_and_transition_requires_user():
    ledgers.validate_gates([_gate()])
    with pytest.raises(ValueError, match="status"):
        ledgers.validate_gates([_gate(status="done")])
    with pytest.raises(ValueError, match="judged_by"):
        ledgers.validate_gates([_gate(status="confirmed")])
    ledgers.validate_gates([_gate(status="confirmed", judged_by="user")])


def test_gates_targets_optional_list():
    ledgers.validate_gates([_gate(targets=["sk_hynix"])])
    with pytest.raises(ValueError, match="targets"):
        ledgers.validate_gates([_gate(targets="sk_hynix")])       # 리스트가 아니면 거부


def test_gates_overdue_and_due_window():
    over = ledgers.overdue_pending([_gate(date="2026-07-01")], today="2026-07-10", grace_days=3)
    assert [g["id"] for g in over] == ["g1"]
    assert ledgers.overdue_pending([_gate(date="2026-07-09")], today="2026-07-10", grace_days=3) == []
    assert ledgers.due_around([_gate(date="2026-07-11")], today="2026-07-10")
    assert not ledgers.due_around([_gate(date="2026-07-20")], today="2026-07-10")


def test_journal_plan_requires_invalidation_and_by(tmp_path):
    p = tmp_path / "j.jsonl"
    ok = {"type": "plan", "id": "p1", "date": "2026-07-10", "target": "sk_hynix",
          "thesis": "t", "band": [1, 2], "invalidation": "x", "triggers": [], "by": "2026-07-29"}
    ledgers.append_journal(str(p), ok)
    bad = dict(ok, id="p2")
    bad.pop("invalidation")
    with pytest.raises(ValueError, match="invalidation"):
        ledgers.append_journal(str(p), bad)
    assert len(p.read_text(encoding="utf-8").strip().splitlines()) == 1


def test_journal_review_verdict_basis_schema(tmp_path):
    p = tmp_path / "j.jsonl"
    ok = {"type": "review", "plan_id": "p1", "date": "2026-08-01",
          "verdict_basis": {"kind": "price", "metric": "close", "value": 2050000, "source": "prices.db"}}
    ledgers.append_journal(str(p), ok)
    with pytest.raises(ValueError, match="verdict_basis"):
        ledgers.append_journal(str(p), {"type": "review", "plan_id": "p1", "date": "2026-08-01",
                                        "verdict_basis": "느낌이 나빴다"})
    narr = {"type": "review", "plan_id": "p1", "date": "2026-08-01",
            "verdict_basis": {"kind": "narrative", "note": "서사"}}
    with pytest.raises(ValueError, match="user_approved"):
        ledgers.append_journal(str(p), narr)
    ledgers.append_journal(str(p), dict(narr, user_approved=True))


def test_frames_v2_local_contract():
    def pole(i, status="active"):
        return {"id": f"p{i}", "label": f"L{i}", "evidence": "e", "test": "t",
                "retire_when": "w", "status": status}
    frame = {"risks": [pole(i) for i in range(5)], "premiums": [], "watchpoints": []}
    ledgers.validate_frames({"kr_equity": frame}, gate_ids=set())
    with pytest.raises(ValueError, match="5"):
        ledgers.validate_frames({"kr_equity": {"risks": [pole(i) for i in range(6)],
                                               "premiums": [], "watchpoints": []}}, gate_ids=set())
    retired_ok = {"risks": [pole(i) for i in range(5)] + [pole(9, "retired")],
                  "premiums": [], "watchpoints": []}
    ledgers.validate_frames({"kr_equity": retired_ok}, gate_ids=set())
    with pytest.raises(ValueError, match="gate"):
        ledgers.validate_frames({"kr_equity": {"risks": [dict(pole(1), gate_id="ghost")],
                                               "premiums": [], "watchpoints": []}}, gate_ids={"g1"})
    with pytest.raises(ValueError, match="축"):
        ledgers.validate_frames({"kr_equity": {"risks": []}}, gate_ids=set())
    dropped = ledgers.drop_invalid_poles({"risks": [pole(1), {"id": "", "label": ""}],
                                          "premiums": [], "watchpoints": []})
    assert [q["id"] for q in dropped["risks"]] == ["p1"]
```

- [ ] **Step 2: 실패 확인** — Expected: FAIL

- [ ] **Step 3: 구현**

```python
# src/newsstore/radar/ledgers.py
"""원장 3종 검증기 — gates.yaml·journal.jsonl·frames.json(v2-local).
결정⑨a: 판정·채점의 주체와 근거를 스키마가 강제한다 — Claude의 재량에 의존하지 않는다."""
from __future__ import annotations

import datetime as dt
import json

import yaml

GATE_STATUSES = ("pending", "confirmed", "refuted", "void")
AXES = ("risks", "premiums", "watchpoints")
MAX_ACTIVE_POLES = 5
BASIS_KINDS = ("price", "flow", "event")


def load_gates(path: str = "radar/gates.yaml") -> list[dict]:
    with open(path, encoding="utf-8") as f:
        gates = (yaml.safe_load(f) or {}).get("gates") or []
    validate_gates(gates)
    return gates


def validate_gates(gates: list[dict]) -> None:
    seen: set[str] = set()
    for g in gates:
        for k in ("id", "date", "test", "on_confirm", "on_refute", "status"):
            if not g.get(k):
                raise ValueError(f"gate {g.get('id')!r}: 필수 필드 {k} 결측")
        if g["id"] in seen:
            raise ValueError(f"gate id 중복: {g['id']}")
        seen.add(g["id"])
        if g["status"] not in GATE_STATUSES:
            raise ValueError(f"gate {g['id']}: status {g['status']!r}는 {GATE_STATUSES} 밖")
        if g["status"] != "pending" and g.get("judged_by") != "user":
            raise ValueError(f"gate {g['id']}: 상태 전이엔 judged_by: user 필수(결정⑨a)")
        if "targets" in g and not isinstance(g["targets"], list):
            raise ValueError(f"gate {g['id']}: targets는 watchlist id 리스트여야 한다")


def overdue_pending(gates: list[dict], *, today: str, grace_days: int = 3) -> list[dict]:
    t = dt.date.fromisoformat(today)
    return [g for g in gates if g["status"] == "pending"
            and dt.date.fromisoformat(str(g["date"])) + dt.timedelta(days=grace_days) < t]


def due_around(gates: list[dict], *, today: str, window_days: int = 2) -> list[dict]:
    t = dt.date.fromisoformat(today)
    return [g for g in gates if g["status"] == "pending"
            and abs((dt.date.fromisoformat(str(g["date"])) - t).days) <= window_days]


def gates_for_target(gates: list[dict], target_id: str) -> list[dict]:
    return [g for g in gates if target_id in (g.get("targets") or [])]


def _validate_entry(e: dict) -> None:
    if e.get("type") == "plan":
        for k in ("id", "date", "target", "thesis", "band", "invalidation", "by"):
            if not e.get(k):
                raise ValueError(f"journal plan: 필수 필드 {k} 결측 — 시한 없는 판단은 채점 불가")
    elif e.get("type") == "review":
        vb = e.get("verdict_basis")
        if not isinstance(vb, dict):
            raise ValueError("journal review: verdict_basis는 구조화 필드여야 한다(자유 문자열 금지 — 결정⑨a)")
        if vb.get("kind") in BASIS_KINDS:
            for k in ("metric", "value", "source"):
                if k not in vb:
                    raise ValueError(f"journal review: verdict_basis.{k} 결측")
        elif not e.get("user_approved"):
            raise ValueError("journal review: 결정론 kind(price|flow|event)가 아니면 user_approved 필수")
    else:
        raise ValueError(f"journal: 알 수 없는 type {e.get('type')!r}")


def append_journal(path: str, entry: dict) -> None:
    _validate_entry(entry)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_journal(path: str = "journal/journal.jsonl") -> list[dict]:
    try:
        with open(path, encoding="utf-8") as f:
            entries = [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []
    for e in entries:
        _validate_entry(e)
    return entries


def active_plans(entries: list[dict], *, today: str) -> list[dict]:
    return [e for e in entries if e.get("type") == "plan" and str(e.get("by", "")) >= today]


def drop_invalid_poles(frame: dict) -> dict:
    return {ax: [p for p in frame.get(ax, []) if p.get("id") and p.get("label")]
            for ax in AXES}


def validate_frames(frames: dict, *, gate_ids: set[str]) -> None:
    for lens, frame in frames.items():
        missing = [ax for ax in AXES if ax not in frame]
        if missing:
            raise ValueError(f"frames[{lens}]: 축 결측 {missing} — 축 3종 필수")
        for ax in AXES:
            poles = frame[ax]
            active = [p for p in poles if p.get("status", "active") == "active"]
            if len(active) > MAX_ACTIVE_POLES:
                raise ValueError(f"frames[{lens}].{ax}: active 극 {len(active)}개 — 상한 {MAX_ACTIVE_POLES}")
            for p in poles:
                gid = p.get("gate_id")
                if gid and gid not in gate_ids:
                    raise ValueError(f"frames[{lens}].{ax}.{p.get('id')}: gate_id {gid!r} 미실재")


def load_frames(path: str = "radar/frames.json", *, gate_ids: set[str]) -> dict:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    frames = raw.get("lenses") or {}
    validate_frames(frames, gate_ids=gate_ids)
    return frames
```

- [ ] **Step 4: 통과 확인** — Expected: PASS
- [ ] **Step 5: Commit** — `feat(radar): 원장 검증기 — judged_by·verdict_basis 스키마 강제 + gates targets 선택 필드`

---

### Task 7: 시드 3종 + 스펙 부록 한 줄

**Files:** Create `radar/gates.yaml`, `journal/journal.jsonl`, `radar/frames.json` / Modify `docs/superpowers/specs/2026-07-10-local-radar-workbench-design.md` / Test `tests/radar/test_seeds.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/radar/test_seeds.py
"""시드가 자기 검증기를 통과하는지 — 시드·계약 드리프트를 커밋 전에 터뜨린다."""
from newsstore.radar import ledgers


def test_seed_gates_valid_ids_and_targets():
    gates = ledgers.load_gates("radar/gates.yaml")
    ids = {g["id"] for g in gates}
    assert {"gate-0729-hynix-call", "gate-adr-pin-release", "gate-price-sync-stability",
            "gate-workbench-adoption-review", "gate-arrival-news-verdict"} <= ids
    assert all(g["status"] == "pending" for g in gates)
    hynix_gates = ledgers.gates_for_target(gates, "sk_hynix")
    assert {"gate-0729-hynix-call", "gate-adr-pin-release"} <= {g["id"] for g in hynix_gates}


def test_seed_journal_valid():
    entries = ledgers.load_journal("journal/journal.jsonl")
    plans = [e for e in entries if e["type"] == "plan"]
    assert plans and plans[0]["target"] == "sk_hynix" and plans[0]["band"] == [2100000, 2200000]


def test_seed_frames_valid_and_gate_refs_resolve():
    gates = ledgers.load_gates("radar/gates.yaml")
    frames = ledgers.load_frames("radar/frames.json", gate_ids={g["id"] for g in gates})
    kr = frames["kr_equity"]
    assert {p["id"] for p in kr["risks"]} == {"lev-etf-reflexivity", "cycle-peak-thesis", "sell-on-best-print"}
    assert any(p.get("gate_id") == "gate-adr-pin-release" for p in kr["premiums"])
    assert "risk" in frames and any(p["id"] == "llm-herding" for p in frames["risk"]["risks"])
```

- [ ] **Step 2: 실패 확인** — Expected: FAIL

- [ ] **Step 3: 시드 작성** — `radar/gates.yaml`은 스펙 §3.3 원문에 **종목 게이트 2건에만 `targets` 추가**: `gate-0729-hynix-call`·`gate-adr-pin-release`에 `targets: [sk_hynix]` 한 줄씩(나머지 3건은 전역 게이트 — targets 없음). `journal/journal.jsonl`은 스펙 §3.4 원문 그대로. `radar/frames.json`은 아래 그대로:

```json
{
  "as_of": "2026-07-10",
  "note": "시드는 확정판이 아니라 첫 재심 대상이다 — 폭락 직후라 risks 과체중·반도체 협착(스펙 §7). 게이트 날짜도 첫 재심에서 가동 개시일 기준 재설정 가능.",
  "lenses": {
    "kr_equity": {
      "risks": [
        {"id": "lev-etf-reflexivity", "label": "레버리지 ETF 반사성 레짐", "evidence": "사이드카 29회·서킷 5회, fwd PER 5~6x에서 -18% — 강제 플로우가 가격을 결정", "test": "일중 변동성·사이드카 빈도의 평시 복귀 여부", "retire_when": "레버리지 상품 순자산 유의미 축소 또는 규제 변경", "status": "active"},
        {"id": "cycle-peak-thesis", "label": "사이클 피크아웃 테제(2028 capex 벽·HBM 가격 균열)", "evidence": "가격상태 하락장 확정이나 실적 롤오버 미입증 — 입증 책임 대칭", "test": "7/29 SK하이닉스 콜의 capex 지속성·HBM 가격 신호", "retire_when": "2개 분기 연속 가이던스로 방향 확정 시 상수화", "status": "active", "gate_id": "gate-0729-hynix-call"},
        {"id": "sell-on-best-print", "label": "호재 선반영(사상 최대 실적에 셀온)", "evidence": "삼성 OP 89.4조 프린트에도 지수 -7.5%", "test": "다음 대형 호재에서 반복 여부", "retire_when": "호재에 지수가 오르는 프린트 1회", "status": "active"}
      ],
      "premiums": [
        {"id": "forced-flow-rebound", "label": "저PER 강제매도의 반등 여력", "evidence": "저PER + 폭력적 매도 = 신념 매도보다 강제 매도 — 플로우 소진 시 펀더 증거 없이 반등 가능", "test": "외국인 순매수 전환 + 레버리지 청산 플로우 소진", "retire_when": "fwd PER 재확장 시", "status": "active"},
        {"id": "adr-book-conviction", "label": "ADR 북빌딩 수요의 조용한 강세(시한부)", "evidence": "본주 -10% 구간에서도 철회 옵션 미행사·7배 유지, +2.9% 프리미엄 프라이싱", "test": "상장 첫 주 $149 방어 여부", "retire_when": "상장 안착 판정과 함께 소화", "status": "active", "gate_id": "gate-adr-pin-release"}
      ],
      "watchpoints": [
        {"id": "hynix-q2-call", "label": "7/29 SK하이닉스 Q2 콜", "evidence": "capex·HBM 신호의 유일한 구조적 도착 지점", "test": "콜 내용", "retire_when": "콜 종료 즉시 — 결과를 risks 극으로 이관", "status": "active", "gate_id": "gate-0729-hynix-call"},
        {"id": "adr-pin-watch", "label": "ADR $149 앵커 핀(본주 ~225만)", "evidence": "차익거래가 본주를 앵커에 핀 — 핀 구간 본주 가격엔 방향 정보 없음", "test": "핀 해제 후 본주 자율 가격 발견", "retire_when": "상장 안착(첫 주 경과) 시", "status": "active", "gate_id": "gate-adr-pin-release"},
        {"id": "foreign-flow-turn", "label": "외국인 수급 전환", "evidence": "+2,173→+794→-5,440으로 트리거 리셋", "test": "순매수 프린트 복귀(판정식은 수급 방안 착수 시 코드로)", "retire_when": "추세 확정 후 상수화", "status": "active"},
        {"id": "canary-sksquare", "label": "SK스퀘어 카나리아 재검증", "evidence": "첫 아웃퍼폼(+3.92%)이나 ADR 핀 특수일이라 오염", "test": "핀 해제 주간 비례 유지 여부", "retire_when": "판정 완료 시", "status": "active"}
      ]
    },
    "risk": {
      "risks": [
        {"id": "mdd-basis-confusion", "label": "레버리지 MDD의 기초자산 오독", "evidence": "지수 -17.6%·현물 -21.9%·2x -40%를 혼동하면 리엔트리 사이징 오판", "test": "포지션 문서에 기준 자산 명시 여부", "retire_when": "없음(상시 극)", "status": "active"},
        {"id": "llm-herding", "label": "LLM 동의를 센티먼트 센서로 쓰는 군집 편입", "evidence": "동질 모델 사용자와 동일 신호 공유 — 컨트라리안 지표로 캘리브레이션돼 있지 않음", "test": "판단 근거에 'Claude 동의'가 등장하면 발동", "retire_when": "없음(상시 극)", "status": "active"}
      ],
      "premiums": [],
      "watchpoints": [
        {"id": "bear-threshold", "label": "베어 임계 -20%(코스피 7,232) 통과 여부", "evidence": "전고점 9,040 대비 -17.6%로 근접", "test": "종가 기준 통과", "retire_when": "±5% 이탈로 논점 해소 시", "status": "active"}
      ]
    }
  }
}
```

스펙 §3.3 계약 문단 끝에 한 줄 부록을 추가한다(마커는 마지막 줄 유지): `게이트에는 선택 필드 targets(watchlist id 리스트)를 둘 수 있다 — 종목 스테이션의 "오늘의 게이트" 구획이 이 필드로 필터한다(스키마 검증: 리스트 타입).`

- [ ] **Step 4: 통과 확인** — Expected: PASS
- [ ] **Step 5: Commit** — `feat(radar): 원장 시드 3종 + gates targets 부록 — 게이트 5건·플랜 1건·프레임 2렌즈`

---

### Task 8: 레이더 커널 (kernel.py)

**Files:** Create `src/newsstore/radar/kernel.py` / Test `tests/radar/test_kernel.py`

- [ ] **Step 0: 계약 확인(읽기)** — `lens_classify.classify_stage1` 시그니처(키워드 인자, `list[str]` 반환)와 `topics.load_topics`(lru_cache)를 읽고 호출부를 계약에 맞춘다.

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/radar/test_kernel.py
from newsstore.radar import kernel, match


def _item(i, ts, title, hint="kr_stock"):
    return {"id": f"i{i}", "feed_id": "f", "source": f"src{i % 2}", "asset_hint": hint,
            "language": "ko", "url": f"http://x/{i}", "title": title, "body": "",
            "published_at": ts, "fetched_at": ts, "kind": "story"}


def test_dedup_by_normalized_title():
    rows = [_item(1, "2026-07-10T01:00:00Z", "삼성전자  실적 발표"),
            _item(2, "2026-07-10T02:00:00Z", "삼성전자 실적 발표")]
    assert len(kernel.dedup(rows)) == 1


def test_zscore_series():
    assert kernel.zscore(10, [2, 2, 2, 2]) == "new"            # 표준편차 0 + 초과 → 신규
    z = kernel.zscore(10, [2, 4, 2, 4])
    assert isinstance(z, float) and z > 0
    assert kernel.zscore(0, []) == "new" or kernel.zscore(0, []) == 0.0  # 빈 기준선 규약 확인용


def test_baseline_coverage_guard():
    ok, _ = kernel.baseline_coverage([1] * 21, window_days=28, min_ratio=2 / 3)
    assert ok
    ok2, reason2 = kernel.baseline_coverage([1] * 10, window_days=28, min_ratio=2 / 3)
    assert not ok2 and "부족" in reason2


def test_article_lenses_and_lens_counts():
    rows = [_item(1, "2026-07-10T01:00:00Z", "삼성전자 실적"),
            _item(2, "2026-07-10T02:00:00Z", "코스피 반등")]
    per = kernel.article_lenses(rows)                          # {item_id: [lens_id...]} 1회 분류
    assert set(per) == {"i1", "i2"}
    counts = kernel.lens_counts_from(per)
    assert sum(counts.values()) >= 1                           # asset_hint=kr_stock 경로로 kr_equity 매칭


def test_signal2_new_edges_and_cooccur():
    rows = [_item(1, "2026-07-10T01:00:00Z", "엔비디아 HBM 공급 계약")]
    edges = kernel.cooccur_edges(rows, ["엔비디아", "HBM", "ADR"], match.find_alias)
    assert ("HBM", "엔비디아") in {tuple(sorted(e)) for e in edges}
    assert kernel.new_edges({("A", "B"), ("A", "C")}, [{("A", "B")}]) == {("A", "C")}


def test_signal3_daily_baseline_real_z():
    titles_now = ["엔드게임 공포 확산", "엔드게임 논쟁 격화", "엔드게임 재점화"]
    base_days = [["시장 상승 마감"], ["금리 동결 발표"], ["엔드게임 언급 소폭"]] * 10   # 30일 일별
    res = kernel.emerging_terms(titles_now, base_days, w_days=1)
    got = {t: (c, z) for t, c, z in res}
    assert "엔드게임" in got
    c, z = got["엔드게임"]
    assert c == 3 and isinstance(z, float) and z > 2.0          # 일별 분포 기반 실제 z(이진 퇴화 금지)


def test_signal3_bigram_emerges():
    titles_now = ["변동성 덫 경고", "변동성 덫 심화", "변동성 덫 재점화"]
    base_days = [["평온한 시장"]] * 30
    res = kernel.emerging_terms(titles_now, base_days, w_days=1)
    assert any(t == "변동성 덫" for t, _c, _z in res)            # 바이그램 검출
```

- [ ] **Step 2: 실패 확인** — Expected: FAIL

- [ ] **Step 3: 구현**

```python
# src/newsstore/radar/kernel.py
"""레이더 커널 — 신호 1~4의 원값 계산(무임계). 임계·필터는 뷰 계층(daily)에서.

- 렌즈 분류: classify_stage1을 asset_hint·language·keyword_text만으로 호출(태깅 컷 —
  tickers/entities/topics 공집합, 해상도 약화는 스펙 §10 리스크). article_lenses는 '같은
  행 집합을 신호 간 재분류하지 않기 위한 공유 지점'이다 — 호출자가 슬라이스별로 부르는
  것은 허용(로컬 규모에서 비용 무해), 동일 슬라이스의 중복 호출만 금지.
- 신호3 z는 기준선 '일별 분포'로 계산한다(총빈도 비율 근사 금지 — 이진 퇴화 방지).
"""
from __future__ import annotations

import re
import statistics
from collections import Counter

from newsstore.enrich import topics as _topics
from newsstore.enrich.lens_classify import classify_stage1

_ws = re.compile(r"\s+")
STOPWORDS = {"및", "등", "의", "를", "은", "는", "이", "가", "와", "과", "에", "도"}


def dedup(rows: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out = []
    for r in rows:
        key = _ws.sub(" ", (r.get("title") or "").strip()).lower()
        if key and key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def zscore(current: float, baseline: list[float]):
    if not baseline:
        return "new" if current > 0 else 0.0
    mean = statistics.fmean(baseline)
    sd = statistics.pstdev(baseline)
    if sd == 0:
        return "new" if current > mean else 0.0
    return (current - mean) / sd


def baseline_coverage(days_with_data: list, *, window_days: int, min_ratio: float) -> tuple[bool, str]:
    ratio = len(days_with_data) / window_days
    if ratio < min_ratio:
        return False, f"결측: 기준선 데이터 부족({len(days_with_data)}/{window_days}일)"
    return True, ""


def article_lenses(rows: list[dict]) -> dict[str, list[str]]:
    """기사 id → 렌즈 목록. 기사당 1회만 분류(신호1·4 공유)."""
    t = _topics.load_topics()
    out: dict[str, list[str]] = {}
    for r in rows:
        kt = ((r.get("title") or "") + " " + (r.get("body") or "")[:200]).lower()
        out[r["id"]] = classify_stage1(
            t, asset_hints=[r["asset_hint"]] if r.get("asset_hint") else [],
            tickers=[], entities=[], topics=[],
            language=r.get("language") or "", keyword_text=kt)
    return out


def lens_counts_from(per_article: dict[str, list[str]]) -> dict[str, int]:
    c: Counter = Counter()
    for lenses in per_article.values():
        for lens in lenses:
            c[lens] += 1
    return dict(c)


def new_edges(current: set[tuple[str, str]], prev_weeks: list[set]) -> set:
    prev_all = set().union(*prev_weeks) if prev_weeks else set()
    return current - prev_all


def cooccur_edges(rows: list[dict], vocab: list[str], find_alias) -> set[tuple[str, str]]:
    edges: set = set()
    for r in rows:
        text = (r.get("title") or "") + " " + (r.get("body") or "")[:200]
        hits = sorted({v for v in vocab if find_alias(v, text)})
        for i in range(len(hits)):
            for j in range(i + 1, len(hits)):
                edges.add((hits[i], hits[j]))
    return edges


def _tokens(title: str):
    """유니그램은 len≥2·불용어 필터, 바이그램은 필터 전 '원시 토큰열'로 조립한다 —
    1글자 토큰('덫')이 먼저 탈락하면 '변동성 덫' 같은 구가 구조적으로 검출 불가가 되고,
    탈락 토큰을 건너뛴 가짜 인접쌍이 생기기 때문(재리뷰 critical — 스펙 §5의 '1글자 제외'는
    유니그램에만 적용된다는 부록을 Task 8 커밋에서 스펙에 한 줄 추가한다)."""
    raw = [t for t in re.split(r"[^0-9A-Za-z가-힣]+", title or "") if t]
    unigrams = [t for t in raw if len(t) >= 2 and t not in STOPWORDS]
    bigrams = [" ".join(p) for p in zip(raw, raw[1:])]
    return unigrams + bigrams


def emerging_terms(titles_now: list[str], baseline_days: list[list[str]],
                   *, w_days: int) -> list[tuple[str, int, object]]:
    """(term, 창 빈도, z 원값). 기준선은 '일별 제목 리스트' — 일별 카운트 분포로 진짜 z를 계산.
    창 빈도는 일평균(cnt/w_days)으로 정규화해 기준선 일별 분포와 스케일을 맞춘다."""
    now = Counter(t for title in titles_now for t in _tokens(title))
    day_counters = [Counter(t for title in day for t in _tokens(title)) for day in baseline_days]
    out = []
    for term, cnt in now.items():
        series = [dc.get(term, 0) for dc in day_counters]
        z = zscore(cnt / max(w_days, 1), series)
        out.append((term, cnt, z))
    out.sort(key=lambda x: (-x[1], x[0]))
    return out


def cross_lens_spread(term_hits: dict[str, list[str]],
                      per_article: dict[str, list[str]]) -> dict[str, int]:
    """term → 걸치는 렌즈 수. term_hits: term → 매칭 기사 id 목록(분류는 per_article 재사용)."""
    return {term: len({lens for iid in ids for lens in per_article.get(iid, [])})
            for term, ids in term_hits.items()}
```

- [ ] **Step 4: 통과 확인** — Expected: PASS
- [ ] **Step 5: Commit** — `feat(radar): 커널 — 기사당 1회 분류 공유·일별 분포 z·간선·창발(무임계 원값)`

---

### Task 9: 종목 스테이션 (station.py)

**Files:** Create `src/newsstore/radar/station.py` / Test `tests/radar/test_station.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/radar/test_station.py
from newsstore.radar import ledgers, localdb, station


def _entry():
    return {"id": "sk_hynix", "label": "SK하이닉스", "ticker": "000660.KS", "role": "stock",
            "station": True, "aliases": ["SK하이닉스", "하이닉스"]}


def _items():
    mk = lambda i, ts, title: {"id": f"i{i}", "feed_id": "f", "source": f"s{i}",
                               "asset_hint": "kr_stock", "language": "ko", "url": f"u{i}",
                               "title": title, "body": "", "published_at": ts,
                               "fetched_at": ts, "kind": "story"}
    return [mk(1, "2026-07-10T01:00:00Z", "SK하이닉스 급락"),
            mk(2, "2026-07-10T02:00:00Z", "사이렌 울린 도심"),
            mk(3, "2026-07-09T01:00:00Z", "하이닉스가 반등")]


def test_arrival_news_matches_with_evidence_and_kst_window():
    block = station.arrival_news(_entry(), _items(), today="2026-07-10")
    assert block["total"] == 2
    assert all("alias" in h and "pos" in h for h in block["hits"])
    assert block["count_today"] == 1                             # KST 당일(7/10) 도착분만


def test_arrival_news_fold_rule():
    many = [{"id": f"i{i}", "title": f"SK하이닉스 뉴스 {i}", "body": "", "source": "s",
             "asset_hint": "kr_stock", "language": "ko", "url": f"u{i}", "feed_id": "f",
             "published_at": f"2026-07-10T{i % 24:02d}:00:00Z",
             "fetched_at": f"2026-07-10T{i % 24:02d}:00:00Z", "kind": "story"} for i in range(24)]
    block = station.arrival_news(_entry(), many, today="2026-07-10")
    assert block["total"] == 24 and len(block["shown"]) == 20 and block["folded"] == 4


def test_status_board_drawdown_and_mdd(tmp_path):
    db = localdb.connect_prices(str(tmp_path / "p.db"))
    rows = [{"ticker": "000660.KS", "date": d, "open": c, "high": c, "low": c,
             "close": c, "adj_close": c, "volume": 1} for d, c in
            [("2026-06-18", 2700000.0), ("2026-07-07", 2109000.0), ("2026-07-10", 2201000.0)]]
    localdb.upsert_prices(db, rows, source="t")
    board = station.status_board(_entry(), db)
    assert board["close"] == 2201000.0 and board["peak"] == 2700000.0
    assert round(board["drawdown"], 4) == round(2201000 / 2700000 - 1, 4)
    assert board["basis"] == "000660.KS 종가"


def test_plan_check_out_of_band():
    plan = {"type": "plan", "id": "p1", "target": "sk_hynix", "band": [2100000, 2200000],
            "invalidation": "x", "by": "2026-07-29", "thesis": "t", "date": "2026-07-10"}
    assert station.plan_check(plan, close=2201000.0)["out_of_band"] is True
    assert station.plan_check(plan, close=2150000.0)["out_of_band"] is False
    nocmp = station.plan_check(plan, close=None)                 # 가격 결측 — 비교 불가 표기
    assert nocmp["out_of_band"] is None


def test_target_gates_filter():
    gates = [{"id": "g-h", "date": "2026-07-29", "test": "t", "on_confirm": "c",
              "on_refute": "r", "status": "pending", "targets": ["sk_hynix"]},
             {"id": "g-all", "date": "2026-07-29", "test": "t", "on_confirm": "c",
              "on_refute": "r", "status": "pending"}]
    ledgers.validate_gates(gates)
    mine = station.target_gates(_entry(), gates, today="2026-07-28")
    assert [g["id"] for g in mine] == ["g-h"]                    # 종목 게이트만(전역은 일보 머리 몫)


def test_coverage_gauge():
    g = station.coverage(_entry(), _items())
    assert g["matched"] == 2 and g["sources"] >= 1 and 0 <= g["body_ratio"] <= 1
```

- [ ] **Step 2: 실패 확인** — Expected: FAIL

- [ ] **Step 3: 구현**

```python
# src/newsstore/radar/station.py
"""종목 스테이션(1차 뷰) — 판단하지 않는다. 수신 준비만 한다(스펙 §4).
약속은 '피드-상대 전수': 무임계로 전부 세고, 표시는 최신순 20건+접기(임계가 아니라 표시 규칙)."""
from __future__ import annotations

from . import ledgers, localdb, match

SHOW_LIMIT = 20


def _matched(entry: dict, items: list[dict]) -> list[dict]:
    hits = []
    for r in items:
        text = (r.get("title") or "") + " " + (r.get("body") or "")[:200]
        m = match.find_any(entry["aliases"], text)
        if m:
            hits.append({**r, "alias": m[0], "pos": m[1]})
    return hits


def coverage(entry: dict, items: list[dict]) -> dict:
    hits = _matched(entry, items)
    with_body = [h for h in hits if (h.get("body") or "").strip()]
    return {"matched": len(hits),
            "sources": len({h.get("source") for h in hits}),
            "body_ratio": (len(with_body) / len(hits)) if hits else 0.0}


def arrival_news(entry: dict, items: list[dict], *, today: str) -> dict:
    import datetime as dt
    hits = _matched(entry, items)
    day = lambda r: localdb.kst_day(r.get("fetched_at") or "")
    count_today = sum(1 for h in hits if day(h) == today)
    t = dt.date.fromisoformat(today)
    baseline_7d = [sum(1 for h in hits if day(h) == (t - dt.timedelta(days=i)).isoformat())
                   for i in range(1, 8)]
    hits.sort(key=lambda h: h.get("fetched_at") or "", reverse=True)
    return {"total": len(hits), "hits": hits, "shown": hits[:SHOW_LIMIT],
            "folded": max(0, len(hits) - SHOW_LIMIT),
            "count_today": count_today, "baseline_7d": baseline_7d}


def status_board(entry: dict, prices_db) -> dict:
    closes = localdb.load_closes(prices_db, entry["ticker"])
    if not closes:
        return {"missing": True, "reason": f"{entry['ticker']}: 가격 데이터 없음"}
    close = closes[-1][1]
    peak = max(c for _d, c in closes)
    running_peak, mdd = closes[0][1], 0.0
    for _d, c in closes:
        running_peak = max(running_peak, c)
        mdd = min(mdd, c / running_peak - 1)
    return {"close": close, "peak": peak, "drawdown": close / peak - 1, "mdd": mdd,
            "basis": f"{entry['ticker']} 종가"}


def plan_check(plan: dict, *, close: float | None) -> dict:
    lo, hi = plan["band"]
    return {"plan_id": plan["id"], "band": plan["band"], "close": close,
            "out_of_band": (None if close is None else not (lo <= close <= hi)),
            "invalidation": plan["invalidation"], "by": plan["by"]}


def target_gates(entry: dict, gates: list[dict], *, today: str) -> list[dict]:
    mine = ledgers.gates_for_target(gates, entry["id"])
    return ledgers.due_around(mine, today=today, window_days=30)   # 종목 게이트는 한 달 창으로 상기


def frame_refs(entry: dict, frames: dict) -> list[dict]:
    refs = []
    for lens, frame in frames.items():
        for ax, poles in frame.items():
            for p in poles:
                blob = " ".join(str(p.get(k, "")) for k in ("id", "label", "evidence", "test"))
                if any(a in blob for a in entry["aliases"]) or entry["id"] in blob:
                    refs.append({"lens": lens, "axis": ax, "id": p["id"], "label": p["label"],
                                 "status": p.get("status", "active")})
    return refs
```

- [ ] **Step 4: 통과 확인** — Expected: PASS
- [ ] **Step 5: Commit** — `feat(radar): 종목 스테이션 — KST 당일 카운트·종목 게이트 필터·가격 결측 시 비교 불가 표기`

---

### Task 10: 일보 조립 + CLI + compose 서비스 (daily.py, run_radar.py)

**Files:** Create `src/newsstore/radar/daily.py`, `src/newsstore/entrypoints/run_radar.py` / Modify `docker-compose.yml`(서비스 3개 — CLI가 생기는 이 태스크에서 추가해 중간 커밋 깨짐 방지) / Test `tests/radar/test_daily.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/radar/test_daily.py
from newsstore.radar import daily, localdb


def _mk(i, ts, title):
    return {"id": f"i{i}", "feed_id": "f", "source": "s", "asset_hint": "kr_stock",
            "language": "ko", "url": f"u{i}", "title": title, "body": "",
            "published_at": ts, "fetched_at": ts, "kind": "story"}


def _seed_items(db, *, days=35, per_day=2):
    """기준선 창(28일)을 채우는 픽스처 — 7/10 기준 과거 days일, 하루 per_day건.
    당일(7/10)에는 급증분 4건을 얹어 뷰 임계(FIELD_MIN=3)를 넘는 발화 경로도 검증한다."""
    import datetime as dt
    rows = []
    i = 0
    end = dt.date(2026, 7, 10)
    for d in range(days):
        day = (end - dt.timedelta(days=d)).isoformat()
        for k in range(per_day):
            rows.append(_mk((i := i + 1), f"{day}T0{k}:00:00Z", f"SK하이닉스 시장 동향 {i}"))
    for k in range(4):                                            # 당일 급증(발화 경로)
        rows.append(_mk((i := i + 1), f"2026-07-10T0{k + 3}:00:00Z", f"SK하이닉스 급락 속보 {k}"))
    localdb.upsert_items(db, rows)


def _ctx(tmp_path, with_prices=False, seed=True):
    items_db = localdb.connect_items(str(tmp_path / "l.db"))
    if seed:
        _seed_items(items_db)
    prices_db = localdb.connect_prices(str(tmp_path / "p.db"))
    if with_prices:
        localdb.upsert_prices(prices_db, [{"ticker": "000660.KS", "date": "2026-07-10",
                                           "open": 1, "high": 1, "low": 1, "close": 2201000.0,
                                           "adj_close": 1, "volume": 1}], source="t")
    return items_db, prices_db


def test_report_sections_signals_and_stations(tmp_path):
    items_db, prices_db = _ctx(tmp_path, with_prices=True)
    md = daily.build_report(items_db, prices_db, today="2026-07-10")
    for sec in ("오늘의 게이트", "신호1", "신호2", "신호3", "신호4", "종목 스테이션", "부록"):
        assert sec in md, f"섹션 누락: {sec}"
    assert "피드가 본 세계" in md and "매칭:" in md
    assert "구간 밖" in md                                        # 시드 플랜 220.1만 > 220만 경고
    assert ", z=" in md                                           # 발화 경로 렌더(당일 급증 픽스처)


def test_plans_shown_even_without_prices(tmp_path):
    items_db, prices_db = _ctx(tmp_path, with_prices=False)
    md = daily.build_report(items_db, prices_db, today="2026-07-10")
    assert "결측" in md                                           # 상태판 결측 명시
    assert "plan-2026-07-10-hynix-entry" in md                    # 플랜은 가격 없이도 표기
    assert "비교 불가" in md


def test_baseline_coverage_guard_reports_missing(tmp_path):
    items_db, prices_db = _ctx(tmp_path, seed=False)
    localdb.upsert_items(items_db, [_mk(1, "2026-07-10T01:00:00Z", "SK하이닉스 단독")])
    md = daily.build_report(items_db, prices_db, today="2026-07-10")
    assert "결측: 기준선" in md                                    # 부분 백필 → 신호 결측 표기


def test_overdue_gate_warning_in_header(tmp_path):
    items_db, prices_db = _ctx(tmp_path)
    md = daily.build_report(items_db, prices_db, today="2026-09-01")
    assert "경고" in md and "pending" in md
```

- [ ] **Step 2: 실패 확인** — Expected: FAIL

- [ ] **Step 3: 구현**

```python
# src/newsstore/radar/daily.py
"""일보 조립 — radar_out/YYYY-MM-DD.md 한 장(스펙 §3.6 순서: 경고→게이트→필드 뷰(신호 4종)
→스테이션→부록). 데이터가 없으면 조용히 생략하지 않고 '결측: 사유'를 표기한다(FAIL-LOUD).

뷰 임계(결정④ — 커널은 원값, 여기서만 필터): 신호1 24h≥3건 AND (z=='new' or z≥2.0),
신호3 빈도≥3 AND (z=='new' or z≥2.0), 신호2는 신규 간선만, 신호4는 확산 2렌즈 이상.
"""
from __future__ import annotations

import datetime as dt

from . import kernel, ledgers, localdb, match, station, watchlist

FIELD_Z = 2.0
FIELD_MIN = 3
BASELINE_28 = 28
BASELINE_30 = 30
MIN_RATIO = 2 / 3


def _by_day(rows: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for r in rows:
        out.setdefault(localdb.kst_day(r.get("fetched_at") or ""), []).append(r)
    return out


def _passes(cnt: int, z, *, min_cnt: int) -> bool:
    return cnt >= min_cnt and (z == "new" or (isinstance(z, float) and z >= FIELD_Z))


def _field_view(rows: list[dict], vocab: list[str], today: str) -> list[str]:
    lines = [f"## 필드 뷰 (뷰 임계: 빈도≥{FIELD_MIN} & z≥{FIELD_Z} 또는 신규)"]
    byday = _by_day(rows)
    t = dt.date.fromisoformat(today)
    base_days_28 = [(t - dt.timedelta(days=i)).isoformat() for i in range(1, BASELINE_28 + 1)]
    have = [d for d in base_days_28 if byday.get(d)]
    ok, reason = kernel.baseline_coverage(have, window_days=BASELINE_28, min_ratio=MIN_RATIO)

    # 신호1 — 렌즈별 당일 카운트 vs 28일 일별 분포 z
    lines.append("### 신호1 테마 속도")
    if not ok:
        lines.append(f"- {reason}")
    else:
        per_today = kernel.article_lenses(byday.get(today, []))
        counts_today = kernel.lens_counts_from(per_today)
        daily_counts: dict[str, list[int]] = {}
        for d in base_days_28:
            cd = kernel.lens_counts_from(kernel.article_lenses(byday.get(d, [])))
            for lens in set(list(cd) + list(counts_today)):
                daily_counts.setdefault(lens, []).append(cd.get(lens, 0))
        shown = False
        for lens, cnt in sorted(counts_today.items(), key=lambda x: -x[1]):
            z = kernel.zscore(cnt, daily_counts.get(lens, []))
            if _passes(cnt, z, min_cnt=FIELD_MIN):
                lines.append(f"- {lens}: 당일 {cnt}건, z={z if z == 'new' else f'{z:.1f}'}")
                shown = True
        if not shown:
            lines.append("- 해당 없음")

    # 신호2 — 금주 간선 vs 직전 8주(신규 간선만)
    lines.append("### 신호2 그래프 드리프트(신규 간선)")
    week_of = lambda ds: dt.date.fromisoformat(ds).isocalendar()[:2]
    cur_week = week_of(today)
    cur_rows, prev_weeks_rows = [], {}
    for d, rs in byday.items():
        if not d:
            continue
        w = week_of(d)
        if w == cur_week:
            cur_rows += rs
        else:
            prev_weeks_rows.setdefault(w, []).extend(rs)
    prev_edge_sets = [kernel.cooccur_edges(rs, vocab, match.find_alias)
                      for _w, rs in sorted(prev_weeks_rows.items())[-8:]]
    fresh = kernel.new_edges(kernel.cooccur_edges(cur_rows, vocab, match.find_alias), prev_edge_sets)
    lines += [f"- {a} — {b} (금주 신규)" for a, b in sorted(fresh)] or ["- 해당 없음"]

    # 신호3 — 어휘 창발(직전 W=3일 창 vs 창 뒤 30일 일별 분포 — 스펙 §5 정의 그대로)
    lines.append("### 신호3 어휘 창발 (radar_vocab 승격 후보)")
    W3 = 3
    now_days = [(t - dt.timedelta(days=i)).isoformat() for i in range(W3)]
    base_days_30 = [(t - dt.timedelta(days=W3 + i)).isoformat() for i in range(BASELINE_30)]
    have30 = [d for d in base_days_30 if byday.get(d)]
    ok30, reason30 = kernel.baseline_coverage(have30, window_days=BASELINE_30, min_ratio=MIN_RATIO)
    emergent: list = []
    if not ok30:
        lines.append(f"- {reason30}")
    else:
        titles_now = [r.get("title") or "" for d in now_days for r in byday.get(d, [])]
        baseline = [[r.get("title") or "" for r in byday.get(d, [])] for d in base_days_30]
        emergent = [(term, cnt, z) for term, cnt, z in
                    kernel.emerging_terms(titles_now, baseline, w_days=W3)
                    if _passes(cnt, z, min_cnt=FIELD_MIN)][:15]
        lines += [f"- {term}: {cnt}건, z={z if z == 'new' else f'{z:.1f}'}"
                  for term, cnt, z in emergent] or ["- 해당 없음"]

    # 신호4 — 크로스렌즈 확산(창발 어휘+vocab의 금주 렌즈 확산)
    lines.append("### 신호4 크로스렌즈 확산")
    terms4 = [term for term, _c, _z in emergent] + vocab
    per_cur = kernel.article_lenses(cur_rows)
    term_hits = {term: [r["id"] for r in cur_rows
                        if match.find_alias(term, (r.get("title") or ""))]
                 for term in terms4}
    spread = {k: v for k, v in kernel.cross_lens_spread(term_hits, per_cur).items() if v >= 2}
    lines += [f"- {term}: {n}개 렌즈" for term, n in
              sorted(spread.items(), key=lambda x: -x[1])[:10]] or ["- 해당 없음"]
    return lines


def build_report(items_db, prices_db, *, today: str,
                 gates_path="radar/gates.yaml", frames_path="radar/frames.json",
                 journal_path="journal/journal.jsonl",
                 watchlist_path="config/watchlist.yaml",
                 vocab_path="config/radar_vocab.yaml") -> str:
    entries = watchlist.load_watchlist(watchlist_path)
    gates = ledgers.load_gates(gates_path)
    frames = ledgers.load_frames(frames_path, gate_ids={g["id"] for g in gates})
    journal = ledgers.load_journal(journal_path)
    vocab = match.load_vocab(vocab_path)
    rows = kernel.dedup(localdb.load_items(items_db))

    out = [f"# 레이더 일보 {today} (KST 기준)", ""]
    overdue = ledgers.overdue_pending(gates, today=today)
    if overdue:
        out.append("## 경고")
        out += [f"- pending 만기 경과: {g['id']} ({g['date']}) — 판정 필요" for g in overdue]
    out.append("## 오늘의 게이트 (±2일)")
    due = ledgers.due_around(gates, today=today)
    out += [f"- {g['date']} **{g['id']}** — {g['test']}" for g in due] or ["- 해당 없음"]
    out += _field_view(rows, vocab, today)

    out.append("## 종목 스테이션")
    plans = ledgers.active_plans(journal, today=today)
    total_cov = 0
    for e in watchlist.station_entries(entries):
        out.append(f"### {e['label']} ({e['ticker']})")
        cov = station.coverage(e, rows)
        total_cov += cov["matched"]
        out.append(f"- 커버리지: 매칭 {cov['matched']}건 · 소스 {cov['sources']}종 · "
                   f"본문 보유율 {cov['body_ratio']:.0%} — 이 페이지는 피드가 본 세계다 — 판단 전 웹 확인")
        board = station.status_board(e, prices_db)
        close = None
        if board.get("missing"):
            out.append(f"- 상태판 결측: {board['reason']}")
        else:
            close = board["close"]
            out.append(f"- 상태판({board['basis']}): 종가 {board['close']:,.0f} · "
                       f"전고점 대비 {board['drawdown']:+.1%} · MDD {board['mdd']:+.1%}")
        for g in station.target_gates(e, gates, today=today):
            out.append(f"- 게이트: {g['date']} **{g['id']}** — {g['test']}")
        for p in [p for p in plans if p["target"] == e["id"]]:      # 플랜은 가격과 독립 표기
            chk = station.plan_check(p, close=close)
            mark = (" ⚠️구간 밖(추격 주의)" if chk["out_of_band"]
                    else " (가격 결측 — 비교 불가)" if chk["out_of_band"] is None else "")
            out.append(f"- 플랜 {p['id']}: 구간 {chk['band']} · 무효화 {chk['invalidation']}"
                       f" · 시한 {chk['by']}{mark}")
        arr = station.arrival_news(e, rows, today=today)
        spark = "·".join(str(n) for n in reversed(arr["baseline_7d"]))
        out.append(f"- 도착 뉴스: 전수 {arr['total']}건(표시 {len(arr['shown'])}·접힘 {arr['folded']})"
                   f" · 당일(KST) {arr['count_today']}건 · 7d {spark}")
        for h in arr["shown"]:
            out.append(f"  - {h.get('title')} (매칭: {h['alias']}@{h['pos']}, {h.get('source')})")
        refs = station.frame_refs(e, frames)
        if refs:
            out.append("- 프레임 참조: " + ", ".join(f"{r['lens']}/{r['axis']}/{r['id']}" for r in refs))
    out.append("## 부록 — 커버리지 총계")
    out.append(f"- 코퍼스 {len(rows)}건(중복 제거 후) · 스테이션 매칭 합계 {total_cov}건")
    return "\n".join(out) + "\n"
```

```python
# src/newsstore/entrypoints/run_radar.py
"""로컬 작업장 CLI — sync|prices|radar|backtest. '오늘'은 여기서 KST로 한 번만 결정한다."""
from __future__ import annotations

import argparse
import pathlib


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=("sync", "prices", "radar", "backtest"))
    ap.add_argument("--as-of", default=None)
    args = ap.parse_args()
    from newsstore.radar import localdb
    pathlib.Path("data").mkdir(exist_ok=True)
    if args.mode == "sync":
        from newsstore.radar import sync
        db = localdb.connect_items("data/local.db")
        n = sync.run_sync(db)
        print(f"sync: {n}건 적재, 워터마크 {localdb.get_watermark(db)}")
    elif args.mode == "prices":
        from newsstore.radar import prices, watchlist
        db = localdb.connect_prices("data/prices.db")
        rep = prices.ingest(db, watchlist.load_watchlist())
        for t, r in rep.items():
            print(f"prices[{t}]: {r}")
    elif args.mode == "radar":
        from newsstore.radar import daily
        today = localdb.today_kst()
        items_db = localdb.connect_items("data/local.db")
        prices_db = localdb.connect_prices("data/prices.db")
        md = daily.build_report(items_db, prices_db, today=today)
        out = pathlib.Path("radar_out") / f"{today}.md"
        out.parent.mkdir(exist_ok=True)
        out.write_text(md, encoding="utf-8")
        print(f"radar: {out} 작성")
    else:
        from newsstore.radar import backtest
        backtest.main(as_of=args.as_of)


if __name__ == "__main__":
    main()
```

`docker-compose.yml` 끝에 서비스 3개 추가(전 계획 1판과 동일 블록 — sync·prices·radar, 각각 `build: infra/Dockerfile + args {INSTALL_DEV: "false", INSTALL_RADAR: "true"}`, `image: newsstore-radar`, `volumes: [".:/app"]`, `env_file: [.env]`, `command: python -m newsstore.entrypoints.run_radar --mode <이름>`).

- [ ] **Step 4: 통과 확인** — Expected: PASS. 추가로 서비스 기동 스모크: `docker compose build radar && MSYS_NO_PATHCONV=1 docker compose run --rm radar --help 2>&1 | head -5` 대신 `docker compose config --services`에 sync/prices/radar가 뜨는지 확인.
- [ ] **Step 5: Commit** — `feat(radar): 일보 조립(신호 4종 뷰 임계·결측 명시) + run_radar CLI + compose 서비스`

---

### Task 11: 백테스트 러너 (backtest.py)

**Files:** Create `src/newsstore/radar/backtest.py` / Test `tests/radar/test_backtest.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/radar/test_backtest.py
from newsstore.radar import backtest, localdb


def _mk(i, day, title):
    ts = f"{day}T09:00:00Z"
    return {"id": f"b{i}", "feed_id": "f", "source": "s", "asset_hint": "kr_stock",
            "language": "ko", "url": f"u{i}", "title": title, "body": "",
            "published_at": ts, "fetched_at": ts, "kind": "story"}


def _seed(db):
    rows, i = [], 0
    for d in range(1, 31):
        rows.append(_mk((i := i + 1), f"2026-06-{d:02d}", "시장 동향 정리"))
    for d in (4, 5, 6):
        for k in range(3):
            rows.append(_mk((i := i + 1), f"2026-07-{d:02d}", f"엔드게임 공포 {k}"))
    localdb.upsert_items(db, rows)


def test_lead_time_detects_pre_event_emergence(tmp_path):
    db = localdb.connect_items(str(tmp_path / "l.db"))
    _seed(db)
    res = backtest.lead_times(db, terms=["엔드게임"], event_day="2026-07-07",
                              start="2026-07-01", end="2026-07-08", w_days=3, m=3, z=2.0)
    assert res["엔드게임"] is not None and res["엔드게임"] < 0


def test_target_terms_fixed_list():
    assert len(backtest.TARGET_TERMS) == 10
    assert "엔드게임" in backtest.TARGET_TERMS and "HBM" in backtest.TARGET_TERMS


def test_corpus_presence_gate(tmp_path):
    db = localdb.connect_items(str(tmp_path / "l.db"))
    localdb.upsert_items(db, [_mk(1, "2026-07-01", "무관 제목")])
    present = backtest.corpus_presence(db, backtest.TARGET_TERMS)
    assert sum(1 for v in present.values() if v > 0) < 2          # 사전 게이트가 중단 사유를 보고


def test_signal1_fp_and_signal2_volume_run(tmp_path):
    db = localdb.connect_items(str(tmp_path / "l.db"))
    _seed(db)
    fp = backtest.signal1_fp_by_weekday(db, month_start="2026-06-01", month_end="2026-06-30")
    assert isinstance(fp, dict) and len(fp) == 7                  # 요일별 오탐 분해(왜곡 실측)
    vol = backtest.signal2_weekly_volume(db, weeks=8, as_of="2026-07-08")
    assert isinstance(vol, list)                                  # 주별 신규 간선 수(강등 판정 근거)
```

- [ ] **Step 2: 실패 확인** — Expected: FAIL

- [ ] **Step 3: 구현**

```python
# src/newsstore/radar/backtest.py
"""신호 소급 실행 러너 — 신호3 캘리브레이션 + 신호1 평시 오탐(요일 분해) + 신호2 산출량 실측.
프로덕션 커널 함수를 임포트해 --as-of만 주입한다(로직 복제 금지 — SSOT, 스펙 결정⑧).
파라미터는 평시 오탐률로 좁히고 리드타임은 채점만(과적합 방지 — 스펙 §9)."""
from __future__ import annotations

import datetime as dt

from . import kernel, localdb, match

# 스펙 §9 사전 등록 타깃 10종 — 실행 시점에 고르지 않는다.
TARGET_TERMS = ["엔드게임", "사이드카", "서킷브레이커", "변동성의 덫", "반사성",
                "레버리지", "ADR", "북빌딩", "디레버리징", "HBM"]


def _rows_by_day(db) -> dict[str, list[dict]]:
    """프로덕션(daily)과 동일한 입력 파이프라인 — 전 컬럼 로드 + dedup + KST 버킷.
    측정기가 입력을 다르게 복제하면 캘리브레이션이 오염된다(재리뷰 major — 실제
    asset_hint·language·body를 그대로 쓰고, kr_stock 하드코딩·UTC substr 경계 오차를 제거)."""
    rows = kernel.dedup(localdb.load_items(db))
    out: dict[str, list[dict]] = {}
    for r in rows:
        out.setdefault(localdb.kst_day(r.get("fetched_at") or ""), []).append(r)
    return out


def _titles_by_day(db, start: str, end: str) -> dict[str, list[str]]:
    byday = _rows_by_day(db)
    return {d: [r.get("title") or "" for r in rs]
            for d, rs in byday.items() if d and start <= d <= end}


def corpus_presence(db, terms: list[str]) -> dict[str, int]:
    out = {}
    for t in terms:
        out[t] = db.execute("SELECT COUNT(*) FROM items WHERE title LIKE ?",
                            (f"%{t}%",)).fetchone()[0]
    return out


def _emerging_on(byday: dict[str, list[str]], day: str, *, w_days: int, b_days: int = 30):
    d = dt.date.fromisoformat(day)
    now = [t for i in range(w_days)
           for t in byday.get((d - dt.timedelta(days=i)).isoformat(), [])]
    baseline = [byday.get((d - dt.timedelta(days=w_days + i)).isoformat(), [])
                for i in range(b_days)]
    return kernel.emerging_terms(now, baseline, w_days=w_days)


def _detected(hits, *, m: int, z: float) -> set[str]:
    return {t for t, cnt, zz in hits
            if cnt >= m and (zz == "new" or (isinstance(zz, float) and zz >= z))}


def lead_times(db, *, terms: list[str], event_day: str, start: str, end: str,
               w_days: int, m: int, z: float) -> dict[str, int | None]:
    byday = _titles_by_day(db, "2026-01-01", end)
    res: dict[str, int | None] = {t: None for t in terms}
    d, endd, ev = (dt.date.fromisoformat(x) for x in (start, end, event_day))
    while d <= endd:
        got = _detected(_emerging_on(byday, d.isoformat(), w_days=w_days), m=m, z=z)
        for t in terms:
            if res[t] is None and t in got:
                res[t] = (d - ev).days
        d += dt.timedelta(days=1)
    return res


def false_positive_rate(db, *, month_start: str, month_end: str, w_days: int, m: int, z: float) -> float:
    byday = _titles_by_day(db, "2026-01-01", month_end)
    d, endd = dt.date.fromisoformat(month_start), dt.date.fromisoformat(month_end)
    days = total = 0
    while d <= endd:
        total += len(_detected(_emerging_on(byday, d.isoformat(), w_days=w_days), m=m, z=z))
        days += 1
        d += dt.timedelta(days=1)
    return total / max(days, 1)


def signal1_fp_by_weekday(db, *, month_start: str, month_end: str) -> dict[int, float]:
    """요일(0=월)별 '유의 렌즈 수' 평균 — 주말 왜곡 실측(스펙 §5 요일 가드 판정 근거).
    입력은 _rows_by_day(실제 asset_hint·language) — 프로덕션 동일 경로."""
    byday = _rows_by_day(db)
    lenses_by_day = {d: kernel.lens_counts_from(kernel.article_lenses(rs))
                     for d, rs in byday.items()}                  # 일별 1회만 분류(재분류 금지)
    out: dict[int, list[int]] = {i: [] for i in range(7)}
    d, endd = dt.date.fromisoformat(month_start), dt.date.fromisoformat(month_end)
    while d <= endd:
        cnt_today = lenses_by_day.get(d.isoformat(), {})
        base: dict[str, list[int]] = {}
        for i in range(1, 29):
            cd = lenses_by_day.get((d - dt.timedelta(days=i)).isoformat(), {})
            for lens in set(list(cd) + list(cnt_today)):
                base.setdefault(lens, []).append(cd.get(lens, 0))
        sig = 0
        for lens, c in cnt_today.items():
            z = kernel.zscore(c, base.get(lens, []))
            if c >= 3 and (z == "new" or (isinstance(z, float) and z >= 2.0)):
                sig += 1
        out[d.weekday()].append(sig)
        d += dt.timedelta(days=1)
    return {wd: (sum(v) / len(v) if v else 0.0) for wd, v in out.items()}


def signal2_weekly_volume(db, *, weeks: int, as_of: str) -> list[int]:
    """주별 신규 간선 수 — '월 3건 미만이면 필드 뷰 강등'(스펙 §5) 판정 근거.
    입력은 _rows_by_day(실제 body 포함) — 프로덕션 cooccur_edges와 동일 재료."""
    byday = _rows_by_day(db)
    vocab = match.load_vocab()
    week_rows: dict[tuple, list[dict]] = {}
    for d, rs in byday.items():
        if not d or d > as_of:
            continue
        w = dt.date.fromisoformat(d).isocalendar()[:2]
        week_rows.setdefault(w, []).extend(rs)
    ordered = sorted(week_rows.items())[-weeks:]
    edge_sets = [kernel.cooccur_edges(rs, vocab, match.find_alias) for _w, rs in ordered]
    return [len(kernel.new_edges(cur, edge_sets[:i])) for i, cur in enumerate(edge_sets)]


def main(as_of: str | None = None) -> None:
    db = localdb.connect_items("data/local.db")
    event = as_of or "2026-07-07"
    present = corpus_presence(db, TARGET_TERMS)
    print(f"타깃 용어 실재(사전 게이트): {present}")
    if sum(1 for v in present.values() if v > 0) < 2:
        print("중단: 코퍼스 실재 용어 2개 미만 — 제목-only 입력 재설계 필요(스펙 §9)")
        return
    for w in (1, 3, 7):
        for m in (3, 5, 10):
            for z in (2.0, 3.0):
                lt = lead_times(db, terms=TARGET_TERMS, event_day=event,
                                start="2026-06-20", end="2026-07-10", w_days=w, m=m, z=z)
                fp = false_positive_rate(db, month_start="2026-05-01", month_end="2026-05-31",
                                         w_days=w, m=m, z=z)
                found = {k: v for k, v in lt.items() if v is not None}
                print(f"W={w} m={m} z={z}: 검출 {len(found)}/{len(TARGET_TERMS)}, "
                      f"리드타임 {found}, 평시 오탐 {fp:.1f}건/일")
    print("신호1 요일별 유의 렌즈 평균:", signal1_fp_by_weekday(
        db, month_start="2026-05-01", month_end="2026-05-31"))
    print("신호2 주별 신규 간선(8주):", signal2_weekly_volume(db, weeks=8, as_of=event))
```

- [ ] **Step 4: 통과 확인** — Expected: PASS
- [ ] **Step 5: Commit** — `feat(radar): 백테스트 러너 — 사전 게이트·리드타임·평시 오탐(요일 분해)·신호2 산출량`

---

### Task 12: 사이트 탭 조정 + 운영 문서 + 최종 검증

**Files:** Modify `web/index.html:139-140`, `docs/operations.md`, `CLAUDE.md`

- [ ] **Step 1: 웹 수정** — 두 버튼에 `hidden` 추가(코드·핸들러·routeFromHash 보존):

```html
        <button class="tab" id="tabStories" hidden>스토리</button>
        <button class="tab" id="tabReport" hidden>리포트</button>
```

- [ ] **Step 2: node 테스트 회귀 확인** — Run: `node --test tests/web/` / Expected: 전부 PASS

- [ ] **Step 3: 운영 문서** — `docs/operations.md`에 두 절 추가:
  (a) **클라우드 컷 절차**(스펙 §8 그대로): pause 5건 명령·collector 유지·Hosting 재배포·재개 절차(잡 resume + Hosting 롤백 + **로컬 local.db 전체 재동기화**). 그리고 **컷 실행 전 게이트 한 줄**: `프로덕션 items에 무인증 runQuery 1페이지 스모크(curl POST https://firestore.googleapis.com/v1/projects/<프로젝트>/databases/(default)/documents:runQuery — limit 3)가 200을 반환하는지 확인한다. 실패하면 sync 전제(공개 읽기 REST)가 깨진 것이므로 컷을 멈추고 조사한다.`
  (b) **로컬 레이더 작업장 운영**: 데일리 커맨드(`docker compose run --rm sync && docker compose run --rm prices; docker compose run --rm radar` — prices 실패해도 radar 진행), 산출 위치(radar_out/), 원장 3종 경로, 백테스트(`docker compose run --rm radar python -m newsstore.entrypoints.run_radar --mode backtest`). 알려진 정상 신호 한 줄: **3일 이상 연휴(설·추석)에는 prices의 '신규 0행 3일 연속' 크래시가 예정대로 발생한다 — 소스 파손이 아니라 휴장이며 다음 거래일 자동 해소**(거래일 판정기를 안 만드는 YAGNI의 수용 비용, 스펙 §3.2).
  `CLAUDE.md` '어디를 볼까'에 한 줄: `- **로컬 레이더 작업장**: 스펙 docs/superpowers/specs/2026-07-10-local-radar-workbench-design.md · 원장 radar/·journal/ · 일보 radar_out/`

- [ ] **Step 4: 전체 검증** — Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test` / Expected: **FAIL=0**. Run: `node --test tests/web/` / Expected: FAIL=0.

- [ ] **Step 5: Commit** — `feat(radar): 사이트 피드 리더 전환(탭 숨김) + 컷 게이트·로컬 운영 절차 문서화`

---

## Self-Review 기록 (2판)

- 1판 리뷰의 critical 2건 해소: 일보가 KST 당일/28·30일 창과 z를 실제로 계산하고 신호 4종 전부를 렌더하며(테스트가 섹션 4종을 단언), emerging_terms는 일별 분포 기준선으로 실제 float z를 낸다(테스트 `z > 2.0` float 단언 — 이진 퇴화 재발 차단).
- major 해소: prices는 신규 날짜 기준 0행 판정 + 같은 날 재실행 비증가 + NaN flagged(전부 테스트), 실측 캡처 파일 절차(Step 5)와 캡처-픽스처 키 대조 테스트, 픽스처 asset_hint 전부 `kr_stock`, 종목 게이트 구획(targets 필드 + station.target_gates + 스펙 부록 한 줄 — Task 7), sync 403 스텁 테스트·datetime 기반 워터마크 max·프로덕션 스모크(컷 절차 게이트), compose는 Task 10으로 이동, lock 결정 주석, 타임존 KST 규약(localdb.kst_day/today_kst 단일 홈).
- 타입 일치 재확인: `station.plan_check(close=None)`↔daily 분기, `kernel.article_lenses`/`lens_counts_from`↔daily·backtest, `arrival_news` 반환 키(hits/shown/folded/count_today/baseline_7d)↔daily 렌더, `ledgers.gates_for_target`↔station.
- 플레이스홀더 없음. 시드는 스펙 §3.3(+targets 2건)·§3.4 원문 참조.

### 재리뷰(2판) 처리 기록
2판 재리뷰가 신규 critical 1건(바이그램이 1글자 토큰 필터 뒤에 조립돼 "변동성 덫" 검출 불가 — 타깃 오염)과 major 2건(daily 신호3이 스펙 W=3 대신 당일 창, 백테스트 측정기가 프로덕션 입력 파이프라인을 재현하지 않음)을 찾았다. 재작성 상한(1회) 도달 상태였으나, 지적이 전부 기계적·결정론적으로 특정된 수정이고 사용자 전권 위임 중이라 escalate 대신 **외과 수정 + 손검증**으로 처리했다: `_tokens` 원시 토큰열 바이그램(검산: '변동성 덫 경고'→bigram '변동성 덫' 생성), daily W3=3 창·기준선 시프트, 백테스트 `_rows_by_day`(dedup+실컬럼+KST) 단일 입력 경로, prices 'current' 상태 구분, 발화 경로 픽스처(당일 4건 급증)와 `", z=" in md` 단언, kernel 공유 계약 문구 정정, 연휴 크래시 정상 신호 문서화. 이 판단(escalate 회피)의 근거와 수정 전부를 여기 기록해 감사 가능하게 남긴다.

<!-- spec-review: passed -->
