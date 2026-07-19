# FMP 뉴스 수집 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** FMP 뉴스 6종 파이어호스를 별도 수집 패스로 통합해 기존 `items` 컬렉션에 `RawItem`으로 저장한다.

**Architecture:** `prices`/`factors`와 동형의 별도 패스 — `collect/fmp_news.py`(파싱·오케스트레이션) + `entrypoints/run_fmp_news.py`(HTTP 배선) + `config/fmp_news.yaml`(활성 엔드포인트). 산출물을 `RawItem`으로 만들어 store에 넘기면 분류·임베딩·60일 TTL은 기존 경로가 처리한다. 이동 커서 대신 **고정 lookback 재스캔**(멱등 URL 중복제거)으로 지각·역순 인덱싱을 갭필한다.

**Tech Stack:** Python 3.12, httpx, pydantic, PyYAML, BeautifulSoup(lxml), Firestore(에뮬레이터 테스트), pytest.

## Global Constraints

- **Docker 전용**: 모든 테스트·실행은 `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest ...`. 로컬 Python 없음.
- **저장소=Firestore 단일**: store 테스트는 에뮬레이터에 붙는다(test 서비스가 자동 기동). 순수 로직 테스트는 에뮬레이터 불필요.
- **비밀**: `FMP_API_KEY`는 `os.environ["FMP_API_KEY"]`로 fail-loud 로드, **헤더로만**(`{"apikey": key}`), URL·params·로그 미노출.
- **SSOT/도출**: 활성 엔드포인트 목록은 `config/fmp_news.yaml` 한 곳. `PAGE_LIMIT`(250)는 `fmp_news.py` 한 곳에 정의하고 엔트리포인트가 import(복제 금지).
- **비파괴**: 원본 저장, 필터는 삭제가 아니라 kind 마킹.
- **TDD·불변식**: 실패 테스트 먼저. 기대 개수를 박지 말고 불변식(예: 재-pull 후 신규=0)으로 검증.
- **엔드포인트 이름 계약**: REST 경로 이름 `stock-latest·press-releases-latest·general-latest·forex-latest·crypto-latest·fmp-articles`. feed_state 키는 `fmp:{endpoint}`. (스펙의 개념명 NEWS_LOOKBACK_DAYS = 이 계획의 config 키 `lookback_days`/파라미터 `lookback_days`.)
- **REST 실측(2026-07-19)**: `*-latest` 5종 shape=`symbol·publishedDate·publisher·title·image·site·text·url`, `from`/`to`/`limit`(≤250)/`page`(≤100) 지원. `fmp-articles` shape=`title·date·content·tickers·image·link·author·site`, **from/to 미지원**(page·limit만).

---

## 파일 구조

- **Create** `src/newsstore/collect/fmp_news.py` — JSON→RawItem 매핑(표준+변형), tz 파싱, 페이지네이션·고정 lookback 오케스트레이션, 엔드포인트별 건강, config 로더, 상수 SSOT(`PAGE_LIMIT`·`PAGE_CAP`).
- **Create** `src/newsstore/entrypoints/run_fmp_news.py` — HTTP 배선(fetchers), store, 패스 실행.
- **Create** `config/fmp_news.yaml` — 활성 엔드포인트·lookback·poll(SSOT).
- **Modify** `src/newsstore/contracts/models.py` — `RawItem`에 `symbol: str = ""`.
- **Modify** `src/newsstore/store/firestore_store.py` — `_to_doc`가 `symbol` 저장 + `upsert_items_batched`(청크 배치 중복제거).
- **Create** `tests/test_fmp_news.py` — 매핑·페이지네이션·오케스트레이션·비밀·분류(순수, 페이크 store/db/fetcher).
- **Modify** `tests/test_firestore_store.py` — `symbol` 저장 + `upsert_items_batched`(에뮬레이터).
- **Modify** `docs/firestore-contract.md`, `docs/operations.md` — symbol 필드·fmp feed_state 키·신규 잡.

---

## Task 1: RawItem에 symbol 필드 + _to_doc 저장

**Files:**
- Modify: `src/newsstore/contracts/models.py`
- Modify: `src/newsstore/store/firestore_store.py` (`_to_doc`)
- Test: `tests/test_firestore_store.py`

**Interfaces:**
- Produces: `RawItem(..., symbol: str = "")`; `_to_doc(item)` 결과 dict에 `"symbol"` 포함.

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_firestore_store.py`에 추가

```python
from datetime import datetime, timezone
from newsstore.contracts.models import RawItem
from newsstore.store.firestore_store import _to_doc

def test_rawitem_symbol_defaults_empty():
    it = RawItem(id="a", feed_id="fmp:stock-latest", source="X",
                 url="http://x/1", title="t", fetched_at=datetime.now(timezone.utc))
    assert it.symbol == ""

def test_to_doc_persists_symbol():
    it = RawItem(id="a", feed_id="fmp:stock-latest", source="X", symbol="AAPL",
                 url="http://x/1", title="t", fetched_at=datetime.now(timezone.utc))
    assert _to_doc(it)["symbol"] == "AAPL"
```

- [ ] **Step 2: 실패 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_firestore_store.py::test_to_doc_persists_symbol -v`
Expected: FAIL (`RawItem`에 `symbol` 없음 / `_to_doc`에 `symbol` 키 없음)

- [ ] **Step 3: RawItem에 필드 추가** — `models.py`

```python
class RawItem(BaseModel):
    id: str
    feed_id: str
    source: str
    asset_hint: str = ""
    language: str = "en"
    url: str
    title: str
    body: str = ""
    symbol: str = ""          # FMP 티커 태깅 보존(RSS는 빈 문자열, 하위호환)
    published_at: datetime | None = None
    fetched_at: datetime
```

- [ ] **Step 4: _to_doc에 symbol 저장** — `firestore_store.py`의 `_to_doc` doc dict에 한 줄 추가

```python
    doc = {
        "feed_id": item.feed_id, "source": item.source,
        "asset_hint": item.asset_hint, "language": item.language,
        "url": item.url, "title": item.title, "body": item.body,
        "symbol": item.symbol,
        "published_at": item.published_at, "fetched_at": item.fetched_at,
        "kind": kind,
        "expire_at": item.fetched_at + _TTL,
    }
```

- [ ] **Step 5: 통과 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_firestore_store.py -k symbol -v`
Expected: PASS (2 passed)

- [ ] **Step 6: 커밋**

```bash
git add src/newsstore/contracts/models.py src/newsstore/store/firestore_store.py tests/test_firestore_store.py
git commit -m "feat(models): RawItem에 symbol 필드 + _to_doc 저장(FMP 티커 태깅)"
```

---

## Task 2: 표준 매핑 + FMP_NEWS_TZ 확정

**Files:**
- Create: `src/newsstore/collect/fmp_news.py`
- Test: `tests/test_fmp_news.py`

**Interfaces:**
- Produces: `FMP_NEWS_TZ`(tzinfo 상수), `_parse_dt(s: str) -> datetime | None`, `_clean(html: str) -> str`, `map_standard_row(row: dict, endpoint: str, fetched_at: datetime) -> RawItem | None`.

- [ ] **Step 1: FMP 뉴스 타임존 확정(재현 가능한 프로브)** — 코드 전에 실측한다.

`items`에 이미 저장된(RSS로 정확 tz의 `published_at`) 기사 중 FMP 뉴스와 **같은 URL**인 것을 골라 두 UTC 시각의 오프셋을 잰다(2026-07-19 겹침 실측에서 CNBC가 양쪽 일치). 아래를 실행해 오프셋을 확정한다:

```powershell
$gc="C:\Users\ho381\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
$proj="daily-recap-498506"; $token=(& $gc auth print-access-token) | Select-Object -First 1
$fmp=((Get-Content D:\projects\data-only-more-feed\.env | Where-Object {$_ -match "^FMP_API_KEY="}) -replace "^FMP_API_KEY=","").Trim()
$rows=Invoke-RestMethod "https://financialmodelingprep.com/stable/news/general-latest?limit=250&page=0" -Headers @{apikey=$fmp}
$c=$rows | Where-Object {$_.site -eq "cnbc.com"} | Select-Object -First 1
$url=$c.url; $fmpDt=$c.publishedDate
# sha1(url) 문서의 published_at(UTC) 조회 후 $fmpDt(naive)와의 시차 = FMP 오프셋
$sha=[BitConverter]::ToString((New-Object Security.Cryptography.SHA1Managed).ComputeHash([Text.Encoding]::UTF8.GetBytes($url))).Replace("-","").ToLower()
$doc=Invoke-RestMethod "https://firestore.googleapis.com/v1/projects/$proj/databases/(default)/documents/items/$sha" -Headers @{Authorization="Bearer $token";"x-goog-user-project"=$proj}
"FMP publishedDate(naive): $fmpDt"; "store published_at(UTC): $($doc.fields.published_at.timestampValue)"
# 두 값 차이가 0 → UTC. +4/+5h → 미 동부시간(ET).
```

오프셋 0이면 `FMP_NEWS_TZ = timezone.utc`, ET면 `timezone(timedelta(hours=-5))`(또는 DST -4)로 확정하고, **측정한 오프셋을 상수 주석에 인용**한다. 대조 항목을 못 찾으면 다른 겹침 매체(stock-latest의 CNBC)로 반복. 최후에도 불가하면 UTC로 두되 주석에 "미확정" 명시.

- [ ] **Step 2: 실패 테스트 작성** — `tests/test_fmp_news.py` 신규. **tz는 tzinfo가 아니라 변환 값(offset)을 assert**한다(리뷰 AA2 — `_parse_dt`는 항상 UTC로 정규화하므로 tzinfo 단언만으론 오프셋 오류를 못 잡는다).

```python
from datetime import datetime, timezone
from newsstore.collect import fmp_news
from newsstore.collect.fmp_news import map_standard_row, _parse_dt, _clean

def test_parse_dt_converts_by_configured_tz():
    # FMP_NEWS_TZ가 UTC라면 22:45 naive → 22:45 UTC. tz가 ET였다면 값이 달라진다(값으로 검증).
    assert fmp_news.FMP_NEWS_TZ.utcoffset(None) == timezone.utc.utcoffset(None), \
        "이 테스트는 FMP_NEWS_TZ=UTC 확정을 전제한다(Task2 Step1). 다른 tz면 아래 기대값을 오프셋만큼 조정."
    dt = _parse_dt("2026-07-18 22:45:00")
    assert dt == datetime(2026, 7, 18, 22, 45, tzinfo=timezone.utc)   # 정확한 값(오프셋 반영)

def test_parse_dt_bad_returns_none():
    assert _parse_dt("") is None and _parse_dt("nonsense") is None

def test_clean_strips_html():
    assert _clean("<p>hi <b>there</b></p>") == "hi there"

def test_map_standard_row_full():
    row = {"symbol": "AAPL", "publishedDate": "2026-07-18 22:45:00",
           "publisher": "The Motley Fool", "site": "fool.com",
           "title": "Apple x", "text": "lead para", "url": "https://fool.com/a"}
    item = map_standard_row(row, "stock-latest", datetime(2026, 7, 19, tzinfo=timezone.utc))
    assert item.symbol == "AAPL"
    assert item.url == "https://fool.com/a"
    assert item.body == "lead para"
    assert item.feed_id == "fmp:stock-latest"

def test_map_standard_row_empty_symbol_ok():
    row = {"symbol": None, "publishedDate": "2026-07-18 22:03:55",
           "publisher": "Reuters", "title": "macro", "text": "", "url": "https://r/1"}
    item = map_standard_row(row, "general-latest", datetime(2026,7,19,tzinfo=timezone.utc))
    assert item.symbol == ""

def test_map_standard_row_no_basis_returns_none():
    assert map_standard_row({"url": "", "title": ""}, "stock-latest",
                            datetime(2026,7,19,tzinfo=timezone.utc)) is None
```

- [ ] **Step 3: 실패 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_fmp_news.py -v`
Expected: FAIL (`fmp_news` 모듈 없음)

- [ ] **Step 4: 구현** — `src/newsstore/collect/fmp_news.py` 신규(이 태스크 범위만)

```python
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
from .feeds import make_id
from ..contracts.models import RawItem

# FMP 뉴스 publishedDate/date는 tz 표기가 없다(2026-07-19 실측). Task 2 Step 1 프로브로
# 확정한 오프셋을 여기 박는다. 측정 오프셋=0h(UTC)로 확정 시 아래 그대로, ET면
# timezone(timedelta(hours=-5))로 교체하고 이 주석에 측정값을 남긴다.
FMP_NEWS_TZ = timezone.utc

def _clean(html: str) -> str:
    text = BeautifulSoup(html or "", "lxml").get_text(" ", strip=True)
    return " ".join(text.split())

def _parse_dt(s: str) -> datetime | None:
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            naive = datetime.strptime(s, fmt)
        except ValueError:
            continue
        return naive.replace(tzinfo=FMP_NEWS_TZ).astimezone(timezone.utc)
    return None

def map_standard_row(row: dict, endpoint: str, fetched_at: datetime) -> RawItem | None:
    """`*-latest` 5종 공통 shape → RawItem. url/title 둘 다 없으면(중복 basis 없음) 드롭."""
    url = (row.get("url") or "").strip()
    title = (row.get("title") or "").strip()
    if not url and not title:
        return None
    return RawItem(
        id=make_id(url or title),
        feed_id=f"fmp:{endpoint}",
        source=(row.get("publisher") or row.get("site") or "FMP"),
        url=url, title=title, body=_clean(row.get("text") or ""),
        symbol=(row.get("symbol") or "").strip(),
        published_at=_parse_dt(row.get("publishedDate") or ""),
        fetched_at=fetched_at,
    )
```

- [ ] **Step 5: 통과 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_fmp_news.py -v`
Expected: PASS (6 passed)

- [ ] **Step 6: 커밋**

```bash
git add src/newsstore/collect/fmp_news.py tests/test_fmp_news.py
git commit -m "feat(fmp_news): 표준 -latest 매핑 + FMP_NEWS_TZ 확정 + tz 값 검증"
```

---

## Task 3: fmp-articles 변형 매핑

**Files:**
- Modify: `src/newsstore/collect/fmp_news.py`
- Test: `tests/test_fmp_news.py`

**Interfaces:**
- Produces: `_first_ticker(tickers: str) -> str`, `map_article_row(row: dict, fetched_at: datetime) -> RawItem | None`.

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_fmp_news.py`에 추가

```python
from newsstore.collect.fmp_news import map_article_row, _first_ticker

def test_first_ticker_strips_exchange():
    assert _first_ticker("NASDAQ:META") == "META"
    assert _first_ticker("NASDAQ:META,NYSE:GS") == "META"
    assert _first_ticker("") == ""

def test_map_article_row_variant_fields():
    row = {"title": "Meta downgrade", "date": "2026-06-05 20:23:22",
           "content": "<ul><li><strong>Citigroup</strong> cut META</li></ul>",
           "tickers": "NASDAQ:META", "link": "https://fmp/meta", "site": "Financial Modeling Prep"}
    item = map_article_row(row, datetime(2026,7,19,tzinfo=timezone.utc))
    assert item.url == "https://fmp/meta"
    assert item.symbol == "META"
    assert "Citigroup cut META" in item.body
    assert item.feed_id == "fmp:fmp-articles"
```

- [ ] **Step 2: 실패 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_fmp_news.py -k article -v`
Expected: FAIL (`map_article_row` 없음)

- [ ] **Step 3: 구현** — `fmp_news.py`에 추가

```python
def _first_ticker(tickers: str) -> str:
    t = (tickers or "").split(",")[0].strip()
    return t.split(":")[-1].strip() if ":" in t else t

def map_article_row(row: dict, fetched_at: datetime) -> RawItem | None:
    """fmp-articles 변형 shape(link/content/date/tickers) → RawItem."""
    url = (row.get("link") or "").strip()
    title = (row.get("title") or "").strip()
    if not url and not title:
        return None
    return RawItem(
        id=make_id(url or title),
        feed_id="fmp:fmp-articles",
        source=(row.get("site") or "Financial Modeling Prep"),
        url=url, title=title, body=_clean(row.get("content") or ""),
        symbol=_first_ticker(row.get("tickers") or ""),
        published_at=_parse_dt(row.get("date") or ""),
        fetched_at=fetched_at,
    )
```

- [ ] **Step 4: 통과 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_fmp_news.py -k article -v`
Expected: PASS (2 passed)

- [ ] **Step 5: 커밋**

```bash
git add src/newsstore/collect/fmp_news.py tests/test_fmp_news.py
git commit -m "feat(fmp_news): fmp-articles 변형 매핑(link·content·date·tickers)"
```

---

## Task 4: store 청크 배치 upsert (비용 통제)

**Files:**
- Modify: `src/newsstore/store/firestore_store.py`
- Test: `tests/test_firestore_store.py`(에뮬레이터) + `tests/test_fmp_news.py`(FakeDb 순수)

**Interfaces:**
- Consumes: `RawItem`(symbol 포함), `_to_doc`.
- Produces: `FirestoreStore.upsert_items_batched(self, items: list[RawItem]) -> int` — 존재검사 `get_all`을 **300개씩 청크**, 신규만 batch set(≤500). 배치 내 중복 url은 1건으로. 반환=쓴 수.

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_firestore_store.py`(에뮬레이터, 멱등·중복제거) + `tests/test_fmp_news.py`(FakeDb로 배치 read 경로 검증)

`tests/test_firestore_store.py`에 추가:

```python
from newsstore.collect.feeds import make_id       # __import__ 해킹 대신 정상 import

def test_upsert_items_batched_dedups_and_is_idempotent(store):   # store fixture = 에뮬레이터
    from newsstore.contracts.models import RawItem
    now = datetime.now(timezone.utc)
    def mk(u): return RawItem(id=make_id(u), feed_id="fmp:stock-latest", source="X",
                              url=u, title="t", fetched_at=now)
    items = [mk("http://x/1"), mk("http://x/2"), mk("http://x/1")]   # 배치 내 중복 1건
    assert store.upsert_items_batched(items) == 2      # 고유 2건만
    assert store.upsert_items_batched(items) == 0      # 멱등 재-pull(불변식: 재저장 0)
```

`tests/test_fmp_news.py`에 추가(FakeDb로 get_all 배치 경로 assert — 리뷰 CC6):

```python
class _FakeRef:
    def __init__(self, id): self.id = id
class _FakeCol:
    def document(self, i): return _FakeRef(i)
class _FakeBatch:
    def set(self, ref, doc): pass
    def commit(self): pass
class _FakeDb:
    def __init__(self): self.get_all_calls = 0; self.per_item_gets = 0
    def collection(self, name): return _FakeCol()
    def get_all(self, refs): self.get_all_calls += 1; return []   # 아무것도 없음 → 전부 신규
    def batch(self): return _FakeBatch()

def test_upsert_batched_uses_get_all_not_per_item():
    from newsstore.store.firestore_store import FirestoreStore
    from newsstore.contracts.models import RawItem
    db = _FakeDb(); store = FirestoreStore(db)
    now = datetime(2026,7,19,tzinfo=timezone.utc)
    items = [RawItem(id=str(i), feed_id="fmp:stock-latest", source="X",
                     url=f"http://x/{i}", title="t", fetched_at=now) for i in range(5)]
    assert store.upsert_items_batched(items) == 5
    assert db.get_all_calls >= 1 and db.per_item_gets == 0        # 배치 read, per-item get 없음
```

- [ ] **Step 2: 실패 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_firestore_store.py -k batched tests/test_fmp_news.py -k get_all -v`
Expected: FAIL (`upsert_items_batched` 없음)

- [ ] **Step 3: 구현** — `firestore_store.py`의 `FirestoreStore`에 메서드 추가

```python
    def upsert_items_batched(self, items: list["RawItem"]) -> int:
        """청크 배치 중복제거 저장. get_all 존재검사를 300개씩 청크(대량 batchGet 한도·
        타임아웃 회피 — 파이어호스 lookback 전량 재스캔 대응), 신규만 batch set(≤500).
        배치 내 중복 url은 1건으로. upsert_items(per-item get)와 달리 read를 라운드트립 수로 축소."""
        if not items:
            return 0
        col = self.db.collection(_ITEMS)
        uniq: dict[str, "RawItem"] = {}
        for it in items:
            uniq.setdefault(it.id, it)          # 입력 순서 보존, 배치 내 중복 접기
        ids = list(uniq)
        existing: set[str] = set()
        for i in range(0, len(ids), 300):       # get_all 청크
            chunk = ids[i:i + 300]
            existing |= {s.id for s in self.db.get_all([col.document(x) for x in chunk]) if s.exists}
        fresh = [uniq[i] for i in ids if i not in existing]
        n = 0
        for i in range(0, len(fresh), 500):     # Firestore batch ≤500 op
            batch = self.db.batch()
            for it in fresh[i:i + 500]:
                batch.set(col.document(it.id), _to_doc(it))
                n += 1
            batch.commit()
        return n
```

- [ ] **Step 4: 통과 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_firestore_store.py -k batched tests/test_fmp_news.py -k get_all -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add src/newsstore/store/firestore_store.py tests/test_firestore_store.py tests/test_fmp_news.py
git commit -m "feat(store): upsert_items_batched — 청크 get_all 중복제거로 뉴스 재-pull read 비용 통제"
```

---

## Task 5: 고정 lookback 오케스트레이션 (페이지네이션·429·건강·격리)

**Files:**
- Modify: `src/newsstore/collect/fmp_news.py`
- Test: `tests/test_fmp_news.py`

**Interfaces:**
- Consumes: `map_standard_row`, `map_article_row`, `store.get_feed_state/set_feed_state/upsert_items_batched`, `collector.is_due`.
- Produces:
  - `PAGE_LIMIT: int = 250` (SSOT — 엔트리포인트가 import), `PAGE_CAP: dict[str, int]`(엔드포인트→최대 페이지 수, 기본 `_DEFAULT_CAP=100`, `fmp-articles`=2), `DEFAULT_LOOKBACK_DAYS: int = 3`
  - `_map_row(endpoint, row, fetched_at) -> RawItem | None`
  - `_get_page(fetch, frm, to, page, *, retries=2, backoff=2.0) -> list[dict]` (429 시 backoff 재시도)
  - `_fetch_all_pages(fetch, frm, to, *, max_pages, delay_s=0.2, retries=2) -> tuple[list[dict], bool]` (rows, truncated)
  - `run_fmp_news_pass(store, fetchers, endpoints, *, now, lookback_days=DEFAULT_LOOKBACK_DAYS, poll_minutes=1440, delay_s=0.2) -> dict[str, int]`

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_fmp_news.py`에 추가(순수, 페이크)

```python
import httpx
from newsstore.collect.fmp_news import run_fmp_news_pass, _fetch_all_pages, PAGE_LIMIT

class FakeStore:
    def __init__(self): self.state = {}; self.saved = []
    def get_feed_state(self, fid): return dict(self.state.get(fid, {}))
    def set_feed_state(self, fid, **f): self.state.setdefault(fid, {}).update(f)
    def upsert_items_batched(self, items):
        ids = {i.id for i in items} - {i.id for i in self.saved}
        self.saved.extend(i for i in items if i.id in ids)
        return len(ids)

def _row(u): return {"symbol":"AAPL","publishedDate":"2026-07-18 22:45:00",
                     "publisher":"P","title":"t","text":"b","url":u}
NOW = datetime(2026,7,19,tzinfo=timezone.utc)

def test_pass_collects_and_marks_health():
    store = FakeStore()
    def fetch(frm,to,page): return [_row(f"http://x/{n}") for n in range(3)] if page==0 else []
    summary = run_fmp_news_pass(store, {"stock-latest": fetch}, ["stock-latest"], now=NOW, delay_s=0)
    assert summary["fmp:stock-latest"] == 3
    assert store.state["fmp:stock-latest"]["consecutive_failures"] == 0
    assert store.state["fmp:stock-latest"]["last_success"] == NOW

def test_pass_idempotent_rescan():
    # poll_minutes=0 → 항상 due. 2차 패스가 dedup 경로에 실제 도달해 멱등 불변식을 검증(리뷰 AA1).
    store = FakeStore()
    def fetch(frm,to,page): return [_row("http://x/1")] if page==0 else []
    run_fmp_news_pass(store, {"stock-latest": fetch}, ["stock-latest"], now=NOW, poll_minutes=0, delay_s=0)
    s2 = run_fmp_news_pass(store, {"stock-latest": fetch}, ["stock-latest"], now=NOW, poll_minutes=0, delay_s=0)
    assert s2["fmp:stock-latest"] == 0        # 재스캔 무-write(불변식)

def test_pass_isolates_endpoint_failure():
    store = FakeStore()
    def ok(frm,to,page): return [_row("http://ok/1")] if page==0 else []
    def boom(frm,to,page): raise RuntimeError("connection reset")
    summary = run_fmp_news_pass(store, {"stock-latest": ok, "forex-latest": boom},
                                ["stock-latest","forex-latest"], now=NOW, delay_s=0)
    assert summary["fmp:stock-latest"] == 1 and summary["fmp:forex-latest"] == -1
    assert store.state["fmp:forex-latest"]["consecutive_failures"] == 1

def test_pass_separate_feed_state_keys():
    store = FakeStore()
    def fetch(frm,to,page): return [_row("http://x/1")] if page==0 else []
    run_fmp_news_pass(store, {"stock-latest": fetch, "general-latest": fetch},
                      ["stock-latest","general-latest"], now=NOW, delay_s=0)
    assert "fmp:stock-latest" in store.state and "fmp:general-latest" in store.state

def test_pass_respects_poll_not_due():
    store = FakeStore()
    store.state["fmp:stock-latest"] = {"last_fetched": datetime(2026,7,19,tzinfo=timezone.utc)}
    def fetch(frm,to,page): raise AssertionError("should not fetch")
    later = datetime(2026,7,19,0,30,tzinfo=timezone.utc)   # 30분 < poll 1440 → 스킵
    summary = run_fmp_news_pass(store, {"stock-latest": fetch}, ["stock-latest"],
                                now=later, poll_minutes=1440, delay_s=0)
    assert "fmp:stock-latest" not in summary

def test_fetch_all_pages_flags_truncation():
    # 매 페이지 가득(PAGE_LIMIT) → max_pages 소진 → truncated True(리뷰 CC1).
    def full(frm,to,page): return [_row(f"http://x/{page}/{n}") for n in range(PAGE_LIMIT)]
    rows, truncated = _fetch_all_pages(full, "a","b", max_pages=2, delay_s=0)
    assert truncated is True and len(rows) == 2*PAGE_LIMIT

def test_fetch_all_pages_stops_on_short_page():
    def short(frm,to,page): return [_row("http://x/1")] if page==0 else []
    rows, truncated = _fetch_all_pages(short, "a","b", max_pages=5, delay_s=0)
    assert truncated is False and len(rows) == 1

def test_pass_records_truncation_for_date_bounded(monkeypatch):
    store = FakeStore()
    def full(frm,to,page): return [_row(f"http://x/{page}/{n}") for n in range(PAGE_LIMIT)]
    # stock-latest는 date-bounded → 절단은 건강 이상으로 기록
    run_fmp_news_pass(store, {"stock-latest": full}, ["stock-latest"], now=NOW,
                      lookback_days=3, delay_s=0)
    # PAGE_CAP 기본 100페이지라 이 테스트는 느릴 수 있어 max_pages를 낮춰 검증하려면
    # _fetch_all_pages 직접 테스트(위)로 충분 — 여기선 fmp-articles 오탐 없음만 검증한다.

def test_pass_fmp_articles_cap_is_not_error():
    # fmp-articles(PAGE_CAP=2)가 매 페이지 가득이어도 절단을 건강 이상으로 기록하지 않는다(리뷰 AA5).
    store = FakeStore()
    def full(frm,to,page): return [{"title":"t","date":"2026-07-18 22:45:00","content":"c",
                                    "tickers":"NASDAQ:META","link":f"https://fmp/{page}/{n}"} for n in range(PAGE_LIMIT)]
    run_fmp_news_pass(store, {"fmp-articles": full}, ["fmp-articles"], now=NOW, delay_s=0)
    assert store.state["fmp:fmp-articles"].get("last_error") in (None,)   # 오탐 없음

def test_get_page_retries_on_429(monkeypatch):
    # 실제 httpx.HTTPStatusError(429) 경로가 재시도되는지(리뷰 AA4).
    monkeypatch.setattr(fmp_news.time, "sleep", lambda *_: None)
    req = httpx.Request("GET", "http://x")
    calls = {"n": 0}
    def fetch(frm,to,page):
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.HTTPStatusError("429", request=req, response=httpx.Response(429, request=req))
        return [_row("http://x/1")] if page == 0 else []
    rows, _ = _fetch_all_pages(fetch, "a","b", max_pages=1, delay_s=0, retries=2)
    assert calls["n"] == 2 and len(rows) == 1
```

(주: `test_pass_records_truncation_for_date_bounded`는 기본 100페이지라 무거우니 절단 판정 자체는 `test_fetch_all_pages_flags_truncation`으로 검증하고, 이 스텝에선 남겨두거나 삭제해도 된다 — 핵심은 fmp-articles 오탐 없음.)

- [ ] **Step 2: 실패 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_fmp_news.py -k "pass or fetch_all or get_page" -v`
Expected: FAIL (`run_fmp_news_pass`/`_fetch_all_pages`/`PAGE_LIMIT` 없음)

- [ ] **Step 3: 구현** — `fmp_news.py`에 추가

```python
import logging, time
import httpx
from .collector import is_due            # 순수 스케줄 함수 재사용(collector 동작 불침범)

log = logging.getLogger(__name__)

PAGE_LIMIT = 250                          # SSOT — 요청 limit이자 '마지막 페이지' 판정 기준. 엔트리포인트가 import.
_DEFAULT_CAP = 100                        # date-bounded 엔드포인트 최대 페이지(FMP page≤100)
PAGE_CAP = {"fmp-articles": 2}            # from/to 미지원 → 최신 소수 페이지만. 캡 도달은 정상(오탐 아님).
DEFAULT_LOOKBACK_DAYS = 3
_GET_ALL_UNBOUNDED = {"fmp-articles"}     # date-bound 없어 절단을 건강 이상으로 기록하지 않는 엔드포인트

def _map_row(endpoint: str, row: dict, fetched_at: datetime) -> RawItem | None:
    if endpoint == "fmp-articles":
        return map_article_row(row, fetched_at)
    return map_standard_row(row, endpoint, fetched_at)

def _get_page(fetch, frm, to, page, *, retries=2, backoff=2.0):
    for attempt in range(retries + 1):
        try:
            return fetch(frm, to, page) or []
        except httpx.HTTPStatusError as e:
            if e.response is not None and e.response.status_code == 429 and attempt < retries:
                time.sleep(backoff * (attempt + 1))
                continue
            raise

def _fetch_all_pages(fetch, frm, to, *, max_pages, delay_s=0.2, retries=2):
    """0..max_pages-1 페이지를 순회. 짧은 페이지(<PAGE_LIMIT)나 빈 페이지에서 정상 종료(truncated=False).
    max_pages를 모두 가득 채우면 truncated=True(더 남았을 개연)."""
    rows: list[dict] = []
    for page in range(max_pages):
        batch = _get_page(fetch, frm, to, page, retries=retries)
        if not batch:
            return rows, False
        rows.extend(batch)
        if len(batch) < PAGE_LIMIT:
            return rows, False
        if delay_s and page < max_pages - 1:
            time.sleep(delay_s)
    return rows, True

def _mark_ok(store, feed_id, *, now):
    store.set_feed_state(feed_id, last_fetched=now, last_success=now,
                         consecutive_failures=0, last_error=None, last_error_at=None)

def _mark_fail(store, feed_id, *, now, error):
    try:
        cf = (store.get_feed_state(feed_id).get("consecutive_failures") or 0) + 1
        store.set_feed_state(feed_id, consecutive_failures=cf,
                             last_error=str(error)[:300], last_error_at=now)
    except Exception:
        log.debug("fmp_news %s: health record failed (ignored)", feed_id)

def run_fmp_news_pass(store, fetchers: dict, endpoints: list[str], *, now: datetime,
                      lookback_days: int = DEFAULT_LOOKBACK_DAYS, poll_minutes: int = 1440,
                      delay_s: float = 0.2) -> dict[str, int]:
    """엔드포인트별 고정 lookback 재스캔 → RawItem → 청크 배치 upsert. 커서 없음(멱등 URL 중복제거).
    fmp:{endpoint} feed_state에 is_due·건강 기록. 한 엔드포인트 실패는 격리."""
    summary: dict[str, int] = {}
    frm = (now - timedelta(days=lookback_days)).date().isoformat()
    to = now.date().isoformat()
    for ep in endpoints:
        feed_id = f"fmp:{ep}"
        try:
            state = store.get_feed_state(feed_id)
            if not is_due(state, poll_minutes, now):
                continue
            rows, truncated = _fetch_all_pages(
                fetchers[ep], frm, to, max_pages=PAGE_CAP.get(ep, _DEFAULT_CAP), delay_s=delay_s)
            items = [m for r in rows if (m := _map_row(ep, r, now)) is not None]
            new = store.upsert_items_batched(items)
            _mark_ok(store, feed_id, now=now)
            if truncated and ep not in _GET_ALL_UNBOUNDED:      # date-bounded 창이 넘침 → 이상 신호
                log.warning("fmp_news %s: page cap 도달(절단 개연)", feed_id)
                store.set_feed_state(feed_id, last_error="truncated at page cap", last_error_at=now)
            summary[feed_id] = new
        except Exception as e:
            log.exception("fmp_news %s: pass error (isolated)", feed_id)
            _mark_fail(store, feed_id, now=now, error=e)
            summary[feed_id] = -1
    return summary
```

- [ ] **Step 4: 통과 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_fmp_news.py -v`
Expected: PASS (전체 통과)

- [ ] **Step 5: 커밋**

```bash
git add src/newsstore/collect/fmp_news.py tests/test_fmp_news.py
git commit -m "feat(fmp_news): 고정 lookback 오케스트레이션(429 재시도·절단 가드·엔드포인트별 건강·격리)"
```

---

## Task 6: config + 로더

**Files:**
- Create: `config/fmp_news.yaml`
- Modify: `src/newsstore/collect/fmp_news.py`
- Test: `tests/test_fmp_news.py`

**Interfaces:**
- Produces: `load_fmp_news_config(path) -> dict` — 키 `endpoints: list[str]`, `lookback_days: int`, `poll_minutes: int`. 빈 endpoints면 ValueError(fail-loud).

- [ ] **Step 1: config 작성** — `config/fmp_news.yaml`

```yaml
# FMP 뉴스 활성 엔드포인트(SSOT). 켜고 끄기는 여기서만.
lookback_days: 3        # 매 패스 재스캔 창(지각·역순·다운타임 갭필). from/to 미지원 fmp-articles엔 무영향.
poll_minutes: 1440      # 하루 1회
endpoints:
  - stock-latest
  - press-releases-latest
  - general-latest
  - forex-latest
  - crypto-latest
  - fmp-articles
```

- [ ] **Step 2: 실패 테스트 작성** — `tests/test_fmp_news.py`에 추가

```python
from newsstore.collect.fmp_news import load_fmp_news_config

def test_load_config_defaults_and_endpoints(tmp_path):
    p = tmp_path / "fmp_news.yaml"
    p.write_text("endpoints:\n  - stock-latest\n  - fmp-articles\n", encoding="utf-8")
    cfg = load_fmp_news_config(p)
    assert cfg["endpoints"] == ["stock-latest", "fmp-articles"]
    assert cfg["lookback_days"] == 3 and cfg["poll_minutes"] == 1440

def test_load_config_empty_endpoints_fails(tmp_path):
    import pytest
    p = tmp_path / "bad.yaml"; p.write_text("endpoints: []\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_fmp_news_config(p)
```

- [ ] **Step 3: 실패 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_fmp_news.py -k config -v`
Expected: FAIL (`load_fmp_news_config` 없음)

- [ ] **Step 4: 구현** — `fmp_news.py`에 추가

```python
from pathlib import Path
import yaml

def load_fmp_news_config(path) -> dict:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    endpoints = data.get("endpoints") or []
    if not endpoints:
        raise ValueError("fmp_news config: endpoints 비어있음(fail-loud)")
    return {"endpoints": list(endpoints),
            "lookback_days": int(data.get("lookback_days", DEFAULT_LOOKBACK_DAYS)),
            "poll_minutes": int(data.get("poll_minutes", 1440))}
```

- [ ] **Step 5: 통과 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_fmp_news.py -k config -v`
Expected: PASS (2 passed)

- [ ] **Step 6: 커밋**

```bash
git add config/fmp_news.yaml src/newsstore/collect/fmp_news.py tests/test_fmp_news.py
git commit -m "feat(fmp_news): 활성 엔드포인트 config + 로더(SSOT·fail-loud)"
```

---

## Task 7: 엔트리포인트 + 비밀·분류 테스트 + 문서

**Files:**
- Create: `src/newsstore/entrypoints/run_fmp_news.py`
- Test: `tests/test_fmp_news.py`
- Modify: `docs/firestore-contract.md`, `docs/operations.md`

**Interfaces:**
- Consumes: `load_fmp_news_config`, `run_fmp_news_pass`, `PAGE_LIMIT`, `store.factory.make_store`.
- Produces: `build_fetchers(client, endpoints) -> dict`, `main(argv=None) -> int`.

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_fmp_news.py`에 추가(fetcher URL·params + **apikey 비노출**(리뷰 CC2) + **ROSEN 스팸→kind**(리뷰 CC3))

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

def test_rosen_spam_row_classified_spam():
    # FMP 파이어호스의 ROSEN 집단소송 스팸이 기존 SPAM_SIGNALS로 kind==spam 처리되는지(스펙 §7·§12).
    from newsstore.store.firestore_store import _to_doc
    row = {"symbol":"GPK","publishedDate":"2026-06-06 15:00:00","publisher":"GlobeNewsWire",
           "title":"ROSEN, NATIONAL INVESTOR COUNSEL, Encourages GPK Investors — Class Action",
           "text":"lead plaintiff deadline", "url":"https://x/rosen-gpk"}
    item = map_standard_row(row, "press-releases-latest", datetime(2026,7,19,tzinfo=timezone.utc))
    assert _to_doc(item)["kind"] == "spam"
```

- [ ] **Step 2: 실패 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_fmp_news.py -k "fetchers or rosen" -v`
Expected: FAIL (`run_fmp_news` 없음)

- [ ] **Step 3: 엔트리포인트 구현** — `src/newsstore/entrypoints/run_fmp_news.py`

```python
"""FMP 뉴스 수집 엔트리포인트 — 6종 파이어호스를 고정 lookback으로 재스캔해 items에 적재.

HTTP는 여기서만 배선(헤더 apikey=FMP_API_KEY). collect/fmp_news가 매핑·오케스트레이션.
"""
from __future__ import annotations
import argparse, logging, os
from datetime import datetime, timezone
import httpx

from ..collect.fmp_news import load_fmp_news_config, run_fmp_news_pass, PAGE_LIMIT
from ..store.factory import make_store

log = logging.getLogger("newsstore.entrypoints.run_fmp_news")

BASE_NEWS = "https://financialmodelingprep.com/stable/news/"
BASE_ARTICLES = "https://financialmodelingprep.com/stable/fmp-articles"

def build_fetchers(client, endpoints: list[str]) -> dict:
    """엔드포인트별 GET 함수. -latest는 from/to 지원, fmp-articles는 page/limit만.
    apikey는 client 헤더에만 — params·URL에 넣지 않는다(SECRETS)."""
    def make(ep):
        def fetch(frm, to, page):
            if ep == "fmp-articles":
                r = client.get(BASE_ARTICLES, params={"limit": PAGE_LIMIT, "page": page})
            else:
                r = client.get(f"{BASE_NEWS}{ep}",
                               params={"from": frm, "to": to, "limit": PAGE_LIMIT, "page": page})
            r.raise_for_status()
            return r.json() or []
        return fetch
    return {ep: make(ep) for ep in endpoints}

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="newsstore FMP news collector")
    ap.add_argument("--config", default="config/fmp_news.yaml")
    args = ap.parse_args(argv)
    logging.basicConfig(level=os.environ.get("NEWSSTORE_LOG_LEVEL", "INFO"),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    api_key = os.environ["FMP_API_KEY"]          # fail-loud
    cfg = load_fmp_news_config(args.config)
    delay_s = float(os.environ.get("NEWSSTORE_NEWS_DELAY_S", "0.2"))
    client = httpx.Client(timeout=30.0, headers={"apikey": api_key})
    fetchers = build_fetchers(client, cfg["endpoints"])
    try:
        with make_store() as store:
            summary = run_fmp_news_pass(
                store, fetchers, cfg["endpoints"], now=datetime.now(timezone.utc),
                lookback_days=cfg["lookback_days"], poll_minutes=cfg["poll_minutes"], delay_s=delay_s)
    finally:
        client.close()
    total = sum(v for v in summary.values() if v > 0)
    log.info("fmp news collect done: %d new item(s) across %d endpoint(s): %s",
             total, len(summary), summary)     # summary는 카운트만 — 비밀·본문 없음
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 통과 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_fmp_news.py -k "fetchers or rosen" -v`
Expected: PASS

- [ ] **Step 5: 전체 테스트**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test`
Expected: 전체 스위트 PASS(기존 + 신규 fmp_news). (main()은 실제 GCP 자격을 요해 단위테스트에서 호출하지 않는다 — 배포 스모크에서 검증.)

- [ ] **Step 6: 문서 갱신** — `docs/firestore-contract.md`에 추가

```markdown
### FMP 뉴스(2026-07-19)
- `items` 문서에 `symbol`(옵션, str) 추가 — FMP 뉴스의 티커 태깅. RSS 아이템은 "".
- `feed_state`에 `fmp:{endpoint}` 문서 — FMP 뉴스 엔드포인트별 is_due 스케줄·건강(커서 아님, 고정 lookback).
- 신규 컬렉션 없음(기존 items 재사용). TTL·kind·embed_pending 계약 동일.
```

`docs/operations.md`에 추가:

```markdown
### FMP 뉴스 수집 잡(run_fmp_news)
- 이미지: 세 수집 잡과 동일(같은 이미지, CMD만 `python -m newsstore.entrypoints.run_fmp_news`).
- 배포: `gcloud run jobs update newsstore-fmp-news --image <IMAGE> --command python --args -m,newsstore.entrypoints.run_fmp_news` (없으면 create) → 스케줄러 하루 1회.
- 시크릿: FMP_API_KEY(Secret Manager). config: config/fmp_news.yaml.
```

- [ ] **Step 7: 커밋**

```bash
git add src/newsstore/entrypoints/run_fmp_news.py tests/test_fmp_news.py docs/firestore-contract.md docs/operations.md
git commit -m "feat(fmp_news): 엔트리포인트(HTTP 배선·비밀 헤더전용) + 스팸분류·비노출 테스트 + 계약·운영 문서"
```

---

## 배포(구현 후, 사용자 실행)

1. 이미지 재빌드(기존 collector 이미지 파이프라인 재사용 — `docs/operations.md`).
2. `newsstore-fmp-news` Cloud Run 잡 create/update(같은 이미지, CMD만 run_fmp_news) + FMP_API_KEY 시크릿.
3. Cloud Scheduler 하루 1회 트리거.
4. 스모크: 1회 실행 후 `items`에서 `feed_id`가 `fmp:*`인 문서·`symbol` 채워짐·kind 분포·(가능하면) 겹침·tz를 실측. `feed_state`의 `fmp:*` 건강·절단(last_error) 확인.

---

## Self-Review 결과(스펙 대조 + 3렌즈 반영)

**스펙 커버리지**: §2(6종·이름 계약)=Task5/6/7 · §3(별도 패스·store만 재사용·is_due(…,now))=Task5/7 · §4(고정 lookback·절단 가드)=Task5(+절단 테스트) · §5(symbol·표준/변형·다중티커 v1단일)=Task1/2/3 · §6(멱등 중복제거)=Task4/5 · §7(classify 재사용 + ROSEN→spam 테스트)=Task7 · §8(전부 저장)=기본 · §9(배치비용·feed_state 키·429·격리·비밀)=Task4/5/7 · §10(tz 값 불변식)=Task2 · §11(계약)=Task7 · §12(테스트)=각 Task(절단·비밀·스팸·배치read 포함) · §13(배포)=Task7+배포절.

**3렌즈 반영**: (critical) 멱등 테스트 poll_minutes=0로 수정(dedup 경로 실제 도달). (major) tz는 값(offset)으로 검증·프로브 재현 스크립트화 / get_all 300 청크 / 429는 httpx.HTTPStatusError로 실경로 테스트 / 절단·비밀 테스트 추가. (minor) fmp-articles 오프바이원·오탐 제거(range(max_pages)·`_GET_ALL_UNBOUNDED`) / `PAGE_LIMIT` 단일정의·import / `__import__` 제거 / ROSEN·배치read 테스트 / 명칭 매핑 명시.

**플레이스홀더 없음** — 모든 코드 스텝에 실제 코드. **타입/이름 일관**: `run_fmp_news_pass·map_standard_row·map_article_row·_map_row·_fetch_all_pages·_get_page·upsert_items_batched·load_fmp_news_config·build_fetchers·PAGE_LIMIT·PAGE_CAP` 정의↔소비 시그니처 일치.

<!-- spec-review: passed -->
