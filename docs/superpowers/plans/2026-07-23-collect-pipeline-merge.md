# 수집 파이프라인 통합(RSS·네이버·FMP 병렬화 + 임베딩 분리) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** RSS·네이버·FMP 3개 독립 Cloud Run Job을 1개(`newsstore-collect-all`)로 병합해 스레드로 병렬 실행하고, 셋 다 끝난 뒤 임베딩 패스를 한 번만 호출하며, 각 소스에 3분 예산 초과 시 fail-loud로 멈추는 안전장치를 넣는다.

**Architecture:** 기존 `collect_once`(RSS)·`run_naver_pass`(네이버)·`run_fmp_news_pass`(FMP)는 로직을 그대로 두고 `deadline`/`clock` 파라미터만 추가한다. 새 순수 오케스트레이션 함수 `run_sources_parallel`(신설 `_parallel.py`)이 `ThreadPoolExecutor`로 셋을 동시 실행하고 격리한다. 새 엔트리포인트 `run_collect_all.py`가 설정 로딩·클라이언트 생성·`run_sources_parallel` 호출·임베딩·`job_health`/시스템 장애 판정을 담당한다.

**Tech Stack:** Python 3.12, `concurrent.futures.ThreadPoolExecutor`, `httpx`, `google-cloud-firestore`(에뮬레이터 기준 테스트), pytest.

## Global Constraints

- 모든 실행·테스트는 Docker로만: `MSYS_NO_PATHCONV=1 docker compose run --rm test` (호스트에 로컬 Python 없음).
- TDD: 각 태스크는 실패하는 테스트를 먼저 쓰고, 통과시키는 최소 구현을 한 뒤 커밋한다.
- SSOT: 설정(피드·엔드포인트·쿼리)은 기존 config 파일에서 도출 — 하드코딩 금지.
- Fail-loud: 예외를 삼키지 않는다. 격리(한 소스 실패가 다른 소스를 막지 않음)와 fail-loud(조용히 넘어가지 않음)는 별개이며 둘 다 만족해야 한다.
- 비파괴 우선: 이미 처리된 항목의 Firestore 반영은 손실되지 않아야 한다(데드라인 초과로 중단해도 그 시점까지 저장된 건 유지).
- 커밋마다 `git add <구체 파일들>`(광범위 `-A`/`.` 금지).
- 스펙 문서: `docs/superpowers/specs/2026-07-23-collect-pipeline-merge-design.md` (승인·3렌즈 리뷰 완료, 마커 `passed`) — 이 플랜의 모든 태스크는 그 문서의 결정을 그대로 따른다.

---

## Task 1: `collect_once`(RSS)에 `deadline`/`clock` 예산 체크 추가

**Files:**
- Modify: `src/newsstore/collect/collector.py`
- Test: `tests/test_collector.py`

**Interfaces:**
- Consumes: 없음(기존 `FeedConfig`·`Store`만 사용).
- Produces: `CollectorTimeoutError`(예외 클래스, `naver_news.py`·`fmp_news.py`가 임포트해 재사용) / `collect_once(client, store, feeds, now=None, deadline: datetime|None=None, clock=None)` — `clock`은 인자 없이 호출하면 현재 시각(`datetime` tz-aware)을 돌려주는 콜러블, 기본값은 실제 벽시계(`datetime.now(timezone.utc)`).

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_collector.py` 맨 위 import에 `CollectorTimeoutError`를 추가하고, 파일 끝(`test_collect_once_fills_hankyung_body` 뒤)에 아래 두 테스트를 추가한다.

```python
import pytest
from newsstore.collect.collector import CollectorTimeoutError


def test_collect_once_raises_when_deadline_already_passed(store):
    feeds = [FeedConfig(feed_id=f"f{i}", url=f"https://e/{i}.rss", source="S") for i in range(3)]
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=RSS)))
    deadline = datetime(2026, 6, 12, 7, 0, tzinfo=timezone.utc)
    after_deadline = lambda: datetime(2026, 6, 12, 7, 1, tzinfo=timezone.utc)   # deadline보다 1분 뒤
    with pytest.raises(CollectorTimeoutError):
        collect_once(client, store, feeds, now=NOW, deadline=deadline, clock=after_deadline)
    assert store.count() == 0   # 첫 피드 진입 전에 바로 중단 — 아무것도 처리 안 됨


def test_collect_once_completes_within_deadline(store):
    feed = FeedConfig(feed_id="f1", url="https://e/x.rss", source="S")
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=RSS)))
    deadline = datetime(2026, 6, 12, 8, 0, tzinfo=timezone.utc)
    before_deadline = lambda: datetime(2026, 6, 12, 7, 0, tzinfo=timezone.utc)
    s = collect_once(client, store, [feed], now=NOW, deadline=deadline, clock=before_deadline)
    assert s == {"f1": 1}
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_collector.py -v`
Expected: `ImportError: cannot import name 'CollectorTimeoutError'` (아직 정의 안 됨).

- [ ] **Step 3: 최소 구현**

`src/newsstore/collect/collector.py`에서 `log = logging.getLogger(__name__)` 바로 다음에 예외 클래스를 추가한다.

```python
log = logging.getLogger(__name__)


class CollectorTimeoutError(Exception):
    """콜렉터가 자체 시간 예산(deadline)을 넘겨 중단했음을 알리는 예외.
    이 시점까지 처리된 항목은 이미 Firestore에 저장돼 있다(루프 안에서 그때그때 커밋)."""
```

`collect_once` 시그니처와 루프 시작부를 다음으로 교체한다.

```python
def collect_once(client: httpx.Client, store: Store, feeds: list[FeedConfig],
                 now: datetime | None = None, deadline: datetime | None = None,
                 clock=None) -> dict:
    now = now or datetime.now(timezone.utc)
    clock = clock or (lambda: datetime.now(timezone.utc))
    summary: dict[str, int] = {}
    for feed in feeds:
        if deadline is not None and clock() >= deadline:
            log.error("collect_once: 시간 예산(deadline) 초과 — 남은 피드 스킵, 지금까지 %d건 처리(fail-loud)",
                      len(summary))
            raise CollectorTimeoutError(f"collect_once exceeded deadline before feed {feed.feed_id}")
        # 한 피드의 실패(파싱/저장 예외 포함)가 다른 피드 수집을 막지 않도록 격리한다.
        try:
```

(이 아래 기존 `try:` 블록 본문은 그대로 둔다 — 들여쓰기·내용 변경 없음.)

- [ ] **Step 4: 테스트 통과 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_collector.py -v`
Expected: 전부 PASS.

- [ ] **Step 5: 전체 스위트 확인 + 커밋**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test`
Expected: 156 passed(기존 154 + 신규 2).

```bash
git add src/newsstore/collect/collector.py tests/test_collector.py
git commit -m "feat(collect): collect_once에 deadline/clock 예산 체크 추가"
```

---

## Task 2: `run_naver_pass`에 동일한 `deadline`/`clock` 체크 추가

**Files:**
- Modify: `src/newsstore/collect/naver_news.py`
- Test: `tests/test_naver_news.py`

**Interfaces:**
- Consumes: `CollectorTimeoutError`(Task 1에서 `collector.py`에 정의됨).
- Produces: `run_naver_pass(store, fetch, queries, *, now, deadline=None, clock=None, delay_s=0.2)`.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_naver_news.py` 맨 위에 `from newsstore.collect.collector import CollectorTimeoutError`를 추가하고, 파일 끝에 추가한다.

```python
def test_pass_raises_when_deadline_already_passed():
    store = FakeStore()
    def fetch(query): raise AssertionError("should not fetch")
    deadline = datetime(2026, 7, 19, 1, 0, tzinfo=timezone.utc)
    after_deadline = lambda: datetime(2026, 7, 19, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(CollectorTimeoutError):
        run_naver_pass(store, fetch, [{"q": "증시", "asset_hint": "kr_stock"}],
                       now=NOW, deadline=deadline, clock=after_deadline, delay_s=0)
    assert store.saved == []


def test_pass_completes_within_deadline():
    store = FakeStore()
    def fetch(query): return [_row("https://x/1")]
    deadline = datetime(2026, 7, 19, 2, 0, tzinfo=timezone.utc)
    before_deadline = lambda: datetime(2026, 7, 19, 1, 0, tzinfo=timezone.utc)
    summary = run_naver_pass(store, fetch, [{"q": "증시", "asset_hint": "kr_stock"}],
                             now=NOW, deadline=deadline, clock=before_deadline, delay_s=0)
    assert summary["naver:증시"] == 1
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_naver_news.py -v`
Expected: `TypeError: run_naver_pass() got an unexpected keyword argument 'deadline'`.

- [ ] **Step 3: 최소 구현**

`src/newsstore/collect/naver_news.py` 상단 import에 추가:

```python
from .collector import CollectorTimeoutError
```

`run_naver_pass` 시그니처와 루프를 교체한다(오래된 docstring의 "poll_minutes" 언급도 이 김에 정리).

```python
def run_naver_pass(store, fetch, queries: list[dict], *, now: datetime,
                   deadline: datetime | None = None, clock=None,
                   delay_s: float = 0.2) -> dict[str, int]:
    """키워드별 검색 뉴스 수집 → RawItem → 청크 배치 upsert. 커서 없음(멱등 URL 중복제거는
    store.upsert_items_batched의 존재검사에 위임). naver:{query} feed_state엔 건강만 기록—
    Job 자체가 스케줄러 주기에 맞춰 실행되므로 별도 due 체크 없음. 한 쿼리 실패는 격리(다음
    쿼리로 진행). deadline/clock은 collector.collect_once와 동일한 3분 예산 체크(2026-07-23
    수집 파이프라인 통합 설계 참고)."""
    clock = clock or (lambda: datetime.now(timezone.utc))
    summary: dict[str, int] = {}
    for q in queries:
        if deadline is not None and clock() >= deadline:
            log.error("run_naver_pass: 시간 예산(deadline) 초과 — 남은 쿼리 스킵, 지금까지 %d건 처리(fail-loud)",
                      len(summary))
            raise CollectorTimeoutError("run_naver_pass exceeded deadline")
        query = (q.get("q") or "").strip()
        asset_hint = (q.get("asset_hint") or "").strip()
        if not query:                    # 잘못된 config 항목은 조용히 넘기지 않고 표면화
            log.warning("naver_news: 빈 q 항목 스킵 %r", q)
            continue
        feed_id = f"naver:{query}"
        try:
```

(이 아래 기존 `try:` 블록 본문은 그대로 둔다.)

- [ ] **Step 4: 테스트 통과 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_naver_news.py -v`
Expected: 전부 PASS.

- [ ] **Step 5: 전체 스위트 확인 + 커밋**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test`
Expected: 158 passed.

```bash
git add src/newsstore/collect/naver_news.py tests/test_naver_news.py
git commit -m "feat(collect): run_naver_pass에 deadline/clock 예산 체크 추가"
```

---

## Task 3: `run_fmp_news_pass`에 동일한 `deadline`/`clock` 체크 추가

**Files:**
- Modify: `src/newsstore/collect/fmp_news.py`
- Test: `tests/test_fmp_news.py`

**Interfaces:**
- Consumes: `CollectorTimeoutError`(Task 1).
- Produces: `run_fmp_news_pass(store, fetchers, endpoints, *, now, lookback_days=..., blackout_start_hour=None, blackout_end_hour=None, deadline=None, clock=None, delay_s=0.2)`.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_fmp_news.py` 파일 끝(`test_fetch_all_pages_stops_on_short_page` 뒤)에 추가한다.

```python
def test_pass_raises_when_deadline_already_passed():
    store = FakeStore()
    def fetch(frm,to,page): raise AssertionError("should not fetch")
    deadline = datetime(2026,7,19,1,0,tzinfo=timezone.utc)
    after_deadline = lambda: datetime(2026,7,19,1,1,tzinfo=timezone.utc)
    with pytest.raises(CollectorTimeoutError):
        run_fmp_news_pass(store, {"stock-latest": fetch}, ["stock-latest"], now=NOW,
                          deadline=deadline, clock=after_deadline, delay_s=0)
    assert store.saved == []


def test_pass_completes_within_deadline():
    store = FakeStore()
    def fetch(frm,to,page): return [_row("http://x/1")] if page==0 else []
    deadline = datetime(2026,7,19,2,0,tzinfo=timezone.utc)
    before_deadline = lambda: datetime(2026,7,19,1,0,tzinfo=timezone.utc)
    summary = run_fmp_news_pass(store, {"stock-latest": fetch}, ["stock-latest"], now=NOW,
                                deadline=deadline, clock=before_deadline, delay_s=0)
    assert summary["fmp:stock-latest"] == 1
```

`import pytest`와 `from newsstore.collect.collector import CollectorTimeoutError`를 파일 상단 import에 추가한다(둘 다 아직 없다면).

- [ ] **Step 2: 테스트 실패 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_fmp_news.py -v`
Expected: `TypeError: run_fmp_news_pass() got an unexpected keyword argument 'deadline'`.

- [ ] **Step 3: 최소 구현**

`src/newsstore/collect/fmp_news.py` 상단 import에 추가:

```python
from .collector import CollectorTimeoutError
```

`run_fmp_news_pass` 시그니처와 for문 시작부를 교체한다.

```python
def run_fmp_news_pass(store, fetchers: dict, endpoints: list[str], *, now: datetime,
                      lookback_days: int = DEFAULT_LOOKBACK_DAYS,
                      blackout_start_hour: int | None = None, blackout_end_hour: int | None = None,
                      deadline: datetime | None = None, clock=None,
                      delay_s: float = 0.2) -> dict[str, int]:
    """엔드포인트별 고정 lookback 재스캔 → RawItem → 청크 배치 upsert. 커서 없음(멱등 URL 중복제거).
    fmp:{endpoint} feed_state엔 건강만 기록. 한 엔드포인트 실패는 격리.

    blackout_start_hour/end_hour(KST, [start,end) 반개구간)가 주어지면, 그 시간대엔 통째로
    스킵한다(2026-07-22: 같은 FMP API를 쓰는 별도 프로세스와의 겹침 회피). feed_state도
    건드리지 않는 순수 no-op.

    deadline/clock은 collector.collect_once와 동일한 3분 예산 체크(2026-07-23 수집
    파이프라인 통합 설계 참고)."""
    clock = clock or (lambda: datetime.now(timezone.utc))
    if blackout_start_hour is not None and blackout_end_hour is not None:
        local_hour = now.astimezone(BLACKOUT_TZ).hour
        if blackout_start_hour <= local_hour < blackout_end_hour:
            log.info("fmp_news: KST %02d~%02d시 블랙아웃 — 전체 패스 스킵(현재 KST %d시)",
                     blackout_start_hour, blackout_end_hour, local_hour)
            return {}
    summary: dict[str, int] = {}
    frm = (now - timedelta(days=lookback_days)).date().isoformat()
    to = now.date().isoformat()
    for ep in endpoints:
        if deadline is not None and clock() >= deadline:
            log.error("run_fmp_news_pass: 시간 예산(deadline) 초과 — 남은 엔드포인트 스킵, 지금까지 %d건 처리(fail-loud)",
                      len(summary))
            raise CollectorTimeoutError("run_fmp_news_pass exceeded deadline")
        feed_id = f"fmp:{ep}"
        try:
```

(이 아래 기존 `try:` 블록 본문은 그대로 둔다.)

- [ ] **Step 4: 테스트 통과 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_fmp_news.py -v`
Expected: 전부 PASS.

- [ ] **Step 5: 전체 스위트 확인 + 커밋**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test`
Expected: 160 passed.

```bash
git add src/newsstore/collect/fmp_news.py tests/test_fmp_news.py
git commit -m "feat(collect): run_fmp_news_pass에 deadline/clock 예산 체크 추가"
```

---

## Task 4: Firestore 클라이언트 동시 스레드 사용 검증

**Files:**
- Test: `tests/test_firestore_store.py` (기존 파일에 추가)

**Interfaces:**
- Consumes: 기존 `store`/`fsclient` fixture(`tests/conftest.py`), `FirestoreStore`.
- Produces: 없음(검증 전용 — 실패하면 이후 태스크 진행 전에 스펙의 "대안"(스레드별 독립 클라이언트)으로 전환 필요).

- [ ] **Step 1: 검증 테스트 작성**

`tests/test_firestore_store.py` 파일 끝에 추가한다(상단에 `import threading`가 없으면 추가).

```python
import threading


def test_concurrent_threads_share_one_store_safely(store):
    """run_collect_all 설계의 핵심 전제 검증: 3개 스레드가 같은 FirestoreStore(같은
    firestore.Client)로 서로 다른 컬렉션에 동시에 upsert_items/set_feed_state를 해도
    예외 없이 전부 반영되는지. 실패하면 스펙의 '대안'(스레드별 독립 클라이언트)으로 전환한다."""
    errors = []

    def write_items(prefix, n):
        try:
            items = [_story(f"{prefix}{i}") for i in range(n)]
            store.upsert_items(items)
        except Exception as e:
            errors.append(e)

    def write_feed_state(feed_id, n):
        try:
            for i in range(n):
                store.set_feed_state(feed_id, last_fetched=NOW, consecutive_failures=i)
        except Exception as e:
            errors.append(e)

    threads = [
        threading.Thread(target=write_items, args=("ca", 10)),
        threading.Thread(target=write_items, args=("cb", 10)),
        threading.Thread(target=write_feed_state, args=("naver:x", 10)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert store.count() == 20
    assert store.get_feed_state("naver:x")["consecutive_failures"] == 9
```

이 파일에 `_story(i)` 헬퍼와 `NOW` 상수가 이미 있는지 확인한다(있으면 재사용, 없으면 파일 상단 기존 정의를 참고해 추가).

- [ ] **Step 2: 테스트 실행**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_firestore_store.py::test_concurrent_threads_share_one_store_safely -v`
Expected: PASS(구현 변경 없이 검증만 하는 태스크이므로 실패해도 최소 구현이 아니라 스펙 대안 검토가 필요 — 아래 참고).

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test`
Expected: 161 passed(160 + 이번 태스크가 추가한 1개).

**만약 이 테스트가 실패하면(예외 발생)**: Task 7의 `main()`에서 `with make_store() as store:` 한 줄을 아래로 교체해 세 소스가 각자 독립된 클라이언트를 쓰게 한다(그 아래 `rss_task`/`naver_task`/`fmp_task`·`_run_once` 호출부는 그대로 두되, `_run_once`에 넘기는 `store` 인자와 각 task 클로저가 캡처하는 `store`만 아래처럼 분리한다).

```python
from ..store.factory import make_store as _make_one_store

with _make_one_store() as rss_store, _make_one_store() as naver_store, _make_one_store() as fmp_store, \
     _make_one_store() as main_store:   # job_health·embed_pass·set_meta는 main_store로 통일
    def rss_task():
        return collect_once(rss_client, rss_store, feeds, now=now, deadline=deadline)

    def naver_task():
        return run_naver_pass(naver_store, naver_fetch, naver_cfg["queries"], now=now,
                              deadline=deadline, delay_s=delay_s)

    def fmp_task():
        return run_fmp_news_pass(fmp_store, fmp_fetchers, fmp_cfg["endpoints"], now=now,
                                 lookback_days=fmp_cfg["lookback_days"],
                                 blackout_start_hour=fmp_cfg["blackout_start_hour"],
                                 blackout_end_hour=fmp_cfg["blackout_end_hour"],
                                 deadline=deadline, delay_s=delay_s)
    # 이하 _run_once(main_store, ...) 호출부는 원안과 동일
```

`get_feed_state`/`consecutive_failures`(만성 죽음 판정)는 컬렉션이 소스별로 겹치지 않는 다른 문서(`items/{id}`·`feed_state/{feed_id}`)를 가리키므로 클라이언트를 분리해도 데이터 정합성엔 영향 없다 — 그냥 연결(TCP/gRPC 채널)만 3개로 늘어난다.

- [ ] **Step 3: 커밋**

```bash
git add tests/test_firestore_store.py
git commit -m "test(store): 3스레드 동시 공유 클라이언트 안전성 검증(collect-all 병합 전제)"
```

---

## Task 5: `run_sources_parallel` — 순수 병렬 오케스트레이션 함수

**Files:**
- Create: `src/newsstore/entrypoints/_parallel.py`
- Test: `tests/test_parallel.py`

**Interfaces:**
- Consumes: `CollectorTimeoutError`(Task 1, `..collect.collector`에서 임포트 — 소스 자체 1단 예산 초과를 오케스트레이터 백스톱 타임아웃과 구분하기 위해 필요).
- Produces: `run_sources_parallel(sources: dict[str, callable], *, timeout: float) -> dict[str, tuple[dict, str | None]]` — 각 소스 이름 → `(summary_dict, error_marker)`. `error_marker`는 정상 완료면 `None`, 소스 자신의 `deadline` 초과(`CollectorTimeoutError`)면 `"deadline"`, 오케스트레이터가 `timeout`초를 못 기다리면 `"timeout"`, 그 외 예외면 `"error"`. `timeout`은 기본값 없이 호출부(Task 7)가 항상 명시적으로 넘긴다(같은 상수를 두 곳에 중복 정의하지 않기 위해).

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_parallel.py`를 새로 만든다.

```python
import logging
import time
import pytest
from newsstore.collect.collector import CollectorTimeoutError
from newsstore.entrypoints._parallel import run_sources_parallel


def test_all_sources_succeed():
    results = run_sources_parallel({
        "a": lambda: {"a1": 1},
        "b": lambda: {"b1": 2},
    }, timeout=5)
    assert results["a"] == ({"a1": 1}, None)
    assert results["b"] == ({"b1": 2}, None)


def test_one_source_raises_others_still_return():
    def boom():
        raise RuntimeError("dead")
    results = run_sources_parallel({
        "ok": lambda: {"x": 1},
        "bad": boom,
    }, timeout=5)
    assert results["ok"] == ({"x": 1}, None)
    assert results["bad"] == ({}, "error")


def test_source_own_deadline_exceeded_is_marked_distinctly_from_generic_error():
    def budget_exceeded():
        raise CollectorTimeoutError("budget exceeded")
    results = run_sources_parallel({"ok": lambda: {"x": 1}, "slow_src": budget_exceeded}, timeout=5)
    assert results["slow_src"] == ({}, "deadline")   # "error"와 구분돼야 진단 가치가 있다


def test_slow_source_times_out_without_blocking_fast_one():
    def slow():
        time.sleep(1.0)
        return {"never": "seen"}
    def fast():
        return {"y": 1}
    t0 = time.time()
    results = run_sources_parallel({"slow": slow, "fast": fast}, timeout=0.1)
    elapsed = time.time() - t0
    assert results["fast"] == ({"y": 1}, None)
    assert results["slow"] == ({}, "timeout")
    assert elapsed < 0.5   # 함수 자체는 slow를 기다리지 않고 빨리 반환한다(설계 문서 "2단 백스톱" 참고)


def test_late_exception_after_timeout_is_still_logged(caplog):
    """Fail-loud 검증: 오케스트레이터가 포기하고 넘어간 뒤에도, 그 스레드가 나중에 실제로
    예외를 던지면 조용히 사라지지 않고 반드시 로그로 남아야 한다."""
    def slow_then_fails():
        time.sleep(0.2)
        raise RuntimeError("late network error")
    with caplog.at_level(logging.ERROR, logger="newsstore.entrypoints.parallel"):
        run_sources_parallel({"slow": slow_then_fails}, timeout=0.05)
        time.sleep(0.4)   # slow_then_fails가 실제로 끝나 done_callback이 발동할 시간을 준다
    assert any("late network error" in r.message or "뒤늦게" in r.message for r in caplog.records)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_parallel.py -v`
Expected: `ModuleNotFoundError: No module named 'newsstore.entrypoints._parallel'`.

- [ ] **Step 3: 최소 구현**

`src/newsstore/entrypoints/_parallel.py`를 새로 만든다.

```python
"""소스 여러 개를 스레드로 동시 실행하고 서로 격리한다(2026-07-23 수집 파이프라인 통합 설계).

중요한 한계(설계 문서 그대로): 파이썬 스레드는 외부에서 안전하게 강제 종료할 수 없다.
`future.result(timeout=...)`가 타임아웃 나도 이 함수는 빨리 리턴하지만, 그 시점에 아직 안
끝난 스레드 자체는 백그라운드에서 계속 산다 — ThreadPoolExecutor의 워커 스레드는
non-daemon이라 인터프리터 종료 시(atexit) 결국 join된다. 즉 이 함수는 "우리 로직(나머지
소스 처리·임베딩·job_health 기록)이 그 하나의 멈춘 소스 때문에 같이 멈추지 않게" 해주는
것이지, "Job 프로세스 자체가 빨리 끝난다"는 걸 보장하지 않는다. 프로세스의 실제 종료는
여전히 Cloud Run Job의 task-timeout(600초)에 달려 있다.

Fail-loud: 타임아웃으로 포기한 뒤 그 스레드가 나중에 실제로 끝나거나 예외를 던져도
`future.result()`/`.exception()`을 아무도 다시 안 부르면 파이썬은 그 결과를 조용히
버린다 — 그래서 타임아웃난 future엔 반드시 `add_done_callback`을 걸어 늦게 오는
성공/실패를 로그로라도 남긴다(이번 job_health 기록엔 이미 반영 못 하더라도, 다음
사이클 운영자가 로그로 추적할 수 있게).
"""
from __future__ import annotations
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from ..collect.collector import CollectorTimeoutError

log = logging.getLogger("newsstore.entrypoints.parallel")


def _log_late_outcome(name: str):
    def _cb(fut):
        try:
            fut.result()
            log.warning("%s: 오케스트레이터 타임아웃 이후 뒤늦게 정상 완료됨"
                        "(이번 실행의 job_health엔 이미 timeout으로 기록됨)", name)
        except Exception:
            log.error("%s: 오케스트레이터 타임아웃 이후 뒤늦게 예외 발생(fail-loud, "
                     "이번 실행의 job_health엔 이미 timeout으로 기록됨)", name, exc_info=True)
    return _cb


def run_sources_parallel(sources: dict, *, timeout: float) -> dict:
    """sources: {이름: 인자없는 콜러블(호출 시 summary dict 반환)}.
    반환: {이름: (summary_dict, error_marker)} — error_marker는 성공 시 None,
    소스 자신의 deadline 초과(CollectorTimeoutError)면 "deadline",
    오케스트레이터 대기 타임아웃이면 "timeout", 그 외 예외면 "error"."""
    ex = ThreadPoolExecutor(max_workers=max(1, len(sources)))
    futures = {ex.submit(fn): name for name, fn in sources.items()}
    results: dict = {}
    for fut, name in futures.items():
        try:
            results[name] = (fut.result(timeout=timeout), None)
        except FuturesTimeoutError:
            log.error("%s: 오케스트레이터 대기 타임아웃(%.0f초) — fail-loud, 다른 소스는 계속 진행", name, timeout)
            results[name] = ({}, "timeout")
            fut.add_done_callback(_log_late_outcome(name))   # 늦게 끝나도 fail-loud로 남긴다
        except CollectorTimeoutError:
            log.error("%s: 소스 자신의 3분 예산(deadline) 초과로 중단(fail-loud) — "
                     "그 시점까지 처리분은 이미 저장돼 있음", name)
            results[name] = ({}, "deadline")
        except Exception:
            log.exception("%s: 처리 중 예외(격리) — 다른 소스는 계속 진행", name)
            results[name] = ({}, "error")
    ex.shutdown(wait=False)   # 안 끝난 스레드를 기다리지 않고 진행(위 모듈 docstring 참고)
    return results
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_parallel.py -v`
Expected: 전부 PASS.

- [ ] **Step 5: 전체 스위트 확인 + 커밋**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test`
Expected: 166 passed(154 시작 + Task1~3 각 2 + Task4 1 + Task5 5. 느린 스레드 하나가 백그라운드에 남아 pytest 종료가 약간(<1초) 느려질 수 있음 — 정상).

```bash
git add src/newsstore/entrypoints/_parallel.py tests/test_parallel.py
git commit -m "feat(entrypoints): run_sources_parallel — 소스별 스레드 격리 오케스트레이션"
```

---

## Task 6: `_health.py` — 시스템 장애 판정 통일 + `JobDegraded`

**Files:**
- Modify: `src/newsstore/entrypoints/_health.py`
- Test: `tests/test_job_health.py`

**Interfaces:**
- Consumes: `store.get_feed_state(feed_id)`(기존 계약).
- Produces: `FAIL_RATE_ALERT`·`CHRONIC_DEAD_STREAK`·`MIN_ATTEMPTED_FOR_ALERT` 상수, `classify_systemic_failure(summary: dict, store) -> tuple[list[str], set[str]]`(반환: `(new_failed 정렬 리스트, chronic 집합)`), `JobDegraded(Exception)`.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_job_health.py` 파일 끝에 추가한다.

```python
from newsstore.entrypoints._health import classify_systemic_failure, JobDegraded, job_health
import pytest


class _FeedStateStore:
    """classify_systemic_failure 검증용 — get_feed_state만 필요."""
    def __init__(self, states): self._states = states
    def get_feed_state(self, feed_id): return self._states.get(feed_id, {})


def test_classify_systemic_failure_separates_chronic_from_new():
    # f1은 만성 죽음(연속실패 5 이상), f2는 방금 실패(새로운 장애).
    store = _FeedStateStore({"f1": {"consecutive_failures": 5}, "f2": {"consecutive_failures": 1}})
    summary = {"ok1": 3, "f1": -1, "f2": -1}
    new_failed, chronic = classify_systemic_failure(summary, store)
    assert new_failed == ["f2"]
    assert chronic == {"f1"}


def test_job_health_records_fail_when_degraded_raised_inside_block():
    class _HStore:
        def __init__(self): self.h = {}
        def get_job_health(self, job): return dict(self.h.get(job, {}))
        def set_job_health(self, job, **fields):
            cur = self.h.setdefault(job, {"job": job}); cur.update(fields)

    s = _HStore()
    with pytest.raises(JobDegraded):
        with job_health(s, "collect_all") as h:
            h["detail"] = "rss=fail naver=ok fmp=ok embed=ok"
            raise JobDegraded(h["detail"])
    st = s.h["collect_all"]
    assert st["last_status"] == "fail"
    assert "rss=fail" in st["detail"]
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_job_health.py -v`
Expected: `ImportError: cannot import name 'classify_systemic_failure'`.

- [ ] **Step 3: 최소 구현**

`src/newsstore/entrypoints/_health.py` 맨 위 import 아래, `@contextmanager` 데코레이터 함수 앞에 추가한다.

```python
# 런의 성공/실패 ≠ 개별 항목(피드/쿼리/엔드포인트)의 건강. 런은 '시스템 장애'(프록시·인증·
# 네트워크 다운으로 평소 멀쩡하던 다수가 갑자기 실패)에서만 fail 처리한다. 한두 개·만성
# 죽은 항목이 죽어도 런은 정상(ok)이고, 그건 로그·대시보드로 surface한다. RSS 전용이던
# 것을 2026-07-23 수집 파이프라인 통합에서 세 소스(RSS·네이버·FMP) 공통으로 승격.
FAIL_RATE_ALERT = 0.5
CHRONIC_DEAD_STREAK = 5       # 연속 실패 이상이면 '만성 죽음' — 시스템 장애 판정에서 제외(이미 아는 죽음)
MIN_ATTEMPTED_FOR_ALERT = 10  # 정상 시도가 이 수 미만이면 실패율 알람 없음(소수 배치 우연 전멸 오판 방지)


class JobDegraded(Exception):
    """세 소스 중 하나 이상이 시스템 장애 수준으로 판정됐거나 임베딩이 실패했음을 알리는 예외.
    job_health(...) 블록 안에서 raise해야 last_status='fail'이 정확히 기록된다."""


def classify_systemic_failure(summary: dict, store) -> tuple[list[str], set[str]]:
    """summary({id: count|-1})와 store.get_feed_state로 '만성 죽음'과 '새로운 실패'를 가른다.
    반환: (new_failed 정렬 리스트, chronic id 집합). 시스템 장애 판정은 이 결과 +
    FAIL_RATE_ALERT/MIN_ATTEMPTED_FOR_ALERT를 조합해 호출부가 내린다(collector.py의
    FAIL_RATE_ALERT 로직을 세 소스 공통으로 일반화)."""
    failed = [k for k, v in summary.items() if v == -1]
    chronic = {k for k in failed
               if (store.get_feed_state(k).get("consecutive_failures") or 0) >= CHRONIC_DEAD_STREAK}
    new_failed = sorted(k for k in failed if k not in chronic)
    return new_failed, chronic
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_job_health.py -v`
Expected: 전부 PASS.

- [ ] **Step 5: 전체 스위트 확인 + 커밋**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test`
Expected: 168 passed(166 + 이번 태스크가 추가한 2개).

```bash
git add src/newsstore/entrypoints/_health.py tests/test_job_health.py
git commit -m "feat(entrypoints): 시스템 장애 판정(classify_systemic_failure)·JobDegraded를 세 소스 공통으로 승격"
```

---

## Task 7: `run_collect_all.py` — 새 오케스트레이터 엔트리포인트

**Files:**
- Create: `src/newsstore/entrypoints/run_collect_all.py`
- Test: `tests/test_run_collect_all.py`

**Interfaces:**
- Consumes: `collect_once`(Task 1)·`run_naver_pass`(Task 2)·`run_fmp_news_pass`(Task 3)·`run_sources_parallel`(Task 5)·`classify_systemic_failure`/`JobDegraded`(Task 6)·`job_health`(기존 `_health.py`, 이번 플랜 대상 아님)·`embed_pass`(기존)·`load_feeds`/`distinct_sources`/`source_tiers`(기존 `feeds.py`)·`load_naver_config`(기존)·`load_fmp_news_config`(기존)·`make_client`(기존 `ssl_config.py`)·`make_store`(기존 `factory.py`).
- Produces: `main(argv=None) -> int` — Cloud Run Job CMD가 호출하는 진입점. `_run_once(store, *, rss_task, naver_task, fmp_task, api_key, gemini_client_factory, embed_pass_fn) -> str`(오케스트레이션 본체, 아래 테스트가 직접 검증). `_summary_verdict(name, summary, store) -> tuple[str, bool]`. `DEADLINE_SECONDS`(180.0)·`BACKSTOP_SECONDS`(200.0) 모듈 상수. `build_naver_fetch(client, display)`·`build_fmp_fetchers(client, endpoints)` — 기존 `run_naver_news.py`의 `build_fetch`·`run_fmp_news.py`의 `build_fetchers`를 이관하며 **이름을 바꿨다**(한 파일에 네이버·FMP 헬퍼가 같이 있으므로 원래 이름 `build_fetch`/`build_fetchers`를 그대로 두면 후자끼리 이름이 겹친다 — 그래서 소스 접두어를 붙여 구분).

- [ ] **Step 1: 오케스트레이션 핵심 로직에 대한 실패하는 테스트 작성**

`tests/test_run_collect_all.py`를 새로 만든다. `main()` 자체(실 시크릿·실 네트워크 필요)는 여기서 테스트하지 않고, 조합 로직만 담은 `_run_once(store, *, rss_task, naver_task, fmp_task, api_key, gemini_client_factory, embed_pass_fn) -> str` 함수를 분리해 테스트한다(이 함수가 `main()`의 본체이고, `main()`은 여기에 실제 클라이언트/설정만 조립해 넘긴다. `DEADLINE_SECONDS`/`BACKSTOP_SECONDS`는 `_run_once`의 파라미터가 아니라 `main()`이 `deadline`을 계산하고 `run_sources_parallel`의 `timeout`을 정할 때 쓰는 모듈 상수다).

```python
from datetime import datetime, timezone
import pytest
from newsstore.entrypoints.run_collect_all import _run_once
from newsstore.entrypoints._health import JobDegraded


class _HStore:
    def __init__(self):
        self.h = {}
        self.feed_states = {}
        self.pending = []

    def get_job_health(self, job): return dict(self.h.get(job, {}))
    def set_job_health(self, job, **fields):
        cur = self.h.setdefault(job, {"job": job}); cur.update(fields)
    def get_feed_state(self, feed_id): return self.feed_states.get(feed_id, {})
    def get_pending_embed_items(self, limit): return self.pending
    def count(self): return 0


def test_run_once_all_sources_ok_calls_embed_and_records_ok():
    store = _HStore()
    embed_calls = []
    def fake_embed_pass(store_, client_):
        embed_calls.append(1)
        return {"pending": 0, "embedded": 0, "permanent": 0, "retryable": 0}

    detail = _run_once(
        store,
        rss_task=lambda: {"f1": 1},
        naver_task=lambda: {"naver:q": 2},
        fmp_task=lambda: {"fmp:e": 3},
        api_key="k",
        gemini_client_factory=lambda k: object(),
        embed_pass_fn=fake_embed_pass,
    )
    assert embed_calls == [1]
    assert store.h["collect_all"]["last_status"] == "ok"
    assert "rss=ok" in detail and "naver=ok" in detail and "fmp=ok" in detail and "embed=ok" in detail


def test_run_once_one_source_raises_others_still_processed_and_degraded():
    store = _HStore()
    def boom(): raise RuntimeError("dead")
    embed_calls = []
    def fake_embed_pass(store_, client_):
        embed_calls.append(1)
        return {"pending": 0, "embedded": 0, "permanent": 0, "retryable": 0}

    with pytest.raises(JobDegraded):
        _run_once(
            store,
            rss_task=lambda: {"f1": 1},
            naver_task=boom,
            fmp_task=lambda: {"fmp:e": 3},
            api_key="k",
            gemini_client_factory=lambda k: object(),
            embed_pass_fn=fake_embed_pass,
        )
    assert embed_calls == [1]                          # 네이버가 죽어도 임베딩은 여전히 호출됨
    assert store.h["collect_all"]["last_status"] == "fail"
    assert "naver=error" in store.h["collect_all"]["detail"]


def test_run_once_embed_failure_alone_degrades_job():
    store = _HStore()
    def failing_embed_pass(store_, client_):
        raise RuntimeError("gemini down")

    with pytest.raises(JobDegraded):
        _run_once(
            store,
            rss_task=lambda: {"f1": 1},
            naver_task=lambda: {"naver:q": 1},
            fmp_task=lambda: {"fmp:e": 1},
            api_key="k",
            gemini_client_factory=lambda k: object(),
            embed_pass_fn=failing_embed_pass,
        )
    assert "embed=fail" in store.h["collect_all"]["detail"]


def test_run_once_missing_key_with_pending_degrades():
    """옛 tests/test_run_collect_embed.py::test_missing_key_with_pending_exits_1의 대체 —
    run_collect.py 삭제(Task 8)로 그 파일도 삭제되므로 이 시나리오를 여기서 이어받는다."""
    store = _HStore()
    store.pending = ["p1"]

    def should_not_be_called(store_, client_):
        raise AssertionError("embed_pass_fn should not be called when api_key is missing")

    with pytest.raises(JobDegraded):
        _run_once(
            store,
            rss_task=lambda: {"f1": 1},
            naver_task=lambda: {"naver:q": 1},
            fmp_task=lambda: {"fmp:e": 1},
            api_key=None,
            gemini_client_factory=lambda k: object(),
            embed_pass_fn=should_not_be_called,
        )
    assert "embed=fail(no_key)" in store.h["collect_all"]["detail"]


def test_run_once_missing_key_without_pending_is_ok():
    """옛 tests/test_run_collect_embed.py::test_missing_key_without_pending_exits_0의 대체."""
    store = _HStore()
    store.pending = []

    def should_not_be_called(store_, client_):
        raise AssertionError("embed_pass_fn should not be called when api_key is missing")

    detail = _run_once(
        store,
        rss_task=lambda: {"f1": 1},
        naver_task=lambda: {"naver:q": 1},
        fmp_task=lambda: {"fmp:e": 1},
        api_key=None,
        gemini_client_factory=lambda k: object(),
        embed_pass_fn=should_not_be_called,
    )
    assert "embed=skip(no_key_no_pending)" in detail
    assert store.h["collect_all"]["last_status"] == "ok"


def test_build_fmp_fetchers_url_params_and_no_apikey_leak():
    """옛 tests/test_fmp_news.py::test_build_fetchers_url_params_and_no_apikey_leak을
    build_fmp_fetchers(이름 변경)로 이관 — Task 8에서 원본 테스트는 삭제한다."""
    from newsstore.entrypoints.run_collect_all import build_fmp_fetchers

    calls = []
    class FakeResp:
        def raise_for_status(self): pass
        def json(self): return []
    class FakeClient:
        def get(self, url, params=None): calls.append((url, params)); return FakeResp()

    fetchers = build_fmp_fetchers(FakeClient(), ["stock-latest", "fmp-articles"])
    fetchers["stock-latest"]("2026-07-16", "2026-07-19", 0)
    fetchers["fmp-articles"]("2026-07-16", "2026-07-19", 1)
    assert calls[0][0].endswith("/news/stock-latest")
    assert calls[0][1] == {"from": "2026-07-16", "to": "2026-07-19", "limit": 250, "page": 0}
    assert calls[1][0].endswith("/fmp-articles")           # /news/ 아님
    assert "from" not in calls[1][1] and calls[1][1] == {"limit": 250, "page": 1}
    # 비밀 비노출: apikey가 URL·params 어디에도 없어야 한다(헤더 전용)
    for url, params in calls:
        assert "apikey" not in url and "apikey" not in (params or {})
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_run_collect_all.py -v`
Expected: `ModuleNotFoundError: No module named 'newsstore.entrypoints.run_collect_all'`.

- [ ] **Step 3: 구현**

`src/newsstore/entrypoints/run_collect_all.py`를 새로 만든다.

```python
"""통합 수집 엔트리포인트 — RSS·네이버·FMP를 병렬 실행하고, 셋 다 끝난 뒤 임베딩 패스를
한 번만 호출한다(2026-07-23 수집 파이프라인 통합 설계).

이전에는 newsstore-collector(RSS, 5분)·newsstore-naver-news(15분)·newsstore-fmp-news(15분)
3개 Cloud Run Job이 서로 완전히 독립적으로 돌았다. 이 엔트리포인트가 그 셋을 대체한다.
"""
from __future__ import annotations
import argparse
import logging
import os
from datetime import datetime, timedelta, timezone

import httpx

from ..collect.feeds import load_feeds, distinct_sources, source_tiers
from ..collect.ssl_config import make_client
from ..collect.collector import collect_once
from ..collect.naver_news import load_naver_config, run_naver_pass
from ..collect.fmp_news import load_fmp_news_config, run_fmp_news_pass, PAGE_LIMIT
from ..store.factory import make_store
from ._health import job_health, classify_systemic_failure, JobDegraded, \
    FAIL_RATE_ALERT, MIN_ATTEMPTED_FOR_ALERT
from ._parallel import run_sources_parallel

log = logging.getLogger("newsstore.entrypoints.run_collect_all")

DEADLINE_SECONDS = 180.0   # 소스별 자체 예산(1단) — 설계 문서 "3분 강제종료" 참고
BACKSTOP_SECONDS = 200.0   # 오케스트레이터 result(timeout=) 백스톱(2단) — 1단보다 20초 여유

NAVER_NEWS_URL = "https://openapi.naver.com/v1/search/news.json"
FMP_BASE_NEWS = "https://financialmodelingprep.com/stable/news/"
FMP_BASE_ARTICLES = "https://financialmodelingprep.com/stable/fmp-articles"


def build_naver_fetch(client, display: int):
    """쿼리 → 검색 뉴스 GET. 인증은 client 헤더에만(params·URL·로그에 비밀 금지, SECRETS)."""
    def fetch(query):
        r = client.get(NAVER_NEWS_URL, params={"query": query, "display": display, "sort": "date"})
        r.raise_for_status()
        return (r.json() or {}).get("items") or []
    return fetch


def build_fmp_fetchers(client, endpoints: list[str]) -> dict:
    """엔드포인트별 GET 함수. -latest는 from/to 지원, fmp-articles는 page/limit만."""
    def make(ep):
        def fetch(frm, to, page):
            if ep == "fmp-articles":
                r = client.get(FMP_BASE_ARTICLES, params={"limit": PAGE_LIMIT, "page": page})
            else:
                r = client.get(f"{FMP_BASE_NEWS}{ep}",
                               params={"from": frm, "to": to, "limit": PAGE_LIMIT, "page": page})
            r.raise_for_status()
            return r.json() or []
        return fetch
    return {ep: make(ep) for ep in endpoints}


def _summary_verdict(name: str, summary: dict, store) -> tuple[str, bool]:
    """한 소스의 summary를 시스템 장애 여부로 판정. 반환: (detail 조각, degraded?)."""
    new_failed, chronic = classify_systemic_failure(summary, store)
    attempted = len(summary)
    healthy_attempted = attempted - len(chronic)
    if healthy_attempted >= MIN_ATTEMPTED_FOR_ALERT and healthy_attempted and \
            len(new_failed) / healthy_attempted >= FAIL_RATE_ALERT:
        return f"{name}=fail({len(new_failed)}/{healthy_attempted})", True
    return f"{name}=ok", False


def _run_once(store, *, rss_task, naver_task, fmp_task, api_key, gemini_client_factory,
              embed_pass_fn) -> str:
    """세 소스를 병렬 실행하고 결과를 종합해 job_health를 기록한다. 시스템 장애나 임베딩
    실패가 있으면 JobDegraded를 raise한다(job_health 블록 안에서 raise돼야 last_status='fail'이
    정확히 기록된다 — 설계 문서 'job_health 정확한 실패 기록' 참고). 성공 시 detail 문자열을
    반환한다. embed_pass_fn은 (store, client) -> {"pending":.., "embedded":.., "permanent":.., "retryable":..}."""
    with job_health(store, "collect_all") as h:
        results = run_sources_parallel(
            {"rss": rss_task, "naver": naver_task, "fmp": fmp_task},
            timeout=BACKSTOP_SECONDS,
        )

        details = []
        degraded = False
        for name in ("rss", "naver", "fmp"):
            summary, error = results[name]
            if error:
                details.append(f"{name}={error}")
                degraded = True
            else:
                piece, is_degraded = _summary_verdict(name, summary, store)
                details.append(piece)
                degraded = degraded or is_degraded

        embed_failed = False
        try:
            if api_key:
                client = gemini_client_factory(api_key)
                es = embed_pass_fn(store, client)
                log.info("embed pass: pending=%d embedded=%d permanent=%d retryable=%d",
                         es["pending"], es["embedded"], es["permanent"], es["retryable"])
                details.append("embed=ok")
            elif store.get_pending_embed_items(limit=1):
                log.error("GEMINI_API_KEY missing but embed_pending items exist (embedding stalled)")
                details.append("embed=fail(no_key)")
                embed_failed = True
            else:
                details.append("embed=skip(no_key_no_pending)")
        except Exception:
            log.exception("embed pass failed")
            details.append("embed=fail")
            embed_failed = True

        detail = " ".join(details)
        h["detail"] = detail
        if degraded or embed_failed:
            raise JobDegraded(detail)
        return detail


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="newsstore 통합 수집(RSS+네이버+FMP+임베딩)")
    ap.add_argument("--feeds", default="config/feeds.yaml")
    ap.add_argument("--naver-config", default="config/naver_news.yaml")
    ap.add_argument("--fmp-config", default="config/fmp_news.yaml")
    args = ap.parse_args(argv)
    logging.basicConfig(level=os.environ.get("NEWSSTORE_LOG_LEVEL", "INFO"),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    # 시크릿은 클라이언트를 하나라도 만들기 전에 전부 먼저 읽는다(fail-loud) — 순서가
    # 반대면(클라이언트부터 만들고 나중에 시크릿을 읽으면) 뒤쪽 시크릿이 없을 때 앞서
    # 만든 클라이언트가 닫히지 않고 새고, job_health 블록에 들어가기도 전에 죽어서
    # 대시보드가 '실패'가 아니라 '미실행'으로만 잡는다(옛 run_naver_news.py도 이 순서였다).
    naver_client_id = os.environ["NAVER_CLIENT_ID"]          # fail-loud
    naver_client_secret = os.environ["NAVER_CLIENT_SECRET"]  # fail-loud
    fmp_api_key = os.environ["FMP_API_KEY"]                  # fail-loud
    api_key = os.environ.get("GEMINI_API_KEY")               # 임베딩은 선택 — 없으면 _run_once가 판단

    feeds = load_feeds(args.feeds)
    naver_cfg = load_naver_config(args.naver_config)
    fmp_cfg = load_fmp_news_config(args.fmp_config)
    delay_s = float(os.environ.get("NEWSSTORE_NEWS_DELAY_S", "0.2"))

    rss_client = make_client()
    naver_client = httpx.Client(timeout=30.0, headers={
        "X-Naver-Client-Id": naver_client_id, "X-Naver-Client-Secret": naver_client_secret})
    fmp_client = httpx.Client(timeout=30.0, headers={"apikey": fmp_api_key})

    now = datetime.now(timezone.utc)
    deadline = now + timedelta(seconds=DEADLINE_SECONDS)
    naver_fetch = build_naver_fetch(naver_client, naver_cfg["display"])
    fmp_fetchers = build_fmp_fetchers(fmp_client, fmp_cfg["endpoints"])

    try:
        with make_store() as store:
            # SSOT: 사이트 소스 목록·tier를 feeds.yaml에서 도출해 기록(하드코딩 X).
            store.set_meta("sources", {"sources": distinct_sources(feeds),
                                       "tiers": source_tiers(feeds)})

            def rss_task():
                return collect_once(rss_client, store, feeds, now=now, deadline=deadline)

            def naver_task():
                return run_naver_pass(store, naver_fetch, naver_cfg["queries"], now=now,
                                      deadline=deadline, delay_s=delay_s)

            def fmp_task():
                return run_fmp_news_pass(store, fmp_fetchers, fmp_cfg["endpoints"], now=now,
                                         lookback_days=fmp_cfg["lookback_days"],
                                         blackout_start_hour=fmp_cfg["blackout_start_hour"],
                                         blackout_end_hour=fmp_cfg["blackout_end_hour"],
                                         deadline=deadline, delay_s=delay_s)

            def gemini_client_factory(key):
                from ..embed.gemini import GeminiEmbedClient
                return GeminiEmbedClient(key)

            from ..embed.embed_pass import embed_pass

            detail = _run_once(store, rss_task=rss_task, naver_task=naver_task,
                               fmp_task=fmp_task, api_key=api_key,
                               gemini_client_factory=gemini_client_factory,
                               embed_pass_fn=embed_pass)
            log.info("collect_all done: %s", detail)
    except JobDegraded as e:
        log.error("collect_all FAILED (systemic): %s", e)
        return 1
    finally:
        rss_client.close()
        naver_client.close()
        fmp_client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_run_collect_all.py -v`
Expected: 전부 PASS.

- [ ] **Step 5: 전체 스위트 확인 + 커밋**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test`
Expected: 174 passed(168 + 이번 태스크가 추가한 6개 — Task 8에서 옛 테스트 2개를 지우면서 다시 줄어든다).

```bash
git add src/newsstore/entrypoints/run_collect_all.py tests/test_run_collect_all.py
git commit -m "feat(entrypoints): run_collect_all — RSS·네이버·FMP 병렬 실행 + 임베딩 통합 오케스트레이터"
```

---

## Task 8: 옛 엔트리포인트 삭제 + 운영 문서 갱신

**Files:**
- Delete: `src/newsstore/entrypoints/run_collect.py`, `src/newsstore/entrypoints/run_naver_news.py`, `src/newsstore/entrypoints/run_fmp_news.py`, `tests/test_run_collect_embed.py`
- Modify: `tests/test_fmp_news.py`(빌드 헬퍼 테스트 제거 — Task 7에서 이미 이관 완료), `docs/operations.md`

**Interfaces:**
- Consumes: 없음.
- Produces: 없음(정리 태스크).

- [ ] **Step 1: 삭제 대상 모듈을 실제로 참조하는 테스트 확인**

Run: `grep -rl "run_collect\b\|run_naver_news\|run_fmp_news\b" tests/`
Expected: `tests/test_run_collect_embed.py`와 `tests/test_fmp_news.py` 2개가 매칭된다(둘 다 아래에서 처리 — "매칭 없음"이 아니라 "이 둘을 처리한다"가 기대치다).
- `tests/test_run_collect_embed.py`: `run_collect.main()`을 에뮬레이터로 통째로 돌리는 6개 테스트. 이 시나리오(임베딩 키 부재·시스템 장애·만성 죽은 피드 제외)는 Task 6의 `test_classify_systemic_failure_separates_chronic_from_new`와 Task 7의 `test_run_once_*`(6개, 특히 `missing_key_with_pending`/`missing_key_without_pending`)로 이미 이관돼 있다.
- `tests/test_fmp_news.py`의 `test_build_fetchers_url_params_and_no_apikey_leak`: Task 7에서 `test_build_fmp_fetchers_url_params_and_no_apikey_leak`로 이미 이관돼 있다.

- [ ] **Step 2: 옛 테스트·엔트리포인트 삭제**

```bash
git rm tests/test_run_collect_embed.py
git rm src/newsstore/entrypoints/run_collect.py src/newsstore/entrypoints/run_naver_news.py src/newsstore/entrypoints/run_fmp_news.py
```

`tests/test_fmp_news.py`에서 아래 테스트 함수 전체(주석 포함)를 삭제한다(Task 7의 `test_build_fmp_fetchers_url_params_and_no_apikey_leak`가 대체).

```python
def test_build_fetchers_url_params_and_no_apikey_leak():
    calls = []
    class FakeResp:
        def raise_for_status(self): pass
        def json(self): return []
    class FakeClient:
        def get(self, url, params=None): calls.append((url, params)); return FakeResp()
    from newsstore.entrypoints.run_fmp_news import build_fetchers
    fetchers = build_fetchers(FakeClient(), ["stock-latest", "fmp-articles"])
    fetchers["stock-latest"]("2026-07-16", "2026-07-19", 0)
    fetchers["fmp-articles"]("2026-07-16", "2026-07-19", 1)
    assert calls[0][0].endswith("/news/stock-latest")
    assert calls[0][1] == {"from": "2026-07-16", "to": "2026-07-19", "limit": 250, "page": 0}
    assert calls[1][0].endswith("/fmp-articles")           # /news/ 아님
    assert "from" not in calls[1][1] and calls[1][1] == {"limit": 250, "page": 1}
    # 비밀 비노출: apikey가 URL·params 어디에도 없어야 한다(헤더 전용)
    for url, params in calls:
        assert "apikey" not in url and "apikey" not in (params or {})
```

- [ ] **Step 3: 전체 스위트 확인**

Run: `grep -rl "run_collect\b\|run_naver_news\|run_fmp_news\b" tests/`
Expected: 매칭 없음(이제 진짜로 없어야 한다).

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test`
Expected: 167 passed(174 − 6[`test_run_collect_embed.py` 삭제] − 1[`test_fmp_news.py`의 이관된 테스트 삭제]).

```bash
git add tests/test_fmp_news.py
git commit -m "test: 옛 run_collect/run_naver_news/run_fmp_news 및 그 테스트 삭제(run_collect_all로 대체 완료)"
```

- [ ] **Step 4: `docs/operations.md` 갱신**

`docs/operations.md`에서 기존 Job(문서에 실제로 기재된 건 `newsstore-collector`·`newsstore-fmp-news` 2개뿐 — 네이버는 애초에 문서에 없었다)과 관련된 재배포 절차(§A 부근)를 찾아, 다음 내용으로 교체한다(정확한 줄 번호는 파일을 열어 확인 — 리소스 인벤토리 표의 Job/스케줄러 행, §A의 재배포 명령, §F의 FMP 관련 섹션 전부 포함).

```markdown
## A. 수집기 재배포 (config/*.yaml 또는 수집기 코드 변경 시)
`config/feeds.yaml`·`config/naver_news.yaml`·`config/fmp_news.yaml`은 이미지에 `COPY`되므로
**반드시 재빌드 후 Job 갱신**해야 반영된다. RSS·네이버·FMP가 이제 `newsstore-collect-all`
Job 하나로 통합돼 있다(2026-07-23, 이전 3개 Job에서 병합).
```
```
# 1) 이미지 재빌드
gcloud builds submit --config infra/cloudbuild.yaml \
  --substitutions=_IMAGE=asia-northeast3-docker.pkg.dev/daily-recap-498506/newsstore/collector:latest .
# 2) Job을 새 이미지 digest로 재고정
gcloud beta run jobs update newsstore-collect-all \
  --image=asia-northeast3-docker.pkg.dev/daily-recap-498506/newsstore/collector:latest \
  --region=asia-northeast3
# 3) 즉시 1회 실행 (안 하면 다음 스케줄에 반영)
gcloud beta run jobs execute newsstore-collect-all --region=asia-northeast3 --wait
# 4) 확인
gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="newsstore-collect-all"' \
  --freshness=5m --format="value(textPayload)"
```

리소스 인벤토리 표를 실제 내용과 대조해 갱신한다. **표에 실제로 있는 것**(`newsstore-collector`·`newsstore-fmp-news` Job 행, `newsstore-5min` 스케줄러 행)은 아래 한 행씩으로 교체하고, **표에 없던 것**(네이버 Job·네이버 스케줄러·FMP 전용 스케줄러 행 — 애초에 이 문서에 기재된 적이 없었다, 문서 stale)은 새로 추가하는 게 아니라 그냥 아래 한 행으로 귀결된다(교체 대상 자체가 없으므로 실제로는 "추가"에 가깝다 — 파일을 열어 정확히 어떤 행이 존재하는지 먼저 확인하고 반영한다).

```markdown
| Cloud Run Job | `newsstore-collect-all` — RSS+네이버+FMP 병렬 수집 + 임베딩 패스(`run_collect_all`, secrets `gemini-api-key`·`fmp-api-key`·네이버 자격증명) |
| Cloud Scheduler | `newsstore-collect-all-15min` (`*/15 * * * *`) — 통합 수집기 |
```

(`newsstore-backfill-embed` Job 행은 이 플랜과 무관하므로 그대로 둔다.)

- [ ] **Step 5: 커밋**

```bash
git add docs/operations.md
git commit -m "docs(operations): 통합 Job(newsstore-collect-all)로 재배포 절차·인벤토리 갱신"
```

---

## Task 9: 배포 — 새 Job·스케줄러 생성, 옛 스케줄러 일시정지

**이 태스크는 실제 프로덕션 인프라를 바꾼다 — 실행 전 사용자에게 확인받는다(이 세션 내내 지켜온 규칙).** 이 리포의 office 환경(사내 ePrism MITM)에서는 최신 gcloud가 SSL 핸드셰이크에서 막히므로(`docs/solved_problems.md` "사내(ePrism MITM) gcloud SSL" 항목), 아래 모든 `gcloud` 호출은 옛 SDK 402 도커 컨테이너 + `gcloud-cfg` 볼륨 + `beta` 트랙으로 감싼다(이 세션에서 실제로 검증된 패턴 그대로). 매 스텝의 "Run:" 블록은 이 wrapper 안의 명령만 바꿔가며 실행한다.

```bash
MSYS_NO_PATHCONV=1 docker run --rm \
  -v gcloud-cfg:/root/.config/gcloud \
  -v "$(pwd)":/work -w /work \
  google/cloud-sdk:402.0.0-slim \
  bash -c "
cp /work/ePrism-SSL-ROOT-CA.crt /usr/local/share/ca-certificates/eprism.crt && \
update-ca-certificates >/dev/null 2>&1 && \
gcloud config set core/custom_ca_certs_file /etc/ssl/certs/ca-certificates.crt >/dev/null 2>&1 && \
gcloud config set project daily-recap-498506 >/dev/null 2>&1 && \
<여기에 각 스텝의 실제 gcloud 명령을 넣는다>
"
```

**Files:** 없음(인프라 전용 태스크).

- [ ] **Step 1: 이미지 재빌드**

위 wrapper 안에 넣어 실행:
```bash
gcloud builds submit --config infra/cloudbuild.yaml \
  --substitutions=_IMAGE=asia-northeast3-docker.pkg.dev/daily-recap-498506/newsstore/collector:latest .
```
Expected: `STATUS: SUCCESS`.

- [ ] **Step 2: 네이버 자격증명이 기존 Job에 어떻게 주입돼 있는지 확인**

옛 `newsstore-naver-news` Job은 삭제하기 전(Task 9 범위 밖 — 별도 세션)까지 아직 살아있으므로, wrapper 안에 넣어 실행:
```bash
gcloud beta run jobs describe newsstore-naver-news --region=asia-northeast3 \
  --format="yaml(spec.template.spec.template.spec.containers[0].env, spec.template.spec.template.spec.containers[0].envFrom)"
```
Expected: `NAVER_CLIENT_ID`/`NAVER_CLIENT_SECRET`이 `value:`(plain env) 형태인지 `valueFrom.secretKeyRef:`(Secret Manager) 형태인지가 출력에 그대로 보인다. 이 결과에 따라 Step 3의 `--set-env-vars`(plain이면) 또는 `--set-secrets`(secret이면, 시크릿 이름은 출력의 `secretKeyRef.name`을 그대로 씀) 중 맞는 쪽을 골라 쓴다.

- [ ] **Step 3: 새 Cloud Run Job 생성**

Step 2 결과가 plain env(`NAVER_CLIENT_ID=<값>`, `NAVER_CLIENT_SECRET=<값>`)였다면 wrapper 안에 넣어 실행(실제 값은 Step 2 출력에서 그대로 복사 — 이 문서엔 실제 비밀값을 적지 않는다):
```bash
gcloud beta run jobs create newsstore-collect-all \
  --image=asia-northeast3-docker.pkg.dev/daily-recap-498506/newsstore/collector:latest \
  --region=asia-northeast3 \
  --command=python --args=-m,newsstore.entrypoints.run_collect_all \
  --set-secrets=GEMINI_API_KEY=gemini-api-key:latest,FMP_API_KEY=fmp-api-key:latest \
  --set-env-vars=NAVER_CLIENT_ID=<Step2에서 확인한 값>,NAVER_CLIENT_SECRET=<Step2에서 확인한 값> \
  --service-account=newsstore-job@daily-recap-498506.iam.gserviceaccount.com \
  --task-timeout=600
```
Step 2 결과가 Secret Manager 참조였다면 `--set-env-vars` 대신 `--set-secrets=...,NAVER_CLIENT_ID=<시크릿명>:latest,NAVER_CLIENT_SECRET=<시크릿명>:latest`로 바꿔 쓴다.
Expected: `Job [newsstore-collect-all] has been successfully created`.

- [ ] **Step 4: 1회 수동 실행으로 검증**

wrapper 안에 넣어 실행: `gcloud beta run jobs execute newsstore-collect-all --region=asia-northeast3 --wait`
Expected: `Execution [...] has successfully completed.`

wrapper 안에 넣어 실행:
```bash
gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="newsstore-collect-all"' \
  --freshness=5m --format="value(textPayload)"
```
Expected: `collect_all done: rss=ok naver=ok fmp=ok embed=ok`(또는 그날 상황에 맞는 값) 로그 라인. `naver=`나 `fmp=`가 `error`/`deadline`이면 Step 2-3의 시크릿 배선을 다시 확인한다.

- [ ] **Step 5: 새 스케줄러 생성**

wrapper 안에 넣어 실행:
```bash
gcloud scheduler jobs create http newsstore-collect-all-15min --location=asia-northeast3 \
  --schedule="*/15 * * * *" \
  --uri="https://asia-northeast3-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/daily-recap-498506/jobs/newsstore-collect-all:run" \
  --http-method=POST --oauth-service-account-email=newsstore-job@daily-recap-498506.iam.gserviceaccount.com
```
Expected: `Created job [newsstore-collect-all-15min]`.

- [ ] **Step 6: 옛 스케줄러 3개 일시정지(삭제 아님 — 설계 문서 "삭제 시점" 정책)**

wrapper 안에 넣어 실행:
```bash
gcloud scheduler jobs pause newsstore-5min --location=asia-northeast3
gcloud scheduler jobs pause newsstore-naver-15min --location=asia-northeast3
gcloud scheduler jobs pause newsstore-fmp-daily --location=asia-northeast3
```
Expected: 각각 `Job has been paused.`

- [ ] **Step 7: 하루~1주일 관찰 후 옛 Job·스케줄러 삭제(별도 세션에서 수행)**

`newsstore-collect-all`이 예정된 기간 동안 문제없이 도는 걸 `job_health`/Cloud Logging으로 확인한 뒤에만, wrapper 안에 넣어 다음을 실행한다(이 플랜의 범위 밖 — 확인 후 별도로 진행).

```bash
gcloud scheduler jobs delete newsstore-5min newsstore-naver-15min newsstore-fmp-daily --location=asia-northeast3
gcloud beta run jobs delete newsstore-collector newsstore-naver-news newsstore-fmp-news --region=asia-northeast3
```

---

## Self-Review (작성 시점에 수행 + 3렌즈 리뷰 반영 후 갱신)

- **스펙 커버리지**: Job 토폴로지(Task 9)·병렬 실행(Task 5,7)·임베딩 분리(Task 7의 `_run_once`가 소스 처리 후에만 임베딩 호출)·2단 방어(Task 1-3의 1단, Task 5의 2단 + 늦게 오는 예외 로깅)·`job_health` 정확한 실패 기록(Task 6,7)·Firestore 동시성 검증 + 실패 시 구체적 대안 코드(Task 4)·삭제 시점 정책(Task 9 Step 6-7)·트레이드오프 인지(문서화만, 별도 코드 없음 — 스펙에 이미 기록됨) 전부 태스크로 매핑됨.
- **플레이스홀더 스캔**: "TBD"·"나중에"·"적절히 처리" 패턴 없음 — 모든 스텝에 완전한 코드 포함.
- **타입/시그니처 일관성**: `deadline`/`clock` 파라미터명과 위치가 Task 1·2·3에서 동일. `run_sources_parallel`의 반환 타입(`{name: (summary, error)}`, error∈{None,"deadline","timeout","error"})이 Task 7의 `_run_once`에서 그대로 소비됨. `classify_systemic_failure`의 반환(`(new_failed, chronic)`)이 `_summary_verdict`에서 그대로 사용됨.
- **3렌즈 리뷰 반영(2026-07-23, 1회 regenerate)**: critical 3건(옛 테스트 파일이 삭제 대상 모듈을 직접 import해 Task 8에서 깨지는 문제 → Task 8에 이관·삭제 스텝 추가 및 Task 7에 대체 테스트 3개 추가; `run_sources_parallel`이 타임아웃 이후 늦게 발생하는 예외를 무로그로 삼키는 Fail-loud 위반 → `add_done_callback` 추가; `CollectorTimeoutError`가 일반 예외와 구분 안 되는 문제 → `"deadline"` 마커 신설), major 다수(테스트 개수 누적 재계산, Task 7 함수명 개명 명시, `main()`의 시크릿 읽기 순서 버그 수정, Task 4 대안의 실제 코드화, Task 9 office 우회 래핑 + 네이버 시크릿 구체 확인 스텝) 전부 반영 완료.

<!-- spec-review: passed -->
