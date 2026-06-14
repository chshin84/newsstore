# Phase C — Firestore 에뮬레이터 + store 단일화 구현 계획

> **For agentic workers:** TDD/회귀. 각 단계 그린 유지. `coding-principles` + `solved_problems` gotchas.

**Goal:** 테스트를 `mock-firestore`에서 **공식 Firestore 에뮬레이터**(Docker)로 격상하고, **sqlite 백엔드를 제거**해 store 구현을 Firestore 하나로 단일화한다.

**Architecture:** `docker compose`에 `firestore-emulator` 서비스 추가. conftest가 `FIRESTORE_EMULATOR_HOST`로 실 client를 에뮬레이터에 붙이고 테스트 간 컬렉션을 비운다. store가 필요한 모든 테스트(processor·stories·enrichment·meta·firestore_store)는 **에뮬레이터-backed FirestoreStore**를 공유 픽스처로 사용. sqlite_store·factory의 sqlite 분기·sqlite/mock 전용 테스트 제거.

**Tech Stack:** Firestore 에뮬레이터(gcloud SDK 또는 firebase-tools 이미지), google-cloud-firestore, pytest, docker compose.

**Spec:** `docs/superpowers/specs/2026-06-14-newsstore-modular-restructure-design.md` §2·§6.

> ⚠️ **리스크(에뮬레이터 미작동/Windows-Docker)**: Task 0(프리플라이트)에서 에뮬레이터+Python client 연결을 먼저 검증. 실패하면 **중단하고 사용자에게 보고**(mock 유지 옵션). 에뮬은 **복합 인덱스를 무시**하므로 인덱스 요구는 별도(실 Firestore/§D)로 검증.

---

## Task 0: 에뮬레이터 프리플라이트 (실행 가능성 먼저)
**Files:** Modify `docker-compose.yml` (emulator 서비스 임시 추가).

- [ ] **Step 1: 에뮬레이터 + 클라이언트 연결 확인**
docker-compose에 서비스 추가 (⚠️ 리뷰 교정: `:slim`엔 에뮬레이터 없음 — **`:emulators` 태그**(JRE+firestore 컴포넌트 포함) 사용. 태그 변동 가능하니 동작 확인):
```yaml
  firestore-emulator:
    image: gcr.io/google.com/cloudsdktool/cloud-sdk:emulators
    command: >
      gcloud emulators firestore start --host-port=0.0.0.0:8080
      --project=test
    ports: ["8080:8080"]
```
> 연결 전 **포트 8080 준비 대기**(sleep 말고 폴링). conftest/실행에서 readiness 확인 후 접속.
연결 스모크(test 서비스 또는 임시 run):
```bash
docker compose up -d firestore-emulator
MSYS_NO_PATHCONV=1 docker run --rm --network <compose_net> \
  -e FIRESTORE_EMULATOR_HOST=firestore-emulator:8080 -e GOOGLE_CLOUD_PROJECT=test \
  -v "D:/projects/newsstore:/app" newsstore python -c "
from google.cloud import firestore
db = firestore.Client(project='test')
db.collection('t').document('a').set({'x':1})
print('emulator roundtrip:', db.collection('t').document('a').get().to_dict())
print('empty doc to_dict:', db.collection('t').document('zzz').get().to_dict())  # None 확인
"
```
Expected: `{'x':1}` + 빈 문서 `None`(실 client 계약 — mock과 다른 그 지점).
- [ ] **Step 2: 판정** — 성공이면 Task 1 진행. **실패/불안정이면 STOP**: 사용자에게 "에뮬레이터가 이 환경에서 불안정 → mock 유지 또는 다른 방법" 보고.

---

## Task 1: compose + conftest 에뮬레이터 픽스처
**Files:** Modify `docker-compose.yml`, `tests/conftest.py`.

- [ ] **Step 1: compose 확정** — `test` 서비스에 `depends_on: [firestore-emulator]` + env `FIRESTORE_EMULATOR_HOST=firestore-emulator:8080`, `GOOGLE_CLOUD_PROJECT=test`. test 명령은 `docker compose run --rm test`로 통일(README/CLAUDE.md 테스트 명령 갱신).
- [ ] **Step 2: conftest 픽스처** — `tests/conftest.py`에 추가:
```python
import os
import pytest

@pytest.fixture
def fsclient():
    """에뮬레이터에 붙은 실 google client. 테스트 간 컬렉션 비움."""
    if not os.environ.get("FIRESTORE_EMULATOR_HOST"):
        pytest.skip("Firestore emulator not running (set FIRESTORE_EMULATOR_HOST)")
    from google.cloud import firestore
    db = firestore.Client(project=os.environ.get("GOOGLE_CLOUD_PROJECT", "test"))
    for col in ("items", "feed_state", "meta", "stories", "t"):
        for d in db.collection(col).stream():
            d.reference.delete()
    return db

@pytest.fixture
def store(fsclient):
    from newsstore.store.firestore_store import FirestoreStore
    return FirestoreStore(fsclient)
```
- [ ] **Step 3: 회귀** — `docker compose run --rm test`. 기존 통과 유지(아직 테스트 본문 안 바꿈; 신규 픽스처는 미사용이라 무영향). Expected: 103 passed.
- [ ] **Step 4: 커밋** — `test: firestore emulator service + conftest store fixture`.

---

## Task 2: FirestoreStore 테스트를 에뮬레이터로 전환
**Files:** `tests/test_firestore_store.py`, `tests/test_store_stories.py`, `tests/test_store_enrichment.py`, `tests/test_store_meta.py`.

- [ ] **Step 1: mock→에뮬레이터** — 각 파일에서 `MockFirestore()` 주입을 `store`/`fsclient` 픽스처로 교체. 예 `test_firestore_store.py`: `def _store(): return FirestoreStore(MockFirestore())` → 테스트 인자에 `store` 픽스처 사용. `from mockfirestore import MockFirestore` 제거.
  > stories/enrichment/meta 테스트가 sqlite·mock 양쪽을 돌면, mock/sqlite 케이스는 제거하고 에뮬레이터 `store` 하나로.
- [ ] **Step 2: 회귀** — `docker compose run --rm test`. 그린 유지(테스트 수는 sqlite/mock 중복 제거만큼 감소 가능).
- [ ] **Step 3: 커밋** — `test: FirestoreStore suites run against the emulator (drop mock-firestore)`.

---

## Task 3: 공용 store 사용처(processor 등) 에뮬레이터로 + sqlite 제거
**Files:** `tests/test_processor.py`(_store=SqliteStore→store 픽스처), 그 외 SqliteStore 사용 테스트. 그리고 `src/newsstore/store/sqlite_store.py`·`store/factory.py`(sqlite 분기)·`tests/test_sqlite_store.py`·`tests/test_store_factory.py` 제거.

- [ ] **Step 1: processor 픽스처 전환** — `test_processor.py`의 `_store(tmp_path)=SqliteStore(...)` → 에뮬레이터 `store` 픽스처. 테스트들이 `s.conn.execute(...)`로 sqlite 내부를 직접 읽는 부분은 **store API 또는 firestore 조회**로 변경(예: `db.collection('items').document('a').get().to_dict()`).
  > 이 단계가 가장 큼 — sqlite SQL 단언을 Firestore 조회로 다 바꿔야 함.
- [ ] **Step 2: sqlite 제거** — `git rm src/newsstore/store/sqlite_store.py tests/test_sqlite_store.py tests/test_store_factory.py`. `store/factory.py`를 firestore 전용으로 축소(또는 제거하고 엔트리포인트가 직접 FirestoreStore 구성). `make_store`의 sqlite 분기·`NEWSSTORE_BACKEND=sqlite` 기본 제거.
- [ ] **Step 3: 엔트리포인트/README/CLAUDE.md 정리** — `NEWSSTORE_BACKEND` 두 축 설명에서 sqlite 제거(또는 "로컬=에뮬레이터"로). `.env.example` 갱신.
- [ ] **Step 4: 전체 회귀** — `docker compose run --rm test`. 그린.
- [ ] **Step 5: 커밋** — `refactor: single Firestore store (drop sqlite backend); tests on emulator`.

---

## Task 4: 인덱스 계약 가드 (에뮬레이터 맹점 보완 — 리뷰 권고)
에뮬레이터는 복합 인덱스를 무시 → "쿼리는 통과하나 실 Firestore는 인덱스 요구"를 못 잡음. 코드가 쓰는 복합쿼리가 `firestore.indexes.json`에 선언됐는지 fail-loud로 가드.
**Files:** Create `tests/test_index_contract.py`.
- [ ] **Step 1: 테스트** — 코드가 요구하는 (collection, fields) 목록을 SSOT로 두고 indexes.json에 있는지 단언:
```python
import json, pathlib
REQUIRED = [   # 코드의 복합쿼리 ↔ 인덱스 (where+order_by/배열)
    ("items", ("processed", "fetched_at")),     # get_unprocessed
    ("items", ("story_id", "published_at")),     # 뷰 타임라인
    ("stories", ("status", "last_seen")),         # 카드 정렬
]
def test_required_composite_indexes_declared():
    idx = json.loads(pathlib.Path("firestore.indexes.json").read_text())
    have = {(i["collectionGroup"], tuple(f["fieldPath"] for f in i["fields"])) for i in idx["indexes"]}
    missing = [r for r in REQUIRED if r not in have]
    assert not missing, f"firestore.indexes.json에 누락된 복합 인덱스: {missing}"
```
- [ ] **Step 2: 통과 확인**(현 indexes.json에 3개 다 있음) + 실효성(REQUIRED에 가짜 추가→FAIL) 확인.
- [ ] **Step 3: 커밋** — `test: index-contract guard (code queries must be declared in indexes.json)`.

## Self-Review
- **Spec 커버리지**: §6 에뮬레이터·functional core = Task1~3 · store 단일화 = Task3.
- **리스크**: Task0 프리플라이트가 게이트. 에뮬 복합인덱스 무시는 §D(실 Firestore)에서 검증.
- **경계**: 변화는 테스트/인프라 위주. 모듈 경계 가드 계속 그린.
