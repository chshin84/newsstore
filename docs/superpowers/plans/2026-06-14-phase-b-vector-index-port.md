# Phase B — VectorIndex 포트 구현 계획

> **For agentic workers:** TDD. 각 단계 전체 스위트 그린(현재 102) 유지. `coding-principles` + `solved_problems` gotchas 적용.

**Goal:** "열린 스토리 중 가장 가까운 것 찾기"를 `VectorIndex` 포트로 추상화하고, processor가 포트를 통해 클러스터링하게 한다. InMemory 어댑터 1개만(Firestore find_nearest는 이연).

**Architecture:** 포트(인터페이스)는 `contracts/ports`, 어댑터 `InMemoryVectorIndex`는 `enrich/`(cosine 등 클러스터 수학 사용 → store에 두면 경계 위반). processor는 인라인 candidates+best_match+assign 대신 포트(`nearest/add_story/add_member`)를 사용. 인덱스를 안 주면 process_once가 배치당 1회 store에서 구성(per-item 재조회 제거).

**Tech Stack:** Python 3.12, pytest, Docker. 테스트: `MSYS_NO_PATHCONV=1 docker run --rm -v "D:/projects/newsstore:/app" newsstore pytest -q`.

**Spec:** `docs/superpowers/specs/2026-06-14-newsstore-modular-restructure-design.md` §4·§5.

---

## Task 1: VectorIndex 포트 + InMemoryVectorIndex 어댑터

**Files:**
- Modify: `src/newsstore/contracts/ports.py` (VectorIndex Protocol 추가)
- Create: `src/newsstore/enrich/vector_index.py`
- Create: `tests/test_vector_index.py`

- [ ] **Step 1: 실패 테스트** — `tests/test_vector_index.py`:
```python
import pytest
from newsstore.enrich.vector_index import InMemoryVectorIndex

def test_nearest_above_threshold_returns_id():
    idx = InMemoryVectorIndex()
    idx.add_story("s1", [1.0, 0.0])
    assert idx.nearest([0.99, 0.01], threshold=0.9) == "s1"
    assert idx.nearest([0.0, 1.0], threshold=0.9) is None

def test_add_member_moves_centroid():
    idx = InMemoryVectorIndex()
    idx.add_story("s1", [2.0, 0.0])      # centroid [2,0]
    idx.add_member("s1", [0.0, 2.0])     # sum [2,2] / count 2 = centroid [1,1]
    # 이제 [1,1] 방향이 [1,0]보다 가까움
    assert idx.nearest([1.0, 1.0], threshold=0.99) == "s1"

def test_add_member_unknown_story_raises():
    with pytest.raises(KeyError):
        InMemoryVectorIndex().add_member("nope", [1.0])

def test_from_open_stories_seeds_centroids():
    class FakeStore:
        def get_open_stories(self, cutoff):
            return [{"id": "s1", "centroid": [1.0, 0.0], "count": 3}]
    idx = InMemoryVectorIndex.from_open_stories(FakeStore(), cutoff=None)
    assert idx.nearest([1.0, 0.0], threshold=0.99) == "s1"
```

- [ ] **Step 2: 실패 확인** — Run: `pytest -q tests/test_vector_index.py`. Expected: ImportError/Fail.

- [ ] **Step 3: 구현**

`contracts/ports.py`에 추가:
```python
class VectorIndex(Protocol):
    """열린 스토리 중심핵에 대한 최근접 검색 + 증분 갱신.
    InMemory(브루트포스) / 미래 Firestore find_nearest 가 같은 계약을 구현."""
    def nearest(self, vec: list[float], *, threshold: float) -> str | None: ...
    def add_story(self, story_id: str, vec: list[float]) -> None: ...
    def add_member(self, story_id: str, vec: list[float]) -> None: ...
```

`enrich/vector_index.py` 신규:
```python
from __future__ import annotations
from ..contracts.vectors import add_vectors
from .cluster import cosine, centroid


class InMemoryVectorIndex:
    """열린 스토리 centroid를 메모리에 들고 브루트포스 코사인으로 최근접 검색.
    entries: [{'id','centroid_sum','count'}]. 현 규모·로컬·테스트 기본 어댑터."""

    def __init__(self, entries=None):
        self._e = [dict(x) for x in (entries or [])]

    @classmethod
    def from_open_stories(cls, store, cutoff) -> "InMemoryVectorIndex":
        es = [{"id": s["id"], "count": s["count"],
               "centroid_sum": [c * s["count"] for c in s["centroid"]]}
              for s in store.get_open_stories(cutoff=cutoff)]
        return cls(es)

    def nearest(self, vec, *, threshold):
        best_id, best = None, -1.0
        for e in self._e:
            s = cosine(vec, centroid(e["centroid_sum"], e["count"]))
            if s > best:
                best, best_id = s, e["id"]
        return best_id if best >= threshold else None

    def add_story(self, story_id, vec):
        self._e.append({"id": story_id, "centroid_sum": list(vec), "count": 1})

    def add_member(self, story_id, vec):
        for e in self._e:
            if e["id"] == story_id:
                e["centroid_sum"] = add_vectors(e["centroid_sum"], list(vec))
                e["count"] += 1
                return
        raise KeyError(story_id)
```

- [ ] **Step 4: 통과 확인** — Run: `pytest -q tests/test_vector_index.py`. Expected: 4 passed.
- [ ] **Step 5: 커밋** — `feat: VectorIndex port + InMemoryVectorIndex (contracts.ports + enrich)`

---

## Task 2: processor가 VectorIndex 포트 사용

**Files:** Modify `src/newsstore/enrich/processor.py`, `src/newsstore/entrypoints/run_enrich.py`, `tests/test_processor.py`.

processor의 `candidates`(list) 인자를 `index: VectorIndex | None`로 교체. `_assign_and_persist`가 best_match/assign 대신 포트를 사용. 인덱스 미제공 시 process_once가 배치당 1회 `InMemoryVectorIndex.from_open_stories`로 구성.

- [ ] **Step 1: 실패 테스트 갱신** — `tests/test_processor.py`의 `test_cluster_pass_cache_no_tagging`를 인덱스 기반으로:
```python
def test_cluster_pass_index_no_tagging(tmp_path):
    import json
    from newsstore.enrich.vector_index import InMemoryVectorIndex
    s = _store(tmp_path)
    s.upsert_items([_item("a", "Fed raises rates sharply today"),
                    _item("b", "Fed raises rates again right now")])
    idx = InMemoryVectorIndex()
    process_once(s, _FakeClient({"Fed raises": _unit(0)}), TAX, now=NOW,
                 tag=False, index=idx)
    rows = {r["id"]: r for r in s.conn.execute(
        "SELECT id,tags,story_id,embedding FROM raw_items")}
    assert json.loads(rows["a"]["tags"]) == []
    assert rows["a"]["embedding"] is not None
    assert rows["a"]["story_id"] == rows["b"]["story_id"]   # 인덱스로 합류
    assert idx.nearest([0.0]*EMBED_DIM, threshold=-2.0) is not None  # 스토리 1개 존재
```
> 기존 `test_cluster_pass_cache_no_tagging`(candidates=cache 사용)는 삭제하고 위로 대체.

- [ ] **Step 2: 실패 확인** — Run: `pytest -q tests/test_processor.py::test_cluster_pass_index_no_tagging`. Expected: FAIL(`index` 인자 없음).

- [ ] **Step 3: 구현** — `processor.py`:
  - import 추가: `from .vector_index import InMemoryVectorIndex`, `from ..contracts.ports import LLMClient, VectorIndex`.
  - `process_once` 시그니처: `candidates: list | None = None` → `index: VectorIndex | None = None`.
  - 본문 초입(`items` 확보 후): `if index is None: index = InMemoryVectorIndex.from_open_stories(store, now - open_window)`.
  - `_assign_and_persist(store, it, vec, entities, now, threshold, open_window, candidates, id_factory)` →
```python
def _assign_and_persist(store, index, it, vec, entities, now, threshold, id_factory) -> tuple[str, bool]:
    sid = index.nearest(vec, threshold=threshold)
    if sid is None:
        sid = id_factory()
        store.create_story(sid, title=it.title, vec=vec, member_id=it.id, entities=entities, now=now)
        index.add_story(sid, vec)
        return sid, True
    store.append_to_story(sid, vec=vec, member_id=it.id, entities=entities, now=now)
    index.add_member(sid, vec)
    return sid, False
```
  - 호출부: `sid = _assign_and_persist(store, index, it, vec, entities, now, threshold, id_factory)`.
  - `assign`·`best_match` 더는 processor에서 안 씀(cluster.py에는 남겨둠 — 다른 데 미사용이면 Task 3에서 정리).

  `run_enrich.py` `_run_cluster`: candidates 시드 부분을
```python
from ..enrich.vector_index import InMemoryVectorIndex
index = InMemoryVectorIndex.from_open_stories(store, now0 - OPEN_WINDOW)
log.info("cluster pass: seeded %d open-story centroids", len(index._e))
```
  로 바꾸고, 루프의 `candidates=candidates` → `index=index`.

- [ ] **Step 4: 통과 + 전체 회귀** — Run: `pytest -q`. Expected: **이전 102에서 ±0 (test 1개 교체)** = 102 passed.
- [ ] **Step 5: 커밋** — `refactor: processor clusters via VectorIndex port (per-batch index, no per-item store query)`

---

## Task 3: 죽은 코드 정리 (assign/best_match)

**Files:** Modify `src/newsstore/enrich/cluster.py`, `tests/test_cluster.py`.

`assign`·`best_match`가 이제 InMemoryVectorIndex로 대체돼 프로덕션 미사용. 테스트만 참조하면 제거.

- [ ] **Step 1: 사용처 확인** — Run: `grep -rn "best_match\|assign(" src tests | grep -v "vector_index\|_assign_and_persist"`.
  - 프로덕션(src)에서 `assign`/`best_match` 참조 0이면 제거 대상.
- [ ] **Step 2: 제거** — `cluster.py`에서 `best_match`·`assign` 함수 삭제(cosine·centroid·DEFAULT_THRESHOLD 유지). `tests/test_cluster.py`에서 그 둘의 테스트(`test_assign_*`, `test_best_match_*`) 삭제.
  > cosine·centroid·DEFAULT_THRESHOLD는 vector_index·processor가 쓰므로 유지.
- [ ] **Step 3: 전체 회귀** — Run: `pytest -q`. Expected: assign/best_match 테스트 수만큼 감소, 나머지 그린.
- [ ] **Step 4: 커밋** — `refactor: drop assign/best_match (subsumed by InMemoryVectorIndex)`

---

## Self-Review
- **Spec 커버리지**: §4 VectorIndex 포트 = Task1 · §5 InMemory 어댑터·processor 포트경유 = Task1·2 · FirestoreVectorIndex 이연(범위 밖) 명시.
- **경계**: InMemoryVectorIndex는 enrich(클러스터 수학 사용) → store 경계 안 건드림. 포트는 contracts. 경계 가드 테스트 계속 그린.
- **동작 보존**: 클러스터 결과 동일(같은 cosine·threshold). 기본 경로가 per-item→per-batch로 *개선*(회귀 아님).
- **플레이스홀더**: 없음.
