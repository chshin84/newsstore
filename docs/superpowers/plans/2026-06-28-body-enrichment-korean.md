# 본문 채우기 (한경 body 인리치) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 한경(헤드라인-only) 새 기사의 본문을 수집기 인라인에서 개별 페이지 fetch로 채운다(화이트리스트·바운드·헤드라인 폴백).

**Architecture:** `collect_once`의 피드 루프에서 `parse_feed` 직후·`upsert_items` 전에 `enrich_bodies`를 호출. 화이트리스트 소스(`source="한국경제"`)의 **미저장** 항목만, per-feed 상한 내에서 기사 URL을 fetch해 `.article-body`를 추출, 실패 시 `body=""`(헤드라인 보존). 새 `collect/body_fetch.py` + Store에 `filter_new_ids` 추가.

**Tech Stack:** Python 3.12, httpx, BeautifulSoup(lxml), pydantic(RawItem), pytest, Firestore 에뮬레이터, Docker.

설계 SSOT: `docs/superpowers/specs/2026-06-28-body-enrichment-korean-design.md`.

## Global Constraints
- **Docker 전용**: 테스트 `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest <…>`.
- **신규 의존성 0**: `httpx`·`bs4`는 기존 의존성(`fetcher.py`·`parser.py`가 이미 사용).
- **바운드(verbatim)**: `MAX_FETCH_PER_FEED=10`, `ARTICLE_TIMEOUT_S=6.0`, `THROTTLE_S=0.2`, `MIN_BODY_CHARS=80`, `EMPTY_RATE_ALERT=0.5`.
- **화이트리스트 SSOT**: `BODY_SELECTORS={"한국경제":".article-body"}` (모듈 상수, 한 곳).
- **`fetch_body`는 절대 예외 전파 안 함** → `""` 폴백. **`it.title` 절대 미변경.**
- **`follow_redirects=True`** 필수(http→https). **per-request `timeout=ARTICLE_TIMEOUT_S`**(기본 90s 상속 금지).
- **테스트 불변식 FAIL=0**, 매직넘버 금지(개수 단언은 상한 등 의미있는 값만). 라이브 네트워크 없음(MockTransport/에뮬레이터).
- **배포(Task 5)는 사용자 게이트** — 명시 승인 전 금지.

---

### Task 1: `Store.filter_new_ids` (계약 + Firestore 구현 + 에뮬레이터 테스트)

**Files:**
- Modify: `src/newsstore/contracts/ports.py` (Store에 추상 메서드)
- Modify: `src/newsstore/store/firestore_store.py` (구현)
- Test: `tests/test_firestore_store.py`

**Interfaces:**
- Produces: `Store.filter_new_ids(ids: list[str]) -> list[str]` — 아직 `items`에 저장 안 된 id만(입력 순서 보존). 빈 입력 → `[]`.

- [ ] **Step 1: 실패 테스트 작성** (`tests/test_firestore_store.py`에 추가; 기존 store fixture 사용 — 파일 상단의 기존 fixture 이름을 따른다)

```python
def test_filter_new_ids_returns_only_unstored(store):
    from datetime import datetime, timezone
    from newsstore.contracts.models import RawItem
    now = datetime(2026, 6, 12, 7, 0, tzinfo=timezone.utc)
    stored = RawItem(id="aaa", feed_id="f", source="S", url="https://e/a", title="t", fetched_at=now)
    store.upsert_items([stored])
    out = store.filter_new_ids(["aaa", "bbb", "ccc"])
    assert out == ["bbb", "ccc"]          # 저장된 aaa 제외, 순서 보존
    assert store.filter_new_ids([]) == []
```

- [ ] **Step 2: 실패 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_firestore_store.py -k filter_new_ids -v`
Expected: FAIL (`filter_new_ids` 없음 — AttributeError)

- [ ] **Step 3: 계약 + 구현**

`src/newsstore/contracts/ports.py`의 `Store` 안에 추가(기존 추상 메서드 스타일에 맞춰):
```python
    def filter_new_ids(self, ids: list[str]) -> list[str]:
        """`items`에 아직 없는 id만(입력 순서 보존)."""
        ...
```
`src/newsstore/store/firestore_store.py`의 `FirestoreStore` 안에 구현(파일 상단 `_ITEMS` 상수 사용):
```python
    def filter_new_ids(self, ids: list[str]) -> list[str]:
        if not ids:
            return []
        col = self.db.collection(_ITEMS)
        refs = [col.document(i) for i in ids]
        existing = {s.id for s in self.db.get_all(refs) if s.exists}
        return [i for i in ids if i not in existing]
```

- [ ] **Step 4: 통과 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_firestore_store.py -k filter_new_ids -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add src/newsstore/contracts/ports.py src/newsstore/store/firestore_store.py tests/test_firestore_store.py
git commit -m "feat(store): add filter_new_ids (un-stored ids, batched get_all)"
```

---

### Task 2: `fetch_body` (기사 페이지 → 본문 추출)

**Files:**
- Create: `src/newsstore/collect/body_fetch.py`
- Test: `tests/test_body_fetch.py`

**Interfaces:**
- Consumes: `fetcher.DEFAULT_HEADERS`(브라우저 UA, 기존).
- Produces: 상수들(Global Constraints) + `fetch_body(client: httpx.Client, url: str, selector: str) -> str`(실패·과소·예외 → `""`).

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_body_fetch.py`

```python
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
```

- [ ] **Step 2: 실패 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_body_fetch.py -v`
Expected: FAIL (모듈/함수 없음)

- [ ] **Step 3: 구현** — `src/newsstore/collect/body_fetch.py`

```python
from __future__ import annotations
import logging
import time
import httpx
from bs4 import BeautifulSoup
from .fetcher import DEFAULT_HEADERS

log = logging.getLogger("newsstore.collect.body_fetch")

BODY_SELECTORS: dict[str, str] = {"한국경제": ".article-body"}
MIN_BODY_CHARS = 80
MAX_FETCH_PER_FEED = 10
ARTICLE_TIMEOUT_S = 6.0
THROTTLE_S = 0.2
EMPTY_RATE_ALERT = 0.5


def fetch_body(client: httpx.Client, url: str, selector: str) -> str:
    """기사 페이지 fetch → selector 본문 추출. 실패/과소/예외 → "" (절대 raise 안 함)."""
    try:
        r = client.get(url, headers=DEFAULT_HEADERS,
                        follow_redirects=True, timeout=ARTICLE_TIMEOUT_S)
        if r.status_code != 200:
            return ""
        el = BeautifulSoup(r.text, "lxml").select_one(selector)
        if el is None:
            return ""
        text = " ".join(el.get_text(" ", strip=True).split())
        return text if len(text) >= MIN_BODY_CHARS else ""
    except Exception:
        return ""
```

- [ ] **Step 4: 통과 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_body_fetch.py -v`
Expected: PASS (6개)

- [ ] **Step 5: 커밋**

```bash
git add src/newsstore/collect/body_fetch.py tests/test_body_fetch.py
git commit -m "feat(collect): add fetch_body (article body extraction, redirect+timeout, empty fallback)"
```

---

### Task 3: `enrich_bodies` (화이트리스트·미저장·상한·스로틀·드리프트)

**Files:**
- Modify: `src/newsstore/collect/body_fetch.py` (함수 추가)
- Test: `tests/test_body_fetch.py` (추가)

**Interfaces:**
- Consumes: `fetch_body`(Task 2), `store.filter_new_ids`(Task 1), `RawItem`(`.id/.source/.url/.body` 가변).
- Produces: `enrich_bodies(client, store, items: list[RawItem]) -> list[RawItem]` — 화이트리스트+헤드라인+미저장 항목을 상한 내 fetch해 `it.body` 채움(`it.title` 불변). 그 외 항목 미변경.

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_body_fetch.py`에 추가

```python
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
    other = RawItem(id="o", feed_id="bz", source="Benzinga", url="https://e/o", title="o")
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
```

- [ ] **Step 2: 실패 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_body_fetch.py -k enrich -v`
Expected: FAIL (`enrich_bodies` 없음)

- [ ] **Step 3: 구현** — `body_fetch.py`에 추가(`fetch_body` 아래)

```python
def enrich_bodies(client, store, items):
    """화이트리스트+헤드라인+미저장 항목을 상한 내 fetch해 body 채움. 항목별 격리."""
    cand = [it for it in items if it.source in BODY_SELECTORS and not it.body]
    if not cand:
        return items
    new = set(store.filter_new_ids([it.id for it in cand]))
    targets = [it for it in cand if it.id in new][:MAX_FETCH_PER_FEED]
    empty = 0
    for it in targets:
        it.body = fetch_body(client, it.url, BODY_SELECTORS[it.source])
        if not it.body:
            empty += 1
            log.warning("body_fetch empty: %s %s", it.id, it.url)
        time.sleep(THROTTLE_S)
    if targets:
        rate = empty / len(targets)
        if rate >= EMPTY_RATE_ALERT:
            log.error("body_fetch: %d/%d empty (%.0f%%) — selector drift?",
                      empty, len(targets), rate * 100)
        else:
            log.info("body_fetch: %d/%d empty (%.0f%%)", empty, len(targets), rate * 100)
    return items
```
> 주의: 테스트가 `body_fetch.fetch_body`를 monkeypatch하므로, `enrich_bodies`는 **모듈 전역 `fetch_body`를 호출**(로컬 import 금지). `time`도 모듈 전역(`body_fetch.time`)이어야 patch됨 — 위 `import time` 그대로면 OK.

- [ ] **Step 4: 통과 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_body_fetch.py -v`
Expected: PASS (전체)

- [ ] **Step 5: 커밋**

```bash
git add src/newsstore/collect/body_fetch.py tests/test_body_fetch.py
git commit -m "feat(collect): add enrich_bodies (whitelist, new-only, cap, throttle, drift alert)"
```

---

### Task 4: 수집기 배선 (`collect_once`에 enrich_bodies)

**Files:**
- Modify: `src/newsstore/collect/collector.py`
- Test: `tests/test_collector.py`

**Interfaces:**
- Consumes: `enrich_bodies`(Task 3).

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_collector.py`에 추가(기존 테스트의 mock client/store 패턴을 따른다; RSS는 한경 1건 + 기사 HTML 두 응답)

```python
def test_collect_once_fills_hankyung_body(monkeypatch, store):
    import httpx
    from newsstore.collect import body_fetch
    from newsstore.collect.collector import collect_once
    from newsstore.collect.feeds import FeedConfig
    monkeypatch.setattr(body_fetch.time, "sleep", lambda *_: None)

    RSS = ("<rss><channel><item><title>제목</title>"
           "<link>https://www.hankyung.com/article/1</link>"
           "<guid>https://www.hankyung.com/article/1</guid>"
           "</item></channel></rss>")
    ART = "<div class='article-body'>" + "한경 본문 내용. " * 10 + "</div>"
    def handler(req):
        return httpx.Response(200, text=ART if "article" in str(req.url) else RSS)
    client = httpx.Client(transport=httpx.MockTransport(handler))

    feeds = [FeedConfig(feed_id="hk_economy", url="https://www.hankyung.com/feed/economy",
                        source="한국경제", language="ko", body_mode="headline")]
    # 기존 테스트가 쓰는 store 더블(에뮬레이터 또는 fake) 사용. filter_new_ids/upsert_items 구현체여야 함.
    summary = collect_once(client, store, feeds, force=True)   # store: 이 테스트모듈의 fixture
    saved = store.get_unprocessed()                            # 또는 기존 조회 헬퍼
    hk = [it for it in saved if it.feed_id == "hk_economy"][0]
    assert "한경 본문" in hk.body
```
> 기존 `tests/test_collector.py`의 store fixture(에뮬레이터 store 또는 fake)와 RSS mock 패턴을 그대로 재사용한다. fake store라면 `filter_new_ids`(미저장 id 반환)도 구현돼 있어야 함 — 없으면 테스트모듈 fake에 한 줄 추가.

- [ ] **Step 2: 실패 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_collector.py -k hankyung_body -v`
Expected: FAIL (body 안 채워짐 — enrich 미배선)

- [ ] **Step 3: 배선** — `src/newsstore/collect/collector.py`

상단 import에 추가:
```python
from .body_fetch import enrich_bodies
```
`collect_once`의 `items = parse_feed(res.content, feed, fetched_at=now)` **다음 줄**에 삽입:
```python
            items = enrich_bodies(client, store, items)
```
(들여쓰기는 기존 `parse_feed` 줄과 동일. 기존 피드별 `try/except` 블록 안에 위치.)

- [ ] **Step 4: 통과 + 전체 회귀**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_collector.py -v && MSYS_NO_PATHCONV=1 docker compose run --rm test`
Expected: 신규 PASS + **전체 스위트 FAIL=0**

- [ ] **Step 5: 커밋**

```bash
git add src/newsstore/collect/collector.py tests/test_collector.py
git commit -m "feat(collect): wire enrich_bodies into collect_once (fill hankyung body)"
```

---

### Task 5: 배포 (사용자 게이트 — 승인 후에만)

**Files:** 없음(수집기 이미지 재빌드+Job 갱신). 절차 `docs/operations.md §A`.

- [ ] **Step 1: 사용자 승인 확인** — 명시 전 금지.
- [ ] **Step 2: 재빌드 + `run jobs update --image` + `execute --wait`** (gcloud 풀경로).
- [ ] **Step 3: 스모크** — 1패스 후 ⓐ 한경 항목 body 채워졌는지(Firestore/로그) ⓑ **빈-본문 비율 로그** ⓒ **RSS 수집까지 정상**(한경이 IP 안 막았는지 — `feed(s) failed`에 한경 없는지). 안 되면 즉시 Job 이미지 직전으로 롤백.
- [ ] **Step 4: 사이트 확인** — 한경 기사에 본문(호버/카드) 노출(Ctrl+F5).

---

## Self-Review
- **Spec 커버리지**: §2.2 filter_new_ids(T1) · §4.1 fetch_body(T2) · §3·§4.1 enrich_bodies(상한·스로틀·드리프트·redirect·timeout)(T2·T3) · §4.3 배선(T4) · §7 배포·스모크(T5). 전부 매핑.
- **Placeholder**: 없음(모든 코드 제시). T4 step1만 "기존 store fixture/RSS mock 재사용"을 지시(테스트 파일의 실제 픽스처 이름은 구현자가 `tests/test_collector.py`에서 확인 — 무지 가정 핸드오프).
- **타입 일관성**: `filter_new_ids(list[str])->list[str]`·`fetch_body(client,url,selector)->str`·`enrich_bodies(client,store,items)->list[RawItem]` 전 태스크 일치. 상수값 Global Constraints와 일치. `it.title` 불변·`it.body` 가변.
- **불변식**: 등록/스위트 FAIL=0, 상한 단언은 `MAX_FETCH_PER_FEED` 상수 참조(매직넘버 아님).

<!-- spec-review: passed lenses=3 date=2026-06-28 note=plan reviewed; 3 test-snippet criticals(RawItem fetched_at ×2, Task4 store fixture param) fixed per reviewer; production code(body_fetch/firestore_store/collector wiring) grounded -->

