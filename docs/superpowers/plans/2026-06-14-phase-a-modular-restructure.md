# Phase A — 모듈러 재구성 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (권장) 또는 executing-plans. 각 서브에이전트에 `coding-principles` + `solved_problems`의 '핵심 gotchas' 주입(`docs/subagent-context.md`).

**Goal:** 작동 중인 newsstore 백엔드를 동작 0변경으로 `contracts / collect / enrich / store / entrypoints` 모듈 경계로 재배치한다.

**Architecture:** 순수 리팩터(파일 이동 + import 재배선). 새 동작·새 테스트 없음 — **기존 테스트 101개가 매 단계 그린이어야** 한다(안전망). 공유 데이터모델·인터페이스(Protocol)를 `contracts/`로 모아 SSOT화하고, 단계별 의존을 `contracts`로만 흐르게 한다.

**Tech Stack:** Python 3.12 패키지(`src/newsstore`), pytest, Docker. 테스트: `MSYS_NO_PATHCONV=1 docker run --rm -v "D:/projects/newsstore:/app" newsstore pytest -q` (기대: **101 passed**).

**Spec:** `docs/superpowers/specs/2026-06-14-newsstore-modular-restructure-design.md` §3·§4.

---

## File Structure (이 Phase의 최종 모습)
```
src/newsstore/
  __init__.py
  contracts/__init__.py  models.py  ports.py     # RawItem / Store·LLMClient Protocol (SSOT)
  collect/__init__.py    collector.py fetcher.py parser.py feeds.py ssl_config.py
  enrich/                classify.py cluster.py tagger.py embedder.py processor.py
                         gemini.py(←llm.py) taxonomy.py
  store/                 firestore_store.py sqlite_store.py factory.py   # base.py 제거
  entrypoints/__init__.py  run_collect.py(←run.py)  run_enrich.py(←process.py)
```
> VectorIndex 포트·sqlite 제거·에뮬레이터는 **Phase B/C**(별도 계획). 이 Phase는 이동만.

각 Task = "파일 이동 → 해당 import 전부 재배선 → 전체 스위트 101 그린 → 커밋". `git mv`로 히스토리 보존.

---

## Task 1: contracts 패키지 — RawItem 이동

**Files:**
- Create: `src/newsstore/contracts/__init__.py`(빈), `src/newsstore/contracts/models.py`
- Modify: `src/newsstore/models.py`(RawItem 제거, FeedConfig·make_id만 남김 — Task 2에서 collect로 이동), 그리고 RawItem import한 전 파일.

- [ ] **Step 1: 패키지 생성 + RawItem 이동**

```bash
mkdir -p src/newsstore/contracts
: > src/newsstore/contracts/__init__.py
```
`src/newsstore/contracts/models.py` 신규(현 `models.py`의 RawItem만 옮김):
```python
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel


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
`src/newsstore/models.py`에서 RawItem 클래스 삭제(FeedConfig·make_id는 유지 — Task 2 대상).

- [ ] **Step 2: RawItem import 재배선**

전 코드/테스트에서 RawItem 출처를 contracts로 변경:
```bash
grep -rln "import RawItem\|RawItem" src tests | xargs grep -l "newsstore.models\|\.\.models\|from .models\|from newsstore.models"
```
패턴 치환(절대·상대 둘 다):
- `from newsstore.models import RawItem` → `from newsstore.contracts.models import RawItem`
- `from ..models import RawItem` → `from ..contracts.models import RawItem`
- `from .models import RawItem`(store/enrich 내부 상대) → `from ..contracts.models import RawItem`
- 혼합 import(`from ..models import RawItem`와 다른 것 같이)면 RawItem만 분리해 contracts에서.

대상(현재): `collector.py` `parser.py` `store/sqlite_store.py` `store/firestore_store.py` `store/base.py`(Protocol 시그니처) `tests/test_*`(models·firestore_store·sqlite_store·store_*·processor·embedder·tagger 등).

- [ ] **Step 3: 전체 스위트 그린 확인**

Run: `MSYS_NO_PATHCONV=1 docker run --rm -v "D:/projects/newsstore:/app" newsstore pytest -q`
Expected: **101 passed** (동작 0변경).

- [ ] **Step 4: 커밋**

```bash
git add -A && git commit -m "refactor: move RawItem to contracts/models (SSOT data model)"
```

---

## Task 2: collect 패키지 — 수집 파일 + FeedConfig/make_id 이동

**Files:**
- Create: `src/newsstore/collect/__init__.py`(빈)
- Move(git mv): `collector.py fetcher.py parser.py ssl_config.py` → `collect/`, `config.py` → `collect/feeds.py`
- Move: `models.py`의 `FeedConfig`·`make_id` → `collect/feeds.py` 상단(또는 `collect/models.py`). 비면 `models.py` 삭제.

- [ ] **Step 1: 파일 이동**
```bash
mkdir -p src/newsstore/collect && : > src/newsstore/collect/__init__.py
git mv src/newsstore/collector.py src/newsstore/collect/collector.py
git mv src/newsstore/fetcher.py   src/newsstore/collect/fetcher.py
git mv src/newsstore/parser.py    src/newsstore/collect/parser.py
git mv src/newsstore/ssl_config.py src/newsstore/collect/ssl_config.py
git mv src/newsstore/config.py    src/newsstore/collect/feeds.py
```
`FeedConfig`·`make_id`를 `models.py`에서 잘라 `collect/feeds.py` 상단에 붙이고(상대 import 정리), 빈 `models.py` 삭제: `git rm src/newsstore/models.py`.

- [ ] **Step 2: import 재배선**

치환:
- `from newsstore.collector import` → `from newsstore.collect.collector import` (fetcher/parser/ssl_config/feeds 동일).
- 상대: `from .collector import` 등은 위치 그대로면 변경 불필요(같은 패키지). `from ..config import` → `from .feeds import` / `from ..models import FeedConfig|make_id` → `from .feeds import ...`.
- `config.py`의 공개 함수명(`load_feeds`·`distinct_sources`)을 쓰는 곳: `from newsstore.config import load_feeds` → `from newsstore.collect.feeds import load_feeds`. (엔트리포인트·테스트)
- collect 내부 모듈끼리 RawItem: `from ..contracts.models import RawItem`(Task 1에서 이미).

대상: `run.py`(엔트리, Task 4에서 또 만짐) · `tests/test_collector.py test_fetcher.py test_parser.py test_config.py test_ssl_config.py test_registry_valid.py test_run.py` · `collect/*` 내부.

- [ ] **Step 3: 전체 스위트 그린**
Run: 위 pytest 명령. Expected: **101 passed**.

- [ ] **Step 4: 커밋**
```bash
git add -A && git commit -m "refactor: group RSS collection into collect/ package (feeds=ex config)"
```

---

## Task 3: contracts.ports — Store·LLMClient Protocol 이동

**Files:**
- Create: `src/newsstore/contracts/ports.py`
- Modify: `store/base.py` 삭제(Protocol 이전), `store/*`·`enrich/*`·`tests/*`의 Protocol import.
- Modify: `enrich/llm.py`에서 `LLMClient` Protocol 제거(→ports), 구현(GeminiClient·call_with_retry·LLMError)만 남김.

- [ ] **Step 1: ports.py 작성** (현 `store/base.py`의 `Store` Protocol + `enrich/llm.py`의 `LLMClient` Protocol을 통합):
```python
from __future__ import annotations
from datetime import datetime
from typing import Protocol
from .models import RawItem


class Store(Protocol):
    def upsert_items(self, items: list[RawItem]) -> int: ...
    def get_feed_state(self, feed_id: str) -> dict: ...
    def set_feed_state(self, feed_id: str, **fields) -> None: ...
    def count(self) -> int: ...
    def get_unprocessed(self, limit: int | None = None) -> list[RawItem]: ...
    def mark_processed(self, ids: list[str], processed_at: datetime | None = None) -> int: ...
    def set_meta(self, key: str, value: dict) -> None: ...
    def save_enrichment(self, item_id, *, kind, tags, embedding, story_id) -> None: ...
    def get_open_stories(self, cutoff) -> list[dict]: ...
    def create_story(self, story_id, *, title, vec, member_id, entities, now) -> None: ...
    def append_to_story(self, story_id, *, vec, member_id, entities, now) -> None: ...
    def close_stale_stories(self, cutoff) -> int: ...


class LLMClient(Protocol):
    def generate_json(self, prompt: str, *, timeout: float) -> dict: ...
    def embed(self, text: str, *, timeout: float) -> list[float]: ...
```
> docstring은 현 base.py에서 그대로 옮겨도 됨. **시그니처는 base.py와 글자 그대로** 일치시킬 것(드리프트 금지).

- [ ] **Step 2: base.py 삭제 + import 재배선**
```bash
git rm src/newsstore/store/base.py
```
- `from .base import Store` / `from newsstore.store.base import Store` → `from newsstore.contracts.ports import Store`.
- `from newsstore.enrich.llm import LLMClient` → `from newsstore.contracts.ports import LLMClient`.
- `enrich/llm.py`: `class LLMClient(Protocol)` 블록 삭제(ports로 이동). 파일 상단 `LLMClient`를 쓰는 타입힌트는 `from ..contracts.ports import LLMClient`로. GeminiClient·call_with_retry·LLMError는 그대로.
- store 구현체가 `Store`를 명시 상속/주석하면 import 갱신.

- [ ] **Step 3: 전체 스위트 그린**
Run: pytest. Expected: **101 passed**.

- [ ] **Step 4: 커밋**
```bash
git add -A && git commit -m "refactor: move Store/LLMClient Protocols to contracts/ports (SSOT interfaces)"
```

---

## Task 4: enrich/llm.py → enrich/gemini.py 리네임

**Files:** `git mv src/newsstore/enrich/llm.py src/newsstore/enrich/gemini.py` + import 갱신.

- [ ] **Step 1: 리네임**
```bash
git mv src/newsstore/enrich/llm.py src/newsstore/enrich/gemini.py
```
- [ ] **Step 2: import 재배선**
- `from newsstore.enrich.llm import GeminiClient|LLMError|call_with_retry` → `...enrich.gemini import ...`
- `from .llm import ...`(enrich 내부: tagger·embedder·processor·llm tests) → `from .gemini import ...`
- 대상: `tagger.py` `embedder.py`(LLMClient는 ports로) `processor.py` `process.py`(엔트리) `tests/test_llm_client.py`(import 경로).
- [ ] **Step 3: 전체 스위트 그린** — pytest. Expected: **101 passed**.
- [ ] **Step 4: 커밋**
```bash
git add -A && git commit -m "refactor: rename enrich/llm.py to enrich/gemini.py (impl, not interface)"
```

---

## Task 5: entrypoints — run.py/process.py 이동 + 인프라 참조 갱신

**Files:**
- Create: `src/newsstore/entrypoints/__init__.py`(빈)
- Move: `run.py` → `entrypoints/run_collect.py`, `process.py` → `entrypoints/run_enrich.py`
- Modify: `infra/Dockerfile`(CMD), `docker-compose.yml`, `infra/cloudbuild*.yaml`(불필요 시 생략), `docs/operations.md`, `README.md`의 실행 명령.

- [ ] **Step 1: 이동**
```bash
mkdir -p src/newsstore/entrypoints && : > src/newsstore/entrypoints/__init__.py
git mv src/newsstore/run.py     src/newsstore/entrypoints/run_collect.py
git mv src/newsstore/process.py src/newsstore/entrypoints/run_enrich.py
```
- [ ] **Step 2: 엔트리 내부 import 갱신**
- `run_collect.py`: `from .config import ...` → `from ..collect.feeds import load_feeds, distinct_sources`; `from .ssl_config import make_client` → `from ..collect.ssl_config import make_client`; `from .store.factory import make_store` → `from ..store.factory import make_store`; `from .collector import collect_once` → `from ..collect.collector import collect_once`.
- `run_enrich.py`: `from .enrich.* import` → `from ..enrich.* import`; `from .store.factory import make_store` → `from ..store.factory import make_store`.
- [ ] **Step 3: 실행 명령 참조 갱신(코드 아님, 문자열)**
- `infra/Dockerfile`: `CMD ["python","-m","newsstore.run","--force"]` → `CMD ["python","-m","newsstore.entrypoints.run_collect","--force"]`.
- `docker-compose.yml`: `command: python -m newsstore.run --force` → `... newsstore.entrypoints.run_collect --force`.
- `docs/operations.md`·`README.md`: `python -m newsstore.run` / `newsstore.process` 문자열을 새 경로로(`run_collect`/`run_enrich`). operations §E의 Job CMD(`-m,newsstore.process`)도 `-m,newsstore.entrypoints.run_enrich`로.
- [ ] **Step 4: 전체 스위트 그린 + 엔트리 import 스모크**
Run: `pytest`(Expected **101 passed**) + `docker run --rm -v "D:/projects/newsstore:/app" newsstore python -c "import newsstore.entrypoints.run_collect, newsstore.entrypoints.run_enrich; print('entrypoints OK')"`.
- [ ] **Step 5: 커밋**
```bash
git add -A && git commit -m "refactor: move CLIs to entrypoints/ (run_collect, run_enrich) + update infra refs"
```

---

## Task 6: 의존 경계 가드 테스트(Fail-Loud) + 최종 확인

**Files:** Create `tests/test_module_boundaries.py`

모듈 경계를 코드로 강제(원칙3·4): collect·enrich·store는 서로 import하면 안 되고 `contracts`만 의존.

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_module_boundaries.py`:
```python
import ast, pathlib

SRC = pathlib.Path("src/newsstore")
# (모듈, 금지된 형제 모듈 prefix들)
FORBIDDEN = {
    "collect": ("newsstore.enrich", "newsstore.store"),
    "enrich":  ("newsstore.collect", "newsstore.store"),
    "store":   ("newsstore.collect", "newsstore.enrich"),
}

def _imports(py: pathlib.Path):
    tree = ast.parse(py.read_text(encoding="utf-8"))
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.module:
            yield n.module
        elif isinstance(n, ast.Import):
            for a in n.names:
                yield a.name

def test_modules_only_depend_on_contracts():
    violations = []
    for mod, banned in FORBIDDEN.items():
        for py in (SRC / mod).rglob("*.py"):
            for imp in _imports(py):
                if imp.startswith(banned):
                    violations.append(f"{py} imports {imp}")
    assert not violations, "모듈 경계 위반(서로 import 금지, contracts만):\n" + "\n".join(violations)
```

- [ ] **Step 2: 실패 확인** — Run: `pytest tests/test_module_boundaries.py -q`.
  Expected: 위반이 있으면 FAIL(있다면 그 import를 contracts 경유로 고침), 없으면 바로 PASS. **PASS가 목표 상태**(경계 이미 깨끗하면 통과).
  > 통과 즉시여도 OK — 이건 드리프트 가드(불변식) 테스트. 일부러 `collect`에 `from newsstore.store...`를 넣어 FAIL 뜨는지 1회 확인 후 되돌려 실효성 검증.

- [ ] **Step 3: 전체 스위트 그린**
Run: `pytest -q`. Expected: **102 passed**(101 + 경계 테스트 1).

- [ ] **Step 4: 커밋**
```bash
git add tests/test_module_boundaries.py && git commit -m "test: module-boundary guard (collect/enrich/store depend only on contracts)"
```

---

## Self-Review (작성자 체크)
- **Spec 커버리지**: §3 모듈구조 = Task1~5 · §4 contracts(models·ports) = Task1·3 · 의존규칙("서로 import 안 함") = Task6 가드. VectorIndex·sqlite제거·에뮬레이터는 **명시적으로 Phase B/C로 이연**(범위 밖).
- **플레이스홀더**: 없음(이동은 git mv, import는 구체 패턴, 테스트는 101/102 기대값).
- **타입 일관**: ports.py의 Store/LLMClient 시그니처는 현 base.py/llm.py와 **글자 동일**(Task3 주석). RawItem 필드 불변.
- **동작 0변경**: 새 동작 없음 → 매 Task 101 그린이 회귀 게이트. Task6만 +1 테스트.
- **gotcha**: Docker bind-mount 폴백 → `MSYS_NO_PATHCONV=1` 형태 사용. `git mv`로 히스토리 보존.

## 후속 계획 (별도 문서)
- **Phase B** — VectorIndex 포트(InMemory) 도입, processor가 포트 경유.
- **Phase C** — sqlite 제거 + mock-firestore→에뮬레이터.
- **Phase D** — 인리치 Cloud Run(서울, 10분) + Scheduler + 쓰기 배치화.
