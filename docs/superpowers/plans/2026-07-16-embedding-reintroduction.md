# 임베딩 재도입 (item_vectors) 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** story 기사를 수집 후 패스에서 gemini-embedding-001(768차원)로 임베딩해 `item_vectors/{item_id}` 컬렉션에 저장한다(스펙: `docs/superpowers/specs/2026-07-16-embedding-reintroduction-design.md`).

**Architecture:** collector 잡이 수집·저장 후 `embed_pass`(cap 500)를 돌린다. `_to_doc`가 story에만 `embed_pending: true`를 박고, 패스가 대기분을 임베딩해 벡터 저장 + 플래그 해제를 같은 batch로 커밋한다. 실패는 3분류(성공/영구/재시도)로 격리하고, 설정 드리프트(키 부재·인증 오류)는 exit 1로 fail-loud한다. 백필은 마킹 + 같은 embed_pass 반복 호출이다.

**Tech Stack:** Python 3.12 · google-genai(옵션 extra, lazy import) · google-cloud-firestore · Firestore 에뮬레이터 테스트(Docker 전용 — 로컬 Python 없음).

**전체 테스트 실행법(이 저장소 관례):** `MSYS_NO_PATHCONV=1 docker compose run --rm test` (전체), 단일 파일은 `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_X.py -q`.

**main 브랜치 참조:** embedder·gemini 클라이언트는 새로 짜지 않고 `git show ca8840a:src/newsstore/enrich/embedder.py`·`git show ca8840a:src/newsstore/enrich/gemini.py`의 검증된 코드를 축소·개조한다(아래 태스크에 개조 완료본 수록).

**파일 지도:**

| 파일 | 역할 |
|---|---|
| Create `src/newsstore/contracts/embedding.py` | EMBED_MODEL·EMBED_DIM 상수 SSOT |
| Modify `src/newsstore/contracts/ports.py` | PendingItem·VectorEntry TypedDict + Store Protocol 3메서드 |
| Modify `src/newsstore/store/firestore_store.py` | `_to_doc` embed_pending + 벡터 3메서드 |
| Create `src/newsstore/embed/__init__.py` | 빈 패키지 파일 |
| Create `src/newsstore/embed/gemini.py` | embed 전용 Gemini 클라이언트 + call_with_retry(지터·영구오류 구분) |
| Create `src/newsstore/embed/embedder.py` | embed_text + embed_items(3분류 결과) |
| Create `src/newsstore/embed/embed_pass.py` | 패스 오케스트레이션(cap·격리) |
| Modify `src/newsstore/entrypoints/run_collect.py` | 패스 배선 + 종료 코드 합성 |
| Create `src/newsstore/entrypoints/run_backfill_embed.py` | 백필(마킹 + drain 루프) — **스펙 §백필의 `scripts/backfill_embed_pending.py`에 대한 의도적 이탈**: entrypoints 관례(다른 run_*.py와 동일)를 따라야 테스트가 import할 수 있다 |
| Modify `pyproject.toml`·`infra/Dockerfile`·`infra/cloudbuild.yaml`·`docker-compose.yml`·`infra/requirements.lock` | embed extra 배선 |
| Modify `firestore.rules`·`tests/conftest.py`·`.env.example` | 규칙·픽스처·env 템플릿 |
| Modify `tests/test_module_boundaries.py` | embed 모듈 경계 추가 |
| Create `tests/test_embedder.py`·`tests/test_embed_pass.py`·`tests/test_backfill_embed.py`·`tests/test_run_collect_embed.py`·`tests/test_embed_contract.py` | 신규 테스트 |
| Modify `tests/test_firestore_store.py` | store 벡터 메서드 테스트 추가 |
| Modify `docs/firestore-contract.md`·`docs/operations.md`·`docs/setup.md`·`README.md`·`CLAUDE.md` | 계약·운영 문서 |

---

### Task 1: contracts — 상수 SSOT + ports 확장 + 모듈 경계

**Files:**
- Create: `src/newsstore/contracts/embedding.py`
- Modify: `src/newsstore/contracts/ports.py`
- Modify: `tests/test_module_boundaries.py`

- [ ] **Step 1: 모듈 경계 테스트에 embed를 추가한다(실패 테스트가 아니라 가드 확장 — embed 모듈이 store/collect를 import하면 터지게 미리 박는다)**

`tests/test_module_boundaries.py`의 `FORBIDDEN`을 다음으로 교체한다:

```python
# 각 모듈이 import하면 안 되는 형제 모듈 prefix (오직 contracts에만 의존해야 함)
FORBIDDEN = {
    "collect": ("newsstore.store",),
    "store":   ("newsstore.collect", "newsstore.embed"),
    "embed":   ("newsstore.store", "newsstore.collect"),
}
```

- [ ] **Step 2: contracts/embedding.py를 만든다**

```python
"""임베딩 계약 상수 — 단일 출처(SSOT).

모델명·차원은 다운스트림과의 계약이다(쿼리도 같은 모델·차원으로 임베딩해야 유사도
검색이 성립). embed 모듈(입력 조립·API 호출)과 store(문서 필드 주입)가 모두 여기서
도출한다 — 독립 리터럴 이중 정의 금지.
"""
EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 768          # gemini-embedding-001 기본 3072차원 → output_dimensionality로 축소
```

- [ ] **Step 3: ports.py에 TypedDict 2개와 Store 메서드 3개를 추가한다**

`FeedState` 클래스 정의 아래에 추가:

```python
class PendingItem(TypedDict):
    """get_pending_embed_items 반환 — 임베딩 입력(title·body)과 TTL 미러링(expire_at)."""
    item_id: str
    title: str
    body: str
    expire_at: datetime


class VectorEntry(TypedDict):
    """save_vectors 입력 — 호출자는 이 셋만 제공, embed_model·embedded_at은 store가 주입."""
    item_id: str
    vector: list[float]
    expire_at: datetime
```

`Store` Protocol의 `get_bars` 정의 뒤에 추가:

```python
    # 임베딩 계약(spec 2026-07-16) — item_vectors 컬렉션 + items.embed_pending 플래그.
    def get_pending_embed_items(self, limit: int) -> list[PendingItem]:
        """items where embed_pending==true 를 limit까지(대기 큐 조회)."""
        ...
    def save_vectors(self, entries: list[VectorEntry]) -> int:
        """item_vectors set + 원본 embed_pending 해제(같은 batch). embed_model·embedded_at은
        store가 주입(단일 통제점). 원본이 TTL로 사라진 항목은 건너뛴다(격리). 반환=쓴 수."""
        ...
    def clear_embed_pending(self, ids: list[str]) -> None:
        """재시도 무의미(영구 실패) 기사의 플래그 처분 — 벡터 없이 플래그만 제거."""
        ...
```

- [ ] **Step 4: 테스트 실행(기존 + 경계 가드 통과 확인)**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_module_boundaries.py -q`
Expected: PASS (embed 디렉토리가 아직 없어도 rglob이 빈 목록이라 통과)

- [ ] **Step 5: Commit**

```bash
git add src/newsstore/contracts/embedding.py src/newsstore/contracts/ports.py tests/test_module_boundaries.py
git commit -m "feat(embed): 임베딩 계약 — EMBED_MODEL/DIM SSOT + Store 포트 3메서드 + 모듈 경계"
```

---

### Task 2: store — `_to_doc`가 story에만 embed_pending을 박는다

**Files:**
- Modify: `src/newsstore/store/firestore_store.py:28-39` (`_to_doc`)
- Test: `tests/test_firestore_store.py`
- Modify: `tests/conftest.py` (item_vectors 클린업)

- [ ] **Step 1: conftest의 fsclient 클린업 컬렉션 목록에 `"item_vectors"`를 추가한다**

```python
    for col in ("items", "feed_state", "meta", "prices", "price_bars", "t",
                "income", "ratios", "prices_eod", "estimates", "profiles",
                "index_members", "index_changes", "delisted", "c1", "item_vectors"):
```

- [ ] **Step 2: 실패 테스트 작성 — tests/test_firestore_store.py 끝에 추가**

```python
# --- 임베딩 대기 플래그(spec 2026-07-16): story에만 embed_pending이 박히는가 ---

def test_to_doc_stamps_embed_pending_for_story_only(store):
    junk = RawItem(id="j2", feed_id="f", source="S", url="https://e/j2",
                   title="Rosen Law reminds investors of class action deadline",
                   body="b", fetched_at=NOW)
    good = RawItem(id="g2", feed_id="f", source="S", url="https://e/g2",
                   title="Fed holds rates steady", body="b", fetched_at=NOW)
    store.upsert_items([junk, good])
    dj = store.db.collection("items").document("j2").get().to_dict()
    dg = store.db.collection("items").document("g2").get().to_dict()
    assert dg["embed_pending"] is True           # story → 대기 플래그
    assert "embed_pending" not in dj             # 비-story → 필드 자체가 없어야 함
```

- [ ] **Step 3: 실패 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_firestore_store.py::test_to_doc_stamps_embed_pending_for_story_only -q`
Expected: FAIL (`KeyError: 'embed_pending'`)

- [ ] **Step 4: `_to_doc` 구현 — kind를 지역변수로 빼고 story에만 플래그**

```python
def _to_doc(item: RawItem) -> dict:
    # 수집 시점 kind triage: 신선 항목도 즉시 spam/digest/sports로 숨김 가능(', More' 등).
    # 백엔드가 kind의 단일 통제점 — 규칙 필터(비-LLM)라 수집 경로에서 한 번만 박는다.
    kind = classify_kind(item.title, item.body)
    doc = {
        "feed_id": item.feed_id, "source": item.source,
        "asset_hint": item.asset_hint, "language": item.language,
        "url": item.url, "title": item.title, "body": item.body,
        "published_at": item.published_at, "fetched_at": item.fetched_at,
        "kind": kind,
        # TTL: 수집 시각 기준 30일 뒤 만료. 원본은 이때까지 보존된다.
        "expire_at": item.fetched_at + _TTL,
    }
    if kind == "story":
        # 임베딩 대기 플래그 — Firestore는 '필드 없음'을 쿼리할 수 없어 플래그의 존재
        # 자체가 '대상이며 미완'을 뜻한다. 임베딩 패스가 완료 시 DELETE_FIELD로 걷는다.
        doc["embed_pending"] = True
    return doc
```

- [ ] **Step 5: 통과 확인 + 기존 스토어 테스트 회귀 없음**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_firestore_store.py -q`
Expected: 전부 PASS

- [ ] **Step 6: Commit**

```bash
git add src/newsstore/store/firestore_store.py tests/test_firestore_store.py tests/conftest.py
git commit -m "feat(embed): _to_doc가 story에만 embed_pending 대기 플래그를 박는다"
```

---

### Task 3: store — get_pending_embed_items / save_vectors / clear_embed_pending

**Files:**
- Modify: `src/newsstore/store/firestore_store.py`
- Test: `tests/test_firestore_store.py`

- [ ] **Step 1: 실패 테스트 작성 — tests/test_firestore_store.py 끝에 추가**

```python
def _story(i):
    return RawItem(id=i, feed_id="f", source="S", url=f"https://e/{i}",
                   title=f"Fed news {i}", body="b", fetched_at=NOW)


def test_get_pending_embed_items_returns_queue_with_limit(store):
    store.upsert_items([_story("p1"), _story("p2"), _story("p3")])
    got = store.get_pending_embed_items(limit=2)
    assert len(got) == 2
    one = got[0]
    assert set(one) == {"item_id", "title", "body", "expire_at"}
    assert one["expire_at"] is not None          # TTL 미러링 원천


def test_save_vectors_writes_vector_and_clears_flag(store):
    store.upsert_items([_story("v1")])
    [p] = store.get_pending_embed_items(limit=10)
    n = store.save_vectors([{"item_id": "v1", "vector": [0.1] * 768,
                             "expire_at": p["expire_at"]}])
    assert n == 1
    vec = store.db.collection("item_vectors").document("v1").get().to_dict()
    assert len(vec["vector"]) == 768
    assert vec["embed_model"] == "gemini-embedding-001"   # store가 SSOT에서 주입
    assert vec["embedded_at"] is not None
    assert vec["expire_at"] == p["expire_at"]             # 원본 TTL 미러링
    item = store.db.collection("items").document("v1").get().to_dict()
    assert "embed_pending" not in item                    # 같은 batch로 플래그 해제
    assert store.get_pending_embed_items(limit=10) == []


def test_save_vectors_skips_missing_item_and_keeps_rest(store):
    """만료 경합 격리: 원본이 사라진 항목이 나머지 벡터 저장을 막지 않는다."""
    store.upsert_items([_story("m1"), _story("m2")])
    exp = store.get_pending_embed_items(limit=10)[0]["expire_at"]
    store.db.collection("items").document("m1").delete()   # TTL 삭제 시뮬레이션
    n = store.save_vectors([
        {"item_id": "m1", "vector": [0.1] * 768, "expire_at": exp},
        {"item_id": "m2", "vector": [0.2] * 768, "expire_at": exp},
    ])
    assert n == 1                                          # m1은 스킵, m2는 저장
    assert not store.db.collection("item_vectors").document("m1").get().exists
    assert store.db.collection("item_vectors").document("m2").get().exists


def test_save_vectors_is_idempotent(store):
    store.upsert_items([_story("i1")])
    exp = store.get_pending_embed_items(limit=10)[0]["expire_at"]
    entry = {"item_id": "i1", "vector": [0.3] * 768, "expire_at": exp}
    store.save_vectors([entry])
    store.save_vectors([entry])                            # 재실행(플래그 이미 없음)
    assert store.db.collection("item_vectors").document("i1").get().exists


def test_clear_embed_pending_removes_flag_without_vector(store):
    store.upsert_items([_story("c1x")])
    store.clear_embed_pending(["c1x", "ghost-없는-id"])     # 없는 id도 조용히 스킵
    item = store.db.collection("items").document("c1x").get().to_dict()
    assert "embed_pending" not in item
    assert not store.db.collection("item_vectors").document("c1x").get().exists
```

- [ ] **Step 2: 실패 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_firestore_store.py -q -k "pending or vectors"`
Expected: FAIL (`AttributeError: ... no attribute 'get_pending_embed_items'`)

- [ ] **Step 3: firestore_store.py 구현 — 상단 상수·import에 추가**

```python
from ..contracts.embedding import EMBED_MODEL
```

컬렉션 상수(`_BARS = "price_bars"` 아래):

```python
_VECTORS = "item_vectors"
```

`get_bars` 메서드 뒤에 추가:

```python
    # ── 임베딩 계약(spec 2026-07-16) — item_vectors + embed_pending 대기 큐 ──────

    def get_pending_embed_items(self, limit: int) -> list[dict]:
        """items where embed_pending==true 를 limit까지(단일 equality — 복합 인덱스 불필요)."""
        q = self.db.collection(_ITEMS).where("embed_pending", "==", True).limit(limit)
        out = []
        for snap in q.stream():
            d = snap.to_dict() or {}
            out.append({"item_id": snap.id, "title": d.get("title") or "",
                        "body": d.get("body") or "", "expire_at": d.get("expire_at")})
        return out

    def save_vectors(self, entries: list[dict]) -> int:
        """item_vectors/{item_id} set + 원본 embed_pending 해제를 항목당 한 batch(2op)로
        커밋 — 벡터 저장과 플래그 해제가 원자적이라 부분 상태가 없다. 원본이 TTL로
        사라졌으면(NotFound) 그 항목만 건너뛴다(만료 경합 격리 — 벡터 고아 방지).
        embed_model·embedded_at은 store가 주입(단일 통제점, 계약 SSOT: contracts/embedding)."""
        if not entries:
            return 0
        from google.api_core.exceptions import FailedPrecondition, NotFound   # lazy(클라이언트 주입 유지)
        from google.cloud.firestore import DELETE_FIELD

        vec_col = self.db.collection(_VECTORS)
        items_col = self.db.collection(_ITEMS)
        now = datetime.now(timezone.utc)
        _MISSING = (NotFound, FailedPrecondition)   # update-of-missing 표면화 타입(에뮬레이터/실서버 편차 흡수)

        def _ops(batch, e):
            batch.set(vec_col.document(e["item_id"]), {
                "vector": e["vector"], "embed_model": EMBED_MODEL,
                "embedded_at": now, "expire_at": e["expire_at"]})
            batch.update(items_col.document(e["item_id"]),
                         {"embed_pending": DELETE_FIELD})

        n = 0
        for i in range(0, len(entries), 250):        # 250건 × 2op = Firestore batch 500 op 한도
            chunk = entries[i:i + 250]
            batch = self.db.batch()
            for e in chunk:
                _ops(batch, e)
            try:
                batch.commit()
                n += len(chunk)
            except _MISSING:
                # 만료 경합: batch는 원자적이라 전체 롤백됨 — 이 청크만 항목 단위로
                # 재커밋해 부재 항목만 건너뛴다(한 건이 나머지 249건을 못 날리게).
                for e in chunk:
                    b2 = self.db.batch()
                    _ops(b2, e)
                    try:
                        b2.commit()
                        n += 1
                    except _MISSING:
                        continue     # 원본 만료 — 이 항목만 스킵(벡터 고아 방지)
        return n

    def clear_embed_pending(self, ids: list[str]) -> None:
        """영구 실패 처분 — 벡터 없이 플래그만 걷는다(좀비 재시도 차단). 없는 id는 스킵."""
        from google.api_core.exceptions import NotFound
        from google.cloud.firestore import DELETE_FIELD
        col = self.db.collection(_ITEMS)
        for i in ids:
            try:
                col.document(i).update({"embed_pending": DELETE_FIELD})
            except NotFound:
                continue
```

주의: happy-path는 스펙대로 청크 batch(250건 × 2op → 런당 커밋 최대 2회)다 — 항목당 직렬 커밋 500회는 실 Firestore 왕복(30~100ms)이 얹혀 600초 예산을 갉아먹는다(플랜 리뷰 major). 만료 경합이 났을 때만 그 청크를 항목 단위로 재커밋한다(스펙의 "항목 단위 재커밋" 규칙 그대로). update-of-missing의 예외 타입은 에뮬레이터로만 검증되므로 NotFound와 FailedPrecondition을 함께 잡고, Task 11 배포 검증에서 실 서버 동작을 확인한다.

- [ ] **Step 4: 통과 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_firestore_store.py -q`
Expected: 전부 PASS

- [ ] **Step 5: Commit**

```bash
git add src/newsstore/store/firestore_store.py tests/test_firestore_store.py
git commit -m "feat(embed): store 벡터 표면 — pending 큐 조회 + 벡터 저장(원자 batch·만료 격리) + 플래그 처분"
```

---

### Task 4: embed/gemini.py — embed 전용 클라이언트 (ca8840a 개조)

**Files:**
- Create: `src/newsstore/embed/__init__.py` (빈 파일)
- Create: `src/newsstore/embed/gemini.py`
- Test: `tests/test_embedder.py` (retry 부분)

- [ ] **Step 1: 실패 테스트 작성 — tests/test_embedder.py 신규**

```python
"""embed 모듈 단위 테스트 — google-genai 없이 돈다(fake 클라이언트·lazy import)."""
import pytest


# --- call_with_retry: 일시/영구 오류 구분 (ca8840a call_with_retry 개조 계약) ---

def test_retry_transient_then_success():
    from newsstore.embed.gemini import call_with_retry
    calls = []
    def fn():
        calls.append(1)
        if len(calls) < 2:
            raise TimeoutError("slow")
        return [0.1]
    assert call_with_retry(fn, base_delay=0.0) == [0.1]
    assert len(calls) == 2


def test_retry_non_transient_raises_permanent_immediately():
    from newsstore.embed.gemini import call_with_retry, PermanentEmbedError
    calls = []
    def fn():
        calls.append(1)
        e = RuntimeError("bad request")
        e.code = 400
        raise e
    with pytest.raises(PermanentEmbedError) as ei:
        call_with_retry(fn, base_delay=0.0,
                        is_transient=lambda e: not (isinstance(getattr(e, "code", None), int)
                                                    and 400 <= e.code < 500 and e.code not in (408, 429)))
    assert len(calls) == 1                     # 재시도 없이 즉시 영구 실패
    assert ei.value.code == 400


def test_retry_exhausted_raises_llmerror():
    from newsstore.embed.gemini import call_with_retry, LLMError, PermanentEmbedError
    def fn():
        raise TimeoutError("always")
    with pytest.raises(LLMError) as ei:
        call_with_retry(fn, attempts=2, base_delay=0.0)
    assert not isinstance(ei.value, PermanentEmbedError)   # 소진 = 재시도 가능 실패
```

- [ ] **Step 2: 실패 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_embedder.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'newsstore.embed'`)

- [ ] **Step 3: `src/newsstore/embed/__init__.py`(빈 파일)와 `src/newsstore/embed/gemini.py` 작성**

```python
"""embed 전용 Gemini 클라이언트 — ca8840a enrich/gemini.py의 embed 경로 축소 복원.

개조점(스펙 2026-07-16): ① generate_json·complete 미복원(YAGNI) ② 백오프에 지터
추가(동시 50이 429에서 일제 재시도하는 폭주 방지) ③ 비일시 오류를 PermanentEmbedError
(code 보존)로 구분해 호출자가 영구/재시도를 가른다.
"""
from __future__ import annotations
import logging
import random
import time
from typing import Any, Callable

from ..contracts.embedding import EMBED_MODEL, EMBED_DIM

log = logging.getLogger("newsstore.embed.gemini")


class LLMError(RuntimeError):
    """임베딩 호출 실패(타임아웃/레이트리밋/빈 응답) — 재시도 가능 부류."""


class PermanentEmbedError(LLMError):
    """비일시 오류(4xx 비429 등) — 재시도 무의미. code로 원인 구분(400=입력, 401/403=인증)."""
    def __init__(self, msg: str, *, code: int | None = None):
        super().__init__(msg)
        self.code = code


def _status_code(e: BaseException) -> int | None:
    code = getattr(e, "code", None) or getattr(e, "status_code", None)
    return code if isinstance(code, int) else None


def call_with_retry(call_fn: Callable[[], Any], *, attempts: int = 3,
                    base_delay: float = 0.5,
                    is_transient: Callable[[BaseException], bool] | None = None) -> Any:
    """지수 백오프(+지터) retry + None 가드. 비일시 오류는 즉시 PermanentEmbedError,
    재시도 소진은 LLMError — 호출자(embedder)가 영구/재시도 처분을 가른다."""
    last: BaseException | None = None
    for i in range(attempts):
        try:
            r = call_fn()
        except Exception as e:               # transient: timeout/ratelimit/5xx
            last = e
            if is_transient is not None and not is_transient(e):
                raise PermanentEmbedError(f"non-transient embed error: {e}",
                                          code=_status_code(e)) from e
            log.warning("embed call failed (attempt %d/%d): %s", i + 1, attempts, e)
        else:
            if r is not None:
                return r
            last = LLMError("empty response")
            log.warning("embed empty response (attempt %d/%d)", i + 1, attempts)
        if i + 1 < attempts:
            time.sleep(base_delay * (2 ** i) * (1 + random.random()))   # 지터
    raise LLMError(f"embed call failed after {attempts} attempts") from last


class GeminiEmbedClient:
    """실 Gemini(google-genai). API key는 env GEMINI_API_KEY(로그/프롬프트 비노출).

    SDK는 lazy import라 google-genai 미설치 환경에서도 이 모듈 import는 가능
    (로직 테스트는 fake 클라이언트 사용)."""
    DEFAULT_TIMEOUT = 30.0

    def __init__(self, api_key: str):
        from google import genai             # lazy
        self._client = genai.Client(api_key=api_key)

    @staticmethod
    def _is_transient(e: BaseException) -> bool:
        """4xx(400/401/403/404 등)는 비일시적 → 재시도 X. 429/408/타임아웃/5xx/네트워크는 재시도."""
        code = _status_code(e)
        if code is not None and 400 <= code < 500:
            return code in (408, 429)
        return True

    def embed(self, text: str, *, timeout: float = DEFAULT_TIMEOUT) -> list[float]:
        from google.genai import types

        def _call():
            r = self._client.models.embed_content(
                model=EMBED_MODEL, contents=text,
                config=types.EmbedContentConfig(
                    output_dimensionality=EMBED_DIM,
                    # 실효 타임아웃(ms) — 행(hang)이 워커 50개를 무한 점유하면 런이
                    # 5분을 넘겨 겹실행 전제(스펙 §임베딩 패스)가 무너진다.
                    http_options=types.HttpOptions(timeout=int(timeout * 1000))))
            embs = getattr(r, "embeddings", None)
            return embs[0].values if embs else None

        return list(call_with_retry(_call, is_transient=self._is_transient))
```

(참고: 과거 코드는 embed에 HttpOptions를 걸지 않았다 — 행 방지를 위한 의도적 개조다. generate 경로가 같은 `http_options=HttpOptions(timeout=ms)` 패턴을 썼으므로 SDK 지원은 동일하다. 만약 EmbedContentConfig가 http_options를 거부하면(SDK 버전 차) 그 시점에 구현자가 genai SDK 문서로 타임아웃 경로를 확인해 대체 배선한다 — 죽은 파라미터로 방치하지 않는다.)

- [ ] **Step 4: 통과 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_embedder.py tests/test_module_boundaries.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/newsstore/embed/__init__.py src/newsstore/embed/gemini.py tests/test_embedder.py
git commit -m "feat(embed): Gemini embed 클라이언트 복원(ca8840a 축소) — 지터 백오프 + 영구오류 구분"
```

---

### Task 5: embed/embedder.py — 3분류 임베딩 (ca8840a 개조)

**Files:**
- Create: `src/newsstore/embed/embedder.py`
- Test: `tests/test_embedder.py`

- [ ] **Step 1: 실패 테스트 추가 — tests/test_embedder.py 끝에**

```python
# --- embedder: 입력 조립 + 항목별 3분류(성공/영구/재시도) ---

class FakeEmbed:
    """스크립트대로 응답하는 fake 클라이언트. script[i] = 벡터(list) 또는 예외."""
    def __init__(self, script):
        self.script = dict(script)
        self.calls = []
    def embed(self, text, *, timeout=30.0):
        self.calls.append(text)
        r = self.script[text]
        if isinstance(r, BaseException):
            raise r
        return r


def _pi(i, title, body=""):
    return {"item_id": i, "title": title, "body": body, "expire_at": None}


def test_embed_text_caps_body_at_500():
    from newsstore.embed.embedder import embed_text, BODY_CAP
    t = embed_text(_pi("a", "T", "x" * 900))
    assert t == "T " + "x" * BODY_CAP


def test_embed_items_three_way_classification():
    from newsstore.embed.embedder import embed_items
    from newsstore.embed.gemini import LLMError, PermanentEmbedError
    items = [_pi("ok1", "good"), _pi("bad-dim", "short"),
             _pi("retry1", "flaky"), _pi("perm1", "reject"), _pi("empty1", "", "")]
    fake = FakeEmbed({
        "good": [0.1] * 768,
        "short": [0.1] * 10,                                     # 차원 불일치 → 영구
        "flaky": LLMError("exhausted"),                          # 재시도 소진 → 재시도 가능
        "reject": PermanentEmbedError("bad input", code=400),    # 400 → 영구
    })
    out = embed_items(items, fake)
    assert [r.item_id for r in out] == ["ok1", "bad-dim", "retry1", "perm1", "empty1"]  # 순서 보존
    by = {r.item_id: r for r in out}
    assert by["ok1"].outcome == "ok" and len(by["ok1"].vector) == 768
    assert by["bad-dim"].outcome == "permanent"
    assert by["retry1"].outcome == "retryable"
    assert by["perm1"].outcome == "permanent"
    assert by["empty1"].outcome == "permanent"       # 빈 입력 — API 호출 없이 즉시 처분
    assert "" not in fake.calls                      # 빈 입력은 호출 안 함


def test_embed_items_auth_error_aborts_pass():
    """401/403은 항목 문제가 아니라 설정 드리프트 — 패스 전체 실패로 승격(플래그 보존)."""
    from newsstore.embed.embedder import embed_items
    from newsstore.embed.gemini import PermanentEmbedError
    fake = FakeEmbed({"a": PermanentEmbedError("unauthorized", code=401)})
    with pytest.raises(PermanentEmbedError):
        embed_items([_pi("x", "a")], fake)
```

- [ ] **Step 2: 실패 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_embedder.py -q`
Expected: 새 테스트 4개 FAIL (`ModuleNotFoundError: ... embedder`)

- [ ] **Step 3: `src/newsstore/embed/embedder.py` 작성**

```python
"""임베딩 입력 조립 + 병렬 실행 — ca8840a enrich/embedder.py 개조.

개조점(스펙 2026-07-16): 기사 단위 실패를 예외로 전파하지 않고 항목별 3분류
(성공/영구/재시도)로 돌려 embed_pass가 플래그 처분을 결정론적으로 가른다.
예외: 401/403(인증)은 항목 문제가 아니라 설정 드리프트 — 그대로 전파해 패스 전체
실패(exit 1)로 승격한다(항목별 영구 처분하면 플래그가 부당하게 걷혀 조용히 고착).
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from ..contracts.embedding import EMBED_DIM
from .gemini import PermanentEmbedError

BODY_CAP = 500
EMBED_CONCURRENCY = 50      # 병렬 임베딩 동시 호출 수 (ca8840a와 동일)

_PER_ITEM_PERMANENT_CODES = {400}    # 400=입력 문제(항목 귀속). 401/403/404 등은 패스 전체 실패.


@dataclass
class EmbedResult:
    item_id: str
    outcome: str                     # "ok" | "permanent" | "retryable"
    vector: list[float] | None = None
    reason: str = ""


def embed_text(item: dict) -> str:
    """임베딩 입력 = title + 본문(≤500자). 기사당 1회(계약 — firestore-contract.md)."""
    return f"{item['title']} {(item['body'] or '')[:BODY_CAP]}".strip()


def embed_items(items: list[dict], client,
                concurrency: int = EMBED_CONCURRENCY) -> list[EmbedResult]:
    """기사당 1회 임베딩, 병렬(순서 보존). 항목별 3분류 — 차원 불일치는 영구(fail-loud)."""
    if not items:
        return []

    def _one(it: dict) -> EmbedResult:
        text = embed_text(it)
        if not text:
            return EmbedResult(it["item_id"], "permanent", reason="empty input")
        try:
            vec = client.embed(text, timeout=30.0)
        except PermanentEmbedError as e:
            if e.code in _PER_ITEM_PERMANENT_CODES:
                return EmbedResult(it["item_id"], "permanent", reason=str(e))
            raise                     # 인증/모델명 드리프트 — 패스 전체 실패로 승격
        except Exception as e:        # LLMError(재시도 소진)·네트워크 등
            return EmbedResult(it["item_id"], "retryable", reason=str(e))
        if len(vec) != EMBED_DIM:
            return EmbedResult(it["item_id"], "permanent",
                               reason=f"dim {len(vec)} != {EMBED_DIM}")
        return EmbedResult(it["item_id"], "ok", vector=vec)

    workers = max(1, min(concurrency, len(items)))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(_one, items))   # map은 순서 보존
```

- [ ] **Step 4: 통과 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_embedder.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/newsstore/embed/embedder.py tests/test_embedder.py
git commit -m "feat(embed): embedder 복원(ca8840a 개조) — 항목별 3분류 + 인증 오류 패스 승격"
```

---

### Task 6: embed/embed_pass.py — 패스 오케스트레이션

**Files:**
- Create: `src/newsstore/embed/embed_pass.py`
- Test: `tests/test_embed_pass.py`

- [ ] **Step 1: 실패 테스트 작성 — tests/test_embed_pass.py 신규**

```python
"""embed_pass 통합 테스트 — 에뮬레이터 store + fake 클라이언트."""
from datetime import datetime, timezone
from newsstore.contracts.models import RawItem
from newsstore.embed.gemini import LLMError, PermanentEmbedError

NOW = datetime(2026, 7, 16, 7, 0, tzinfo=timezone.utc)


def _story(i, title):
    return RawItem(id=i, feed_id="f", source="S", url=f"https://e/{i}",
                   title=title, body="b", fetched_at=NOW)


class FakeEmbed:
    def __init__(self, script):
        self.script = dict(script)
    def embed(self, text, *, timeout=30.0):
        for key, r in self.script.items():
            if key in text:
                if isinstance(r, BaseException):
                    raise r
                return r
        return [0.5] * 768


def test_embed_pass_mixed_outcomes(store):
    from newsstore.embed.embed_pass import embed_pass
    store.upsert_items([_story("ok1", "Fed alpha"), _story("re1", "Fed beta"),
                        _story("pe1", "Fed gamma")])
    fake = FakeEmbed({"alpha": [0.1] * 768,
                      "beta": LLMError("exhausted"),
                      "gamma": PermanentEmbedError("bad", code=400)})
    s = embed_pass(store, fake)
    assert s == {"pending": 3, "embedded": 1, "permanent": 1, "retryable": 1}
    assert store.db.collection("item_vectors").document("ok1").get().exists
    items = store.db.collection("items")
    assert "embed_pending" not in items.document("ok1").get().to_dict()   # 성공 → 해제
    assert items.document("re1").get().to_dict()["embed_pending"] is True # 재시도 → 잔존
    assert "embed_pending" not in items.document("pe1").get().to_dict()   # 영구 → 처분
    assert not store.db.collection("item_vectors").document("pe1").get().exists


def test_embed_pass_respects_cap(store):
    from newsstore.embed.embed_pass import embed_pass
    store.upsert_items([_story(f"c{i}", f"Fed {i}") for i in range(5)])
    s = embed_pass(store, FakeEmbed({}), cap=3)
    assert s["pending"] == 3 and s["embedded"] == 3
    assert len(store.get_pending_embed_items(limit=10)) == 2   # 잔여분은 다음 런 몫


def test_embed_pass_empty_queue_noop(store):
    from newsstore.embed.embed_pass import embed_pass
    s = embed_pass(store, FakeEmbed({}))
    assert s == {"pending": 0, "embedded": 0, "permanent": 0, "retryable": 0}
```

- [ ] **Step 2: 실패 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_embed_pass.py -q`
Expected: FAIL (`ModuleNotFoundError: ... embed_pass`)

- [ ] **Step 3: `src/newsstore/embed/embed_pass.py` 작성**

```python
"""수집 후 임베딩 패스 — 대기 큐를 cap까지 임베딩(스펙 2026-07-16).

cap 근거: collector Cloud Run 잡은 task-timeout 600초·5분 주기라, 상한 없이 백필
백로그를 물면 타임아웃 반복(thrash)에 빠진다. 잔여분은 다음 런(또는 백필 drain
루프)이 이어받는다. store는 Protocol 주입(모듈 경계 — embed는 store를 import 안 함).
"""
from __future__ import annotations
import logging

from .embedder import embed_items

log = logging.getLogger("newsstore.embed")

DEFAULT_CAP = 500


def embed_pass(store, client, cap: int = DEFAULT_CAP) -> dict:
    """반환: {"pending": 이번에 읽은 대기 수, "embedded": 저장 수,
    "permanent": 영구 실패(플래그 처분) 수, "retryable": 재시도 예정 수}."""
    pending = store.get_pending_embed_items(limit=cap)
    if not pending:
        return {"pending": 0, "embedded": 0, "permanent": 0, "retryable": 0}
    expire_by_id = {p["item_id"]: p["expire_at"] for p in pending}
    results = embed_items(pending, client)
    entries = [{"item_id": r.item_id, "vector": r.vector,
                "expire_at": expire_by_id[r.item_id]}
               for r in results if r.outcome == "ok"]
    permanent = [r for r in results if r.outcome == "permanent"]
    retryable = [r for r in results if r.outcome == "retryable"]
    embedded = store.save_vectors(entries)
    if permanent:
        store.clear_embed_pending([r.item_id for r in permanent])
        for r in permanent:
            log.error("embed permanent failure %s: %s (pending cleared, no vector)",
                      r.item_id, r.reason)
    for r in retryable:
        log.warning("embed retryable failure %s: %s (retried next run)",
                    r.item_id, r.reason)
    return {"pending": len(pending), "embedded": embedded,
            "permanent": len(permanent), "retryable": len(retryable)}
```

- [ ] **Step 4: 통과 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_embed_pass.py tests/test_module_boundaries.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/newsstore/embed/embed_pass.py tests/test_embed_pass.py
git commit -m "feat(embed): embed_pass — cap 상한 + 3분류 처분(저장/재시도 잔존/영구 처분)"
```

---

### Task 7: run_collect 배선 — 수집 격리 + 종료 코드 합성

**Files:**
- Modify: `src/newsstore/entrypoints/run_collect.py`
- Test: `tests/test_run_collect_embed.py`

- [ ] **Step 1: 실패 테스트 작성 — tests/test_run_collect_embed.py 신규**

```python
"""run_collect 임베딩 배선 — 키 부재 fail-loud(대기분 있을 때만) + 수집 보존.

에뮬레이터에 붙어 main()을 통째로 돌린다(피드 0개 yaml — 수집은 no-op).
"""
from datetime import datetime, timezone
from newsstore.contracts.models import RawItem
from newsstore.entrypoints.run_collect import main

NOW = datetime(2026, 7, 16, 7, 0, tzinfo=timezone.utc)


def _feeds_yaml(tmp_path):
    p = tmp_path / "feeds.yaml"
    p.write_text("feeds: []\n", encoding="utf-8")
    return str(p)


def test_missing_key_with_pending_exits_1(store, tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    store.upsert_items([RawItem(id="p1", feed_id="f", source="S", url="https://e/p1",
                                title="Fed news", body="b", fetched_at=NOW)])
    assert main(["--feeds", _feeds_yaml(tmp_path)]) == 1


def test_missing_key_without_pending_exits_0(store, tmp_path, monkeypatch):
    """키 없는 로컬 수집 스모크를 깨지 않는다 — 대기 0건이면 경고 후 정상 종료."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert main(["--feeds", _feeds_yaml(tmp_path)]) == 0


def test_embed_wholesale_failure_preserves_collection_and_exits_1(store, tmp_path, monkeypatch):
    """패스 전체 실패(더미 키 → 클라이언트 생성/인증 실패)여도 수집 결과는 저장돼 있다."""
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-invalid-key")
    store.upsert_items([RawItem(id="p2", feed_id="f", source="S", url="https://e/p2",
                                title="Fed news 2", body="b", fetched_at=NOW)])
    assert main(["--feeds", _feeds_yaml(tmp_path)]) == 1
    assert store.db.collection("items").document("p2").get().exists   # 수집 보존
    d = store.db.collection("items").document("p2").get().to_dict()
    assert d["embed_pending"] is True                                 # 플래그 보존(재시도 가능)
```

종료 코드 합성의 피드 축도 검증한다(스펙 테스트 목록 — 피드 실패율 OR 임베딩 실패). 같은 파일에 추가:

```python
def test_feed_failure_rate_exits_1_even_without_embed_issues(store, tmp_path, monkeypatch):
    """합성의 피드 축 — 임베딩이 무사(키 없음·대기 0건)해도 피드 실패율 초과면 exit 1."""
    import newsstore.entrypoints.run_collect as rc
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(rc, "collect_once", lambda *a, **k: {"f1": -1})   # 전 피드 실패 주입
    assert rc.main(["--feeds", _feeds_yaml(tmp_path)]) == 1
```

(세 번째 테스트의 실패 경로: 테스트 이미지에는 google-genai가 없어 lazy import가 `ModuleNotFoundError`를 내고, genai가 설치된 환경이면 더미 키 인증 401이 `PermanentEmbedError`로 승격된다 — 어느 쪽이든 "패스 전체 실패 → exit 1" 경로다.)

- [ ] **Step 2: 실패 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_run_collect_embed.py -q`
Expected: FAIL (main이 임베딩 없이 0을 반환 → 1·2번째 assert 실패)

- [ ] **Step 3: run_collect.py 수정 — collect 후 임베딩 패스 배선**

`collect_once` 블록(`with make_store() as store:` 내부, 요약 로그 뒤)에 추가하고 반환부를 합성한다. 수정 후 `main` 전문:

```python
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="newsstore collector (one pass)")
    ap.add_argument("--feeds", default="config/feeds.yaml")
    ap.add_argument("--force", action="store_true", help="ignore poll intervals (fetch all)")
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=os.environ.get("NEWSSTORE_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    feeds = load_feeds(args.feeds)
    client = make_client()
    embed_failed = False
    with make_store() as store:                  # Firestore(에뮬레이터 or 실)
        # SSOT: 사이트 소스 목록·tier를 feeds.yaml에서 도출해 기록 (하드코딩 X). tier 전파 #17.
        store.set_meta("sources", {"sources": distinct_sources(feeds),
                                   "tiers": source_tiers(feeds)})
        try:
            summary = collect_once(client, store, feeds, force=args.force)
        finally:
            client.close()

        total_new = sum(v for v in summary.values() if v > 0)
        failed = [k for k, v in summary.items() if v == -1]
        attempted = len(summary)      # skipped (not-due) feeds are absent from summary
        log.info("collected %d new item(s); store total = %d", total_new, store.count())
        for fid, n in sorted(summary.items()):
            log.info("  %s: %s", fid, "FAIL" if n == -1 else n)

        # ── 임베딩 패스(스펙 2026-07-16) — 수집과 격리: 여기 실패해도 수집분은 이미 저장됨.
        # 키 부재 fail-loud는 '대기분 실재'로 좁힌다(키 없는 로컬 수집 스모크 보존).
        api_key = os.environ.get("GEMINI_API_KEY")
        try:
            if api_key:
                from ..embed.gemini import GeminiEmbedClient
                from ..embed.embed_pass import embed_pass
                es = embed_pass(store, GeminiEmbedClient(api_key))
                log.info("embed pass: pending=%d embedded=%d permanent=%d retryable=%d",
                         es["pending"], es["embedded"], es["permanent"], es["retryable"])
            elif store.get_pending_embed_items(limit=1):
                log.error("GEMINI_API_KEY missing but embed_pending items exist "
                          "(embedding stalled — set the secret)")
                embed_failed = True
            else:
                log.warning("GEMINI_API_KEY not set; no pending embeds — skipping embed pass")
        except Exception:
            log.exception("embed pass failed (collection results preserved)")
            embed_failed = True

    if attempted and len(failed) / attempted >= FAIL_RATE_ALERT:
        log.error("run FAILED: %d/%d feeds failed (>= %.0f%%): %s",
                  len(failed), attempted, FAIL_RATE_ALERT * 100, ", ".join(sorted(failed)))
        return 1
    if failed:
        log.warning("%d feed(s) failed (isolated): %s", len(failed), ", ".join(sorted(failed)))
    return 1 if embed_failed else 0
```

- [ ] **Step 4: 통과 확인 + 기존 수집 테스트 회귀 없음**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_run_collect_embed.py tests/test_collector.py tests/test_smoke.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/newsstore/entrypoints/run_collect.py tests/test_run_collect_embed.py
git commit -m "feat(embed): run_collect 배선 — 수집 격리 임베딩 패스 + 종료 코드 합성(키 부재는 대기분 있을 때만 fail)"
```

---

### Task 8: 백필 entrypoint — 마킹 + drain 루프

**Files:**
- Create: `src/newsstore/entrypoints/run_backfill_embed.py`
- Test: `tests/test_backfill_embed.py`

- [ ] **Step 1: 실패 테스트 작성 — tests/test_backfill_embed.py 신규**

```python
"""백필 — 레거시(플래그 없는) story 문서 마킹 + drain 루프(무진전 가드)."""
from datetime import datetime, timezone, timedelta

NOW = datetime.now(timezone.utc)


def _legacy_doc(db, i, *, kind="story", life=timedelta(days=20)):
    """배포 전 저장된(embed_pending 없는) 문서를 직접 기록해 레거시를 시뮬레이션."""
    db.collection("items").document(i).set({
        "title": f"t{i}", "body": "b", "kind": kind,
        "fetched_at": NOW, "expire_at": NOW + life,
    })


def test_mark_pending_selects_unembedded_fresh_stories(store):
    from newsstore.entrypoints.run_backfill_embed import mark_pending
    db = store.db
    _legacy_doc(db, "L1")                                     # 대상
    _legacy_doc(db, "L2", kind="spam")                        # 비-story → 제외
    _legacy_doc(db, "L3")                                     # 벡터 이미 있음 → 제외
    db.collection("item_vectors").document("L3").set({"vector": [0.1] * 768})
    _legacy_doc(db, "L4", life=timedelta(days=1))             # 잔여 수명 <2일 → 제외
    assert mark_pending(store) == 1
    assert db.collection("items").document("L1").get().to_dict()["embed_pending"] is True
    for i in ("L2", "L3", "L4"):
        assert "embed_pending" not in db.collection("items").document(i).get().to_dict()


def test_mark_pending_is_idempotent(store):
    from newsstore.entrypoints.run_backfill_embed import mark_pending
    _legacy_doc(store.db, "L5")
    assert mark_pending(store) == 1
    assert mark_pending(store) == 0        # 재실행 — 이미 마킹된 것은 추가 마킹 없음


class AlwaysRetryable:
    def embed(self, text, *, timeout=30.0):
        from newsstore.embed.gemini import LLMError
        raise LLMError("persistent transient")


def test_drain_stops_after_no_progress(store):
    """재시도 가능 실패만 계속 나오면 무한 루프 대신 무진전 2회에서 멈춘다."""
    from newsstore.entrypoints.run_backfill_embed import drain
    from newsstore.contracts.models import RawItem
    store.upsert_items([RawItem(id="d1", feed_id="f", source="S", url="https://e/d1",
                                title="Fed", body="b", fetched_at=NOW)])
    totals = drain(store, AlwaysRetryable(), cap=10)
    assert totals["embedded"] == 0
    assert len(store.get_pending_embed_items(limit=10)) == 1   # 플래그는 남아 정규 런 몫


def test_drain_drains_to_zero(store):
    from newsstore.entrypoints.run_backfill_embed import drain
    from newsstore.contracts.models import RawItem

    class OkEmbed:
        def embed(self, text, *, timeout=30.0):
            return [0.1] * 768

    store.upsert_items([RawItem(id=f"d{i}", feed_id="f", source="S", url=f"https://e/d{i}",
                                title=f"Fed {i}", body="b", fetched_at=NOW) for i in range(5)])
    totals = drain(store, OkEmbed(), cap=2)          # cap<대기 — 여러 라운드에 걸쳐 소진
    assert totals["embedded"] == 5
    assert store.get_pending_embed_items(limit=10) == []
```

- [ ] **Step 2: 실패 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_backfill_embed.py -q`
Expected: FAIL (`ModuleNotFoundError: ... run_backfill_embed`)

- [ ] **Step 3: `src/newsstore/entrypoints/run_backfill_embed.py` 작성**

```python
"""일회성 백필(스펙 2026-07-16): 레거시 story 기사에 embed_pending을 마킹하고,
정규 embed_pass를 반복 호출(drain)해 즉시 소진한다 — 임베딩 경로는 한 벌(SSOT).

로컬(Docker)에서 실행한다: Cloud Run task-timeout 제약이 없다.
  MSYS_NO_PATHCONV=1 docker compose run --rm collect \
    python -m newsstore.entrypoints.run_backfill_embed
멱등: 이미 벡터가 있거나 마킹된 기사는 건너뛴다. 재실행 안전.
"""
from __future__ import annotations
import argparse
import logging
import os
from datetime import datetime, timezone, timedelta

from ..embed.embed_pass import embed_pass, DEFAULT_CAP
from ..store.factory import make_store

log = logging.getLogger("newsstore.backfill_embed")

MIN_LIFE = timedelta(days=2)     # 잔여 수명 2일 미만은 제외 — 곧 만료될 벡터에 쿼터 낭비 방지
_MARK_CHUNK = 250                # Firestore batch 500 op 한도 내(update 1op씩)


def mark_pending(store, *, min_life: timedelta = MIN_LIFE) -> int:
    """kind==story ∧ 벡터 없음 ∧ 미마킹 ∧ 잔여 수명 ≥ min_life 에 embed_pending 마킹.
    select 프로젝션으로 본문 다운로드를 피한다(일회성이지만 read 페이로드 절약)."""
    now = datetime.now(timezone.utc)
    db = store.db
    snaps = list(db.collection("items").where("kind", "==", "story")
                 .select(["expire_at", "embed_pending"]).stream())
    marked = 0
    for i in range(0, len(snaps), _MARK_CHUNK):
        chunk = snaps[i:i + _MARK_CHUNK]
        refs = [db.collection("item_vectors").document(s.id) for s in chunk]
        have_vector = {r.id for r in db.get_all(refs) if r.exists}
        batch = db.batch()
        pending_ops = 0
        for s in chunk:
            d = s.to_dict() or {}
            if s.id in have_vector or d.get("embed_pending"):
                continue
            exp = d.get("expire_at")
            if exp is None or exp - now < min_life:
                continue
            batch.update(s.reference, {"embed_pending": True})
            pending_ops += 1
        if pending_ops:
            batch.commit()
            marked += pending_ops
    return marked


def drain(store, client, *, cap: int = DEFAULT_CAP) -> dict:
    """embed_pass를 대기분 0까지 반복. 무진전(저장·처분 0) 2회 연속이면 중단하고
    잔여분을 로그로 남긴다 — 잔여분은 정규 5분 주기 런이 이어받는다."""
    totals = {"embedded": 0, "permanent": 0}
    stall = 0
    while True:
        s = embed_pass(store, client, cap=cap)
        totals["embedded"] += s["embedded"]
        totals["permanent"] += s["permanent"]
        if s["pending"] == 0:
            break
        if s["embedded"] + s["permanent"] == 0:
            stall += 1
            if stall >= 2:
                log.error("drain: no progress after 2 rounds; %d pending remain "
                          "(regular runs will retry)", s["pending"])
                break
        else:
            stall = 0
        log.info("drain round: embedded=%d permanent=%d retryable=%d",
                 s["embedded"], s["permanent"], s["retryable"])
    return totals


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="backfill embed_pending + drain (one-off)")
    ap.add_argument("--cap", type=int, default=DEFAULT_CAP, help="embed_pass 라운드당 상한")
    args = ap.parse_args(argv)
    logging.basicConfig(level=os.environ.get("NEWSSTORE_LOG_LEVEL", "INFO"),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        log.error("GEMINI_API_KEY required for backfill")
        return 1
    from ..embed.gemini import GeminiEmbedClient   # lazy — genai 설치 환경에서만
    with make_store() as store:
        marked = mark_pending(store)
        log.info("marked %d legacy story item(s) for embedding", marked)
        totals = drain(store, GeminiEmbedClient(api_key), cap=args.cap)
        log.info("backfill done: embedded=%d permanent=%d", totals["embedded"], totals["permanent"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 통과 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_backfill_embed.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/newsstore/entrypoints/run_backfill_embed.py tests/test_backfill_embed.py
git commit -m "feat(embed): 백필 entrypoint — 레거시 마킹(수명 가드) + drain 루프(무진전 2회 중단)"
```

---

### Task 9: 인프라 배선 — extra·Dockerfile·compose·cloudbuild·rules·env·lock

**Files:**
- Modify: `pyproject.toml`, `infra/Dockerfile`, `infra/cloudbuild.yaml`, `docker-compose.yml`, `firestore.rules`, `.env.example`, `infra/requirements.lock`
- Test: `tests/test_embed_contract.py`

- [ ] **Step 1: 실패 테스트 작성 — tests/test_embed_contract.py 신규**

```python
"""임베딩 인프라 계약 가드(FAIL-LOUD) — 규칙·배선이 조용히 빠지는 드리프트를 터뜨린다."""
import pathlib
import re


def test_item_vectors_public_read_rule_declared():
    rules = pathlib.Path("firestore.rules").read_text(encoding="utf-8")
    assert re.search(r"match /item_vectors/\{id\}\s*\{\s*allow read: if true; "
                     r"allow write: if false;", rules), \
        "firestore.rules에 item_vectors 공개 read 규칙이 없다"


def test_embed_extra_wired_into_prod_image():
    """스펙 재리뷰 critical: extra 선언만으로는 프로덕션에 설치되지 않는다 — 배선 3점 가드."""
    assert '"google-genai' in pathlib.Path("pyproject.toml").read_text(encoding="utf-8")
    dockerfile = pathlib.Path("infra/Dockerfile").read_text(encoding="utf-8")
    assert "INSTALL_EMBED" in dockerfile
    cloudbuild = pathlib.Path("infra/cloudbuild.yaml").read_text(encoding="utf-8")
    assert "INSTALL_EMBED=true" in cloudbuild
    lock = pathlib.Path("infra/requirements.lock").read_text(encoding="utf-8")
    assert "google-genai==" in lock
```

- [ ] **Step 2: 실패 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_embed_contract.py -q`
Expected: FAIL 2건

- [ ] **Step 3: 배선 6개 파일 수정**

`pyproject.toml`의 optional-dependencies:

```toml
[project.optional-dependencies]
dev = ["pytest>=8.2"]
gcp = ["google-cloud-firestore>=2.16"]
# 임베딩(embed 모듈)은 lazy import — extra 미설치 환경에서도 import·테스트 가능.
embed = ["google-genai>=1.0"]
```

`infra/Dockerfile` — ARG 블록에 추가(`ARG INSTALL_GCP=false` 아래):

```dockerfile
# 임베딩(gemini) — collector 이미지용. lock -c 는 버전 제약일 뿐 설치 트리거가 아니므로
# extra를 명시 설치해야 한다(스펙 2026-07-16 재리뷰 critical).
ARG INSTALL_EMBED=false
```

RUN의 EXTRAS 조립에 한 줄 추가(INSTALL_GCP 줄 아래):

```dockerfile
    if [ "$INSTALL_EMBED" = "true" ]; then EXTRAS="${EXTRAS:+$EXTRAS,}embed" ; fi ; \
```

`infra/cloudbuild.yaml` — args에 추가(INSTALL_GCP=true 뒤):

```yaml
      - --build-arg
      - INSTALL_EMBED=true
```

`docker-compose.yml` — `collect` 서비스의 build args에 추가:

```yaml
      args:
        INSTALL_DEV: "false"
        INSTALL_GCP: "true"       # 실 Firestore 접속(run_collect) — firestore 라이브러리 필수
        INSTALL_EMBED: "true"     # 임베딩 패스(gemini) — 백필 실행도 이 서비스로
```

(test 서비스는 embed 미설치 유지 — lazy import 속성이 실제로 지켜지는지 테스트 환경 자체가 증명한다.)

`firestore.rules` — `match /delisted/...` 줄 아래에 추가:

```
    match /item_vectors/{id}     { allow read: if true; allow write: if false; }
```

`.env.example` — FMP 블록 아래에 추가:

```
# ── Gemini (임베딩 전용) — 백엔드 전용 비밀. 절대 커밋·클라이언트 노출 금지 ──
# story 기사 임베딩(item_vectors). 없으면 임베딩 패스만 멈춘다(대기분 있으면 run이 exit 1).
# 프로덕션은 Secret Manager(gemini-api-key) 주입. 아래 값은 플레이스홀더 — 실 키로 교체하라.
GEMINI_API_KEY=your-gemini-api-key-here
```

- [ ] **Step 4: requirements.lock 재생성 (Docker로 — 로컬 Python 없음)**

```bash
MSYS_NO_PATHCONV=1 docker compose run --rm -T test sh -c "pip install -q -e '.[dev,gcp,embed]' >/dev/null 2>&1 && pip freeze --exclude-editable" > /tmp/req.lock
```

(install 출력을 /dev/null로 버려 freeze 외 줄이 lock에 섞이는 오염을 막는다. 교체 전 `/tmp/req.lock`이 `패키지==버전` 줄만인지 확인한다 — 비-패키지 줄이 섞이면 `-c` 파싱이 깨진다.)

생성물 확인 후 `infra/requirements.lock`을 교체하되, 헤더 2줄을 다음으로 갱신해 유지한다:

```
# Full pip freeze (transitive deps included) — Dockerfile이 -c(constraints)로 사용.
# 재생성: docker compose run --rm -T test sh -c "pip install -q -e '.[dev,gcp,embed]' && pip freeze --exclude-editable"
```

`google-genai==`가 lock에 들어왔는지 확인한다.

- [ ] **Step 5: 이미지 재빌드 + 전체 테스트 통과 확인**

```bash
MSYS_NO_PATHCONV=1 docker compose build
MSYS_NO_PATHCONV=1 docker compose run --rm test
```

Expected: 전체 PASS (기존 121 + 신규)

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml infra/Dockerfile infra/cloudbuild.yaml docker-compose.yml firestore.rules .env.example infra/requirements.lock tests/test_embed_contract.py
git commit -m "feat(embed): 인프라 배선 — embed extra(프로덕션 설치 경로 포함)·rules 공개 read·env 템플릿 + 계약 가드"
```

---

### Task 10: 문서 갱신 — 계약·운영·셋업·스코프

**Files:**
- Modify: `docs/firestore-contract.md`, `docs/operations.md`, `docs/setup.md`, `README.md`, `CLAUDE.md`

- [ ] **Step 1: firestore-contract.md 갱신**

컬렉션 개요 표에 행 추가(price_bars 행 아래):

```markdown
| `item_vectors` | collect Job(임베딩 패스) | 공개(다운스트림) | 있음(`expire_at` — **원본 item 미러링**) | story 기사 임베딩 벡터(768차원) — 기사와 함께 만료 |
```

TTL 규칙 절의 첫 불릿에 미러링 예외 추가(price_bars 서술 뒤에 이어서):

```markdown
**`item_vectors`는 원본 item의 `expire_at`을 그대로 미러링**한다(기사와 벡터가 함께 만료 — 고아 벡터 방지). 이 컬렉션만 호출자(임베딩 패스)가 원본에서 읽은 값을 전달하고, `embed_model`·`embedded_at`은 store가 주입한다.
```

컬렉션 스키마 절에 추가(`prices` 스키마 앞):

```markdown
### `item_vectors` (collect Job의 임베딩 패스가 기록, 공개 read)
story 기사당 벡터 1문서. 문서 키 = item id. **분석이 아니라 수집 시점 1회 계산**이다(생성형 LLM 아님 — 스코프 예외).
- **필드**: `vector`(float×768), `embed_model`("gemini-embedding-001" — store가 SSOT 주입), `embedded_at`, `expire_at`(원본 미러링).
- **임베딩 입력 규칙(계약)**: `title + " " + body[:500]`. 모델·차원과 함께 다운스트림 계약이다 — 유사도 검색 쿼리도 같은 모델·차원·규칙으로 임베딩해야 한다. 상수 SSOT: `src/newsstore/contracts/embedding.py`.
- **모델 교체는 단방향 문**: 다운스트림이 이 계약에 의존하면 교체 시 전량 재임베딩 + 다운스트림 협응이 필요하다. `embed_model` 필드가 mismatch 감지 수단.

### `items.embed_pending` (transient 플래그)
`_to_doc`가 story에만 `embed_pending: true`를 박고, 임베딩 패스가 완료 시 `DELETE_FIELD`로 걷는다(영구 실패도 처분 시 걷는다 — 좀비 재시도 방지). Firestore가 "필드 없음"을 쿼리할 수 없어 플래그 존재 = 대기를 뜻한다. **공개 read인 items에 임베딩 전까지 노출되는 백엔드 상태 필드**다 — 경미한 노출은 수용 결정(웹 파서는 미지 필드 무시).
```

Store 표면 절에 추가:

```markdown
- `get_pending_embed_items(limit)`, `save_vectors(entries)`, `clear_embed_pending(ids)` — 임베딩 대기 큐·벡터 저장(원자 batch + 만료 격리)·영구 실패 처분. 타입 계약은 `contracts/ports.py`의 `PendingItem`·`VectorEntry`.
```

인프라 절의 공개 read 컬렉션 나열에 `item_vectors` 추가.

- [ ] **Step 2: operations.md 갱신**

머리말 비밀 불릿(FMP 줄) 아래에 추가:

```markdown
- collector 잡은 `GEMINI_API_KEY`(백엔드 전용 비밀)를 **Secret Manager**(`gemini-api-key`)로 주입한다(임베딩 패스). prices·factors 잡에는 넣지 않는다.
```

collector 잡 절(§뉴스 수집 근처)에 추가:

```markdown
### 임베딩 패스 (collector 잡 내)
- 수집 후 `embed_pass`가 story 대기분(`embed_pending`)을 런당 500건까지 임베딩해 `item_vectors`에 쓴다. Gemini 장애는 수집을 막지 않고, 실패분은 다음 5분 런이 재시도한다.
- **키 부재 + 대기분 존재 = run 실패(exit 1)** — 조용한 무임베딩 고착을 스케줄러가 감지한다.
- 시크릿 재발급: `printf '%s' "<NEW_GEMINI_API_KEY>" | gcloud secrets versions add gemini-api-key --data-file=-`
- **배포 직후 실측(MEASURE-FIRST)**: 첫 백필 런 로그에서 (collect 소요 + embed 소요) < task-timeout 600초를 확인하고, 넘치면 `embed_pass` cap을 낮춘다.

### 임베딩 백필 (일회성 — 배포 직후)
로컬 Docker로 실행한다(Cloud Run 타임아웃 제약 없음). 멱등 — 재실행 안전.
```

```bash
MSYS_NO_PATHCONV=1 docker compose run --rm collect python -m newsstore.entrypoints.run_backfill_embed
```

TTL 프로비저닝 절(§F)의 컬렉션 목록에 `item_vectors`를 추가한다.

- [ ] **Step 3: setup.md 갱신**

§7 TTL 컬렉션 목록에 `item_vectors` 추가. §8(시크릿) FMP 아래에:

```markdown
- **Gemini 키(임베딩)**: `gcloud secrets create gemini-api-key --replication-policy=automatic` 후 `printf '%s' "<GEMINI_API_KEY>" | gcloud secrets versions add gemini-api-key --data-file=-`. collector 잡에 주입: `gcloud run jobs update newsstore-collector --set-secrets=GEMINI_API_KEY=gemini-api-key:latest --region=<REGION>` (setup.md의 기존 `<REGION>` 플레이스홀더 관례를 따른다)
```

(잡 이름·리전 변수 표기는 setup.md의 기존 서술 관례에 맞춘다 — 실제 잡 이름이 다르면 §리소스 인벤토리를 따른다.)

- [ ] **Step 4: README.md·CLAUDE.md 스코프 문장 정정**

CLAUDE.md의 스코프 불릿에서 `LLM/분석/신호/리포트는 이 repo에 없다(...)` 문장을 다음으로 교체:

```markdown
**생성형 LLM/분석/신호/리포트는 이 repo에 없다**(태깅·클러스터·스토리·렌즈·프레임·리포트·레이더 전부 제거). **단 하나의 예외 — 임베딩 벡터 계산**: 수집 후 패스가 story 기사를 gemini-embedding-001(768차원)로 임베딩해 `item_vectors`에 저장한다(다운스트림 재사용 — 분석이 아니라 수집 산출물).
```

README.md의 대응 문장(스코프/아키텍처 서술)도 같은 취지로 정정하고, 컬렉션 나열에 `item_vectors`를 추가한다(README의 기존 서술 형식을 따른다).

- [ ] **Step 5: 문서 리뷰(reviewer-grounding+fit — 프로젝트 관례) 후 Commit**

```bash
git add docs/firestore-contract.md docs/operations.md docs/setup.md README.md CLAUDE.md
git commit -m "docs(embed): 계약·운영·셋업·스코프 — item_vectors/embed_pending 계약 + 시크릿·백필·TTL 절차"
```

---

### Task 11: 전체 검증 + 배포·백필 (배포는 사용자 확인 후)

- [ ] **Step 1: 전체 테스트**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test`
Expected: 전부 PASS, FAIL=0

- [ ] **Step 2: 로컬 엔드투엔드 스모크(실 키 — .env에 있음)**

```bash
MSYS_NO_PATHCONV=1 docker compose build collect
MSYS_NO_PATHCONV=1 docker compose run --rm collect
```

Expected: 수집 로그 뒤 `embed pass: pending=N embedded=N ...` — 실 Firestore `item_vectors`에 문서 생성 확인(콘솔 또는 웹 대시보드 아님 — gcloud/콘솔로 확인).

- [ ] **Step 3: 배포 절차(사용자와 함께 — operations.md대로)**

1. 시크릿 생성 + collector 잡에 주입(setup.md §8 추가분).
2. 이미지 재빌드(cloudbuild — INSTALL_EMBED=true 포함) → 세 잡 update(같은 이미지) → collector execute.
3. `item_vectors` TTL 정책 활성화(gcloud fields ttl update).
4. firestore.rules 배포(Firebase REST — `x-goog-user-project` 헤더).
5. 백필 실행(로컬 Docker) 후 소진 확인.
6. **실측(MEASURE-FIRST)**: collector 런 로그에서 (collect 소요 + 임베딩 소요 + save_vectors 커밋) < 600초를 확인한다(넘치면 cap 하향). 만료 경합 예외 타입(NotFound/FailedPrecondition)이 실 서버에서 스킵으로 처리되는지도 백필 로그에서 확인한다.

- [ ] **Step 4: 오답노트** — 구현 중 얻은 재사용 교훈이 있으면 `docs/solved_problems.md`에 append.

<!-- spec-review: passed -->
