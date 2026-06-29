# news-analytics 통합 (gray-band 클러스터링 이식 + 분석 로드맵 이관) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** news-analytics의 검증된 gray-band 클러스터링을 newsstore `src/`로 이식(cross-repo 의존성 0)해 newsstore 자체 단일-임계값 클러스터링을 대체하고, 분석 능력 로드맵을 newsstore 문서로 이관한다.

**Architecture:** 통합 우선 전략(2026-06-29) — news-analytics 알고리즘을 newsstore 소스로 vendoring(F1 0.821 검증 코드를 verbatim 보존, 임포트 경로만 조정). 순수 로직 + DI(임베더·LLM 주입) 설계 유지 → 미래 재분리 용이. 새 분석 능력(impact·risk·델타·렌즈·brief)은 도면만 이관, 통합 개발은 후속.

**Tech Stack:** Python 3.12, Docker-only(`MSYS_NO_PATHCONV=1 docker compose run --rm test` = Firestore 에뮬레이터 + pytest). 클러스터링: `gemini-embedding-001`/768 임베딩 + `gemini-3.1-flash-lite-preview` gray-band LLM(둘 다 주입). 새 의존성 없음.

**Source(이식 원천, GitHub `@main` = 로컬 검증본 `249aa3d`):** `D:\projects\news-analytics\src\news_analytics\{clustering.py,contracts.py,config.py}` + `tests/`. *원천은 참조용 — 알고리즘 verbatim 복사, 로직 변경 금지.*

**핵심 gotchas:**
- **알고리즘 verbatim** — clustering.py 로직(gray-band·union-find·top-k·_merge)은 F1 검증됨. 임포트 경로만 바꾸고 로직은 건드리지 않는다(버그 주입 금지).
- **mock/실제 None 차이** — fake LLM이 `{}`/`[]` 줘도 실 SDK는 `None`. `complete`는 `call_with_retry` None 가드.
- **테스트 매직넘버 금지** — 불변식(같은 사건→같은 id, 다른 사건→다른 id)으로 검증.
- **비파괴** — `append_to_story`/`save_enrichment` merge. 옛 코드(cluster.py 등) 삭제는 **대체 검증 후**(Phase D).

**명령:** 특정 테스트 `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/X.py -v` · 전체 `MSYS_NO_PATHCONV=1 docker compose run --rm test`

---

## File Structure

| 파일 | 책임 | 변경 |
|---|---|---|
| `src/newsstore/enrich/clustering_types.py` | `Article`·`Story` dataclass (이식) | Create |
| `src/newsstore/enrich/clustering.py` | gray-band 알고리즘 (이식, config 인라인) | Create |
| `src/newsstore/enrich/cluster_adapter.py` | RawItem/dict ↔ Article/Story + embed·llm 주입 | Create |
| `src/newsstore/enrich/gemini.py` | `GeminiClient.complete` 평문 | Modify |
| `src/newsstore/contracts/ports.py` | `LLMClient.complete` + `get_open_stories` docstring | Modify |
| `src/newsstore/store/firestore_store.py` | `get_open_stories` title·centroid_sum | Modify |
| `src/newsstore/enrich/processor.py` | 배정 → gray-band | Modify |
| `src/newsstore/entrypoints/run_enrich.py` | 어댑터 배선, threshold 제거 | Modify |
| `src/newsstore/enrich/cluster.py`, `vector_index.py` | (대체 후 삭제) | Delete (Phase D) |
| `tests/test_clustering.py` | 클러스터링 단위(이식) | Create |
| `tests/test_cluster_adapter.py` | 어댑터 단위 | Create |
| `tests/test_gemini_complete.py` | complete 단위 | Create |
| `tests/test_processor.py`, `test_firestore_store.py` | 갱신 | Modify |
| `tests/test_vector_index.py`, `test_cluster*.py` | (Phase D 정리) | Delete (Phase D) |
| `docs/analysis-roadmap.md` | 분석 능력 로드맵·방법론(이관) | Create |
| `docs/firestore-contract.md`, `CLAUDE.md` | 통합 현실 반영 | Modify (Phase E) |
| 보류 cutover spec/plan, handoff 2종 | 삭제/슬림 | Delete (Phase E) |

---

## Phase A — 코드 이식 (새 의존성 0)

### Task 1: `clustering_types.py` — Article·Story 이식

**Files:** Create `src/newsstore/enrich/clustering_types.py`, Test `tests/test_clustering_types.py`

- [ ] **Step 1: 실패 테스트**

`tests/test_clustering_types.py`:
```python
def test_article_and_story_defaults():
    from newsstore.enrich.clustering_types import Article, Story
    a = Article(id="x", title="t", body="b", source="S", published_at="2026-06-29")
    assert a.tags == () and a.embedding is None
    s = Story(id="s", title="t")
    assert s.centroid_sum is None and s.status == "open" and s.member_ids == ()
```

- [ ] **Step 2: 실패 확인** — `... pytest tests/test_clustering_types.py -v` → FAIL (ModuleNotFound)

- [ ] **Step 3: 이식**

`D:\projects\news-analytics\src\news_analytics\contracts.py`의 `Article`·`Story` dataclass와 `LLMClient`·`Clusterer` Protocol을 **verbatim 복사**해 `src/newsstore/enrich/clustering_types.py` 생성(모듈 docstring은 "news-analytics에서 이식(2026-06-29)"로 조정). import는 stdlib(`dataclasses`, `typing`)만이라 경로 변경 불필요.

- [ ] **Step 4: 통과 확인** — PASS

- [ ] **Step 5: Commit** — `git add ... && git commit -m "feat(enrich): vendor Article/Story types from news-analytics"`

### Task 2: `clustering.py` — gray-band 알고리즘 이식

**Files:** Create `src/newsstore/enrich/clustering.py`, Test `tests/test_clustering.py`

- [ ] **Step 1: 실패 테스트(news-analytics 단위 이식 + 불변식)**

`tests/test_clustering.py`:
```python
from newsstore.enrich.clustering import EventClusterer, cluster_articles
from newsstore.enrich.clustering_types import Article, Story


class _LLM:
    def __init__(self, verdict="DIFFERENT", boom=False):
        self.verdict, self.boom, self.calls = verdict, boom, 0
    def complete(self, prompt, *, timeout=30.0):
        self.calls += 1
        if self.boom:
            raise RuntimeError("down")
        return self.verdict


def _art(i, vec):
    return Article(id=i, title=f"t{i}", body="b", source="S", published_at="2026-06-29",
                   embedding=tuple(vec))


def test_assign_deterministic_join_identical():
    llm = _LLM()
    c = EventClusterer(embed=lambda t: [[0.0, 0.0]], llm=llm)
    s = Story(id="s1", title="x", centroid_sum=(1.0, 0.0))
    assert c.assign(_art("a", [1.0, 0.0]), [s]) == "s1" and llm.calls == 0


def test_assign_deterministic_new_orthogonal():
    llm = _LLM()
    c = EventClusterer(embed=lambda t: [[0.0, 0.0]], llm=llm)
    s = Story(id="s1", title="x", centroid_sum=(1.0, 0.0))
    assert c.assign(_art("a", [0.0, 1.0]), [s]) is None and llm.calls == 0


def test_assign_gray_band_same_joins():
    llm = _LLM("SAME")
    c = EventClusterer(embed=lambda t: [[0.0, 0.0]], llm=llm)
    s = Story(id="s1", title="x", centroid_sum=(1.0, 0.0))
    assert c.assign(_art("a", [0.83, 1.0]), [s]) == "s1" and llm.calls == 1


def test_assign_gray_band_llm_error_failsoft_new():
    llm = _LLM(boom=True)
    c = EventClusterer(embed=lambda t: [[0.0, 0.0]], llm=llm)
    s = Story(id="s1", title="x", centroid_sum=(1.0, 0.0))
    assert c.assign(_art("a", [0.83, 1.0]), [s]) is None


def test_cluster_articles_merges_same_event():
    # 배치: 동일 벡터 2건 → 같은 cluster_id (gray-band 안 걸림, cos=1.0)
    llm = _LLM()
    out = cluster_articles([_art("a", [1.0, 0.0]), _art("b", [1.0, 0.0])],
                           embed=lambda t: [[0.0, 0.0]] * len(t), llm=llm)
    assert out["a"] == out["b"]
```

- [ ] **Step 2: 실패 확인** — FAIL (ModuleNotFound)

- [ ] **Step 3: 이식(verbatim + config 인라인)**

`D:\projects\news-analytics\src\news_analytics\clustering.py`를 `src/newsstore/enrich/clustering.py`로 **verbatim 복사**하되 **정확히 세 곳만 변경**:

(a) 22행 `from .config import DBSTREAM_PARAMS, GRAY_BAND, LLM_CALL_CAP_RATIO, TOP_K` 삭제 → 상단에 상수 인라인:
```python
# Vendored from news-analytics @249aa3d (2026-06-29). config.py 상수 인라인.
# gray-band 경계 [lo, hi]: sim>=hi 결정론 합류 / sim<lo 결정론 신규 / 그 사이만 LLM 판정.
# (이란+코스피 골든셋 + gemini-embedding-001/768로 측정된 값 — newsstore 코퍼스 재캘리브레이션은 후속.)
GRAY_BAND: tuple[float, float] = (0.55, 0.75)
LLM_CALL_CAP_RATIO: float = 0.2          # 배치 런당 LLM 콜 상한(docs 대비 비율)
TOP_K: int = 8                            # 후보 top-k(머지 판정 대상)
DBSTREAM_PARAMS: dict = {"clustering_threshold": 1.0, "fading_factor": 0.01,
                         "cleanup_interval": 2.0, "intersection_factor": 0.3,
                         "minimum_weight": 1.0}
```
(b) 24행 로거 개명: `logging.getLogger("news_analytics.clustering")` → `logging.getLogger("newsstore.enrich.clustering")` (네임스페이스 정합 — 안 바꾸면 로그가 엉뚱한 네임스페이스로 나감).

(c) 모듈 docstring 상단에 1줄 추가: `news-analytics @249aa3d에서 이식(2026-06-29). _default_embedder/_default_base_cluster(river·sentence-transformers, DBSTREAM_PARAMS)는 newsstore 주입 경로에선 미사용 — eval/미래용 보존.`

그 외 로직(EventClusterer·cluster_articles·_merge·_cosine·_UF·gray-band)은 **한 줄도 바꾸지 않는다**(F1 검증 코드 — 변형 금지). river/sentence-transformers는 함수 내부 lazy import라 주입 경로(우리 사용)에선 호출 안 됨 → 새 의존성 불필요.

- [ ] **Step 4: 통과 확인** — `... pytest tests/test_clustering.py -v` → PASS (5 passed). gray-band 코사인 0.64 검증은 cutover 플랜과 동일 방식.

- [ ] **Step 5: Commit** — `git commit -m "feat(enrich): vendor gray-band clustering algorithm from news-analytics (F1 0.821)"`

### Task 3: `cluster_adapter.py` — 경계 어댑터(내부)

**Files:** Create `src/newsstore/enrich/cluster_adapter.py`, Test `tests/test_cluster_adapter.py`

- [ ] **Step 1: 실패 테스트**

`tests/test_cluster_adapter.py`:
```python
from newsstore.contracts.models import RawItem
from newsstore.enrich import cluster_adapter


class _Client:
    def __init__(self, verdict="DIFFERENT"):
        self.verdict = verdict
    def embed(self, text, *, timeout=30.0):
        return [0.0, 0.0]
    def complete(self, prompt, *, timeout=30.0):
        return self.verdict


def _item(i):
    return RawItem(id=i, feed_id="f", source="S", url=f"https://e/{i}", title=f"t{i}", body="b")


def _row(sid, csum):
    return {"id": sid, "title": "x", "centroid_sum": list(csum),
            "centroid": list(csum), "count": 1}


def test_to_stories_maps_centroid_sum():
    [s] = cluster_adapter.to_stories([_row("s1", [1.0, 0.0])])
    assert s.id == "s1" and tuple(s.centroid_sum) == (1.0, 0.0)


def test_assign_join_identical():
    cl = cluster_adapter.build_clusterer(_Client())
    open_stories = cluster_adapter.to_stories([_row("s1", [1.0, 0.0])])
    assert cluster_adapter.assign(cl, _item("a"), [1.0, 0.0], open_stories) == "s1"


def test_assign_new_orthogonal():
    cl = cluster_adapter.build_clusterer(_Client())
    open_stories = cluster_adapter.to_stories([_row("s1", [1.0, 0.0])])
    assert cluster_adapter.assign(cl, _item("a"), [0.0, 1.0], open_stories) is None
```

- [ ] **Step 2: 실패 확인** — FAIL

- [ ] **Step 3: 구현**

`src/newsstore/enrich/cluster_adapter.py`:
```python
"""클러스터링 경계 어댑터 — newsstore 데이터(RawItem/스토리 dict) ↔ clustering Article/Story
매핑 + embed·llm 주입. 알고리즘은 clustering.py 소유(여기엔 로직 없음)."""
from __future__ import annotations

from .clustering import EventClusterer
from .clustering_types import Article, Story
from ..contracts.models import RawItem
from ..contracts.ports import LLMClient


def build_clusterer(client: LLMClient) -> EventClusterer:
    def embed(texts: list[str]) -> list[list[float]]:
        return [client.embed(t) for t in texts]
    return EventClusterer(embed=embed, llm=client)


def to_article(item: RawItem, vec) -> Article:
    return Article(id=item.id, title=item.title, body=item.body or "",
                   source=item.source, published_at=str(item.published_at or ""),
                   tags=(), embedding=tuple(vec))


def to_stories(rows) -> list[Story]:
    return [Story(id=r["id"], title=r.get("title") or "",
                  centroid_sum=tuple(r["centroid_sum"]))
            for r in rows if r.get("centroid_sum")]


def assign(clusterer: EventClusterer, item: RawItem, vec, open_stories) -> str | None:
    return clusterer.assign(to_article(item, vec), open_stories)
```

- [ ] **Step 4: 통과 확인** — PASS

- [ ] **Step 5: Commit** — `git commit -m "feat(enrich): cluster_adapter (map + inject) for vendored clustering"`

---

## Phase B — 배선 컷오버

### Task 4: `GeminiClient.complete` + Protocol

**Files:** Modify `src/newsstore/enrich/gemini.py:69`, `src/newsstore/contracts/ports.py:64-66`. Test `tests/test_gemini_complete.py`

- [ ] **Step 1: 실패 테스트** — (cutover 플랜 Task 2와 동일)

`tests/test_gemini_complete.py`:
```python
import types as _t
from newsstore.enrich.gemini import GeminiClient


def _client(responses):
    c = GeminiClient.__new__(GeminiClient)
    c._model = "m"; c._embed_model = "e"; c._embed_dim = 768
    seq = iter(responses)
    def generate_content(*, model, contents, config):
        return _t.SimpleNamespace(text=next(seq))
    c._client = _t.SimpleNamespace(models=_t.SimpleNamespace(generate_content=generate_content))
    return c


def test_complete_returns_plain_text():
    assert _client(["SAME\nx"]).complete("p").startswith("SAME")


def test_complete_none_guard_retries():
    assert _client([None, "DIFFERENT"]).complete("p").startswith("DIFFERENT")
```

- [ ] **Step 2: 실패 확인** — FAIL (no attribute 'complete')

- [ ] **Step 3: 구현** — `gemini.py`의 `generate_json`(69행) 앞에 추가:
```python
    def complete(self, prompt: str, *, timeout: float = DEFAULT_TIMEOUT) -> str:
        """평문 생성(JSON mime 없이). gray-band LLM(llm.complete)용. None 가드 재사용."""
        from google.genai import types

        def _call():
            r = self._client.models.generate_content(
                model=self._model, contents=prompt,
                config=types.GenerateContentConfig(
                    http_options=types.HttpOptions(timeout=int(timeout * 1000))))
            return getattr(r, "text", None)

        return call_with_retry(_call, is_transient=self._is_transient)
```

- [ ] **Step 4: Protocol** — `ports.py`의 `LLMClient`(64-66행)에 `def complete(self, prompt: str, *, timeout: float) -> str: ...` 추가.

- [ ] **Step 5: 통과 확인** — PASS

- [ ] **Step 6: Commit** — `git commit -m "feat(enrich): GeminiClient.complete (plain-text) for gray-band LLM"`

### Task 5: `get_open_stories` title·centroid_sum 확장

**Files:** Modify `src/newsstore/store/firestore_store.py:71-79`, `ports.py:38-40`. Test `tests/test_firestore_store.py`

- [ ] **Step 1: 실패 테스트** — (cutover 플랜 Task 4와 동일)
```python
def test_get_open_stories_includes_title_and_centroid_sum(store):
    from datetime import datetime, timezone, timedelta
    now = datetime(2026, 6, 29, tzinfo=timezone.utc)
    store.create_story("s1", title="Fed move", vec=[1.0, 2.0], member_id="a",
                       entities=["Fed"], now=now)
    store.append_to_story("s1", vec=[3.0, 0.0], member_id="b", entities=[], now=now)
    [row] = store.get_open_stories(cutoff=now - timedelta(hours=1))
    assert row["title"] == "Fed move" and row["centroid_sum"] == [4.0, 2.0]
    assert row["centroid"] == [2.0, 1.0] and row["count"] == 2
```

- [ ] **Step 2: 실패 확인** — FAIL

- [ ] **Step 3: 구현** — `get_open_stories`(71-79행) 교체:
```python
    def get_open_stories(self, cutoff) -> list[dict]:
        out = []
        for snap in self.db.collection("stories").where("status", "==", "open").stream():
            d = snap.to_dict() or {}
            if d.get("last_seen") and d["last_seen"] >= cutoff:
                csum = list(d.get("centroid_sum", []))
                c = d.get("count", 1) or 1
                out.append({"id": snap.id, "title": d.get("title") or "",
                            "centroid_sum": csum, "centroid": [x / c for x in csum],
                            "count": c})
        return out
```

- [ ] **Step 4: Protocol docstring** — `ports.py:39` 갱신(`[{'id','title','centroid_sum','centroid'(=합/count),'count'}]`).
  > **비파괴 보장:** 기존 `centroid`·`count` 키를 **보존**하므로 `vector_index.InMemoryVectorIndex.from_open_stories`(아직 삭제 전, Phase D)가 `s['centroid']`·`s['count']`를 그대로 읽어 안 깨진다. `test_vector_index.py`는 Phase B~C 동안 계속 GREEN.

- [ ] **Step 5: 통과 + 회귀** — `... pytest tests/test_firestore_store.py -v` → PASS

- [ ] **Step 6: Commit** — `git commit -m "feat(store): get_open_stories returns title+centroid_sum"`

### Task 6: `processor.py` 컷오버 (gray-band + 배치내 가시성)

**Files:** Modify `src/newsstore/enrich/processor.py`, `tests/test_processor.py`

- [ ] **Step 1: 실패 테스트** — `_FakeClient`에 `complete` 추가 + 신규:
```python
    def complete(self, prompt, *, timeout=30.0):
        return "DIFFERENT"
```
파일 끝에:
```python
def test_same_batch_second_article_joins_first(store):
    store.upsert_items([_item("a", "Fed raises rates sharply today"),
                        _item("b", "Fed raises rates again right now")])
    process_once(store, _FakeClient({"Fed raises": _unit(0)}), TAX, now=NOW)
    sid = {i: r["story_id"] for i, r in _rows(store).items()}
    assert sid["a"] == sid["b"]


def test_gray_band_same_merges(store):
    class _Gray(_FakeClient):
        def complete(self, prompt, *, timeout=30.0):
            return "SAME"
    def _v(a, b):
        v = [0.0] * EMBED_DIM; v[0] = a; v[1] = b; return v
    store.upsert_items([_item("a", "Alpha one"), _item("b", "Beta two")])
    process_once(store, _Gray({"Alpha": _v(1.0, 0.0), "Beta": _v(0.83, 1.0)}), TAX, now=NOW)
    sid = {i: r["story_id"] for i, r in _rows(store).items()}
    assert sid["a"] == sid["b"]
```

- [ ] **Step 2: 실패 확인** — FAIL (gray-band 미반영)

- [ ] **Step 3: imports 교체** — `processor.py` 7·9행의 `from .cluster import DEFAULT_THRESHOLD`·`from .vector_index import InMemoryVectorIndex` 삭제, 추가:
```python
from . import cluster_adapter
from .clustering_types import Story
```
10행을 `from ..contracts.ports import LLMClient`로(VectorIndex 제거).

- [ ] **Step 4: `process_once` 시그니처·배선** — `threshold`/`index` 파라미터를 `clusterer=None, open_stories: list | None = None`로 교체. 48-49행 인덱스 구성을:
```python
    if clusterer is None:
        clusterer = cluster_adapter.build_clusterer(client)
    if open_stories is None:
        open_stories = cluster_adapter.to_stories(store.get_open_stories(now - open_window))
```
78-79행 호출을 `sid, is_new = _assign_and_persist(store, clusterer, open_stories, it, vec, entities, now, id_factory)`로.

- [ ] **Step 5: `_assign_and_persist` 교체**:
```python
def _assign_and_persist(store, clusterer, open_stories, it, vec, entities, now,
                        id_factory) -> tuple[str, bool]:
    sid = cluster_adapter.assign(clusterer, it, vec, open_stories)
    if sid is None:
        sid = id_factory()
        store.create_story(sid, title=it.title, vec=vec, member_id=it.id,
                           entities=entities, now=now)
        open_stories.append(Story(id=sid, title=it.title, centroid_sum=tuple(vec)))
        return sid, True
    store.append_to_story(sid, vec=vec, member_id=it.id, entities=entities, now=now)
    return sid, False
```

- [ ] **Step 6: 기존 test 갱신** — `test_processor.py`에서 `from newsstore.enrich.vector_index import InMemoryVectorIndex`(86행)와 `idx = InMemoryVectorIndex()`(89행) 사용 테스트를 교체. `test_cluster_pass_index_no_tagging`(84-96행)을 인라인 교체:
```python
def test_cluster_pass_no_tagging(store):
    # tag=False: 태깅 생략, 클러스터만(어댑터 기본 경로 — index 주입 제거)
    store.upsert_items([_item("a", "Fed raises rates sharply today"),
                        _item("b", "Fed raises rates again right now")])
    process_once(store, _FakeClient({"Fed raises": _unit(0)}), TAX, now=NOW, tag=False)
    rows = _rows(store)
    assert rows["a"]["tags"] == []
    assert rows["a"]["embedding"] is not None
    assert rows["a"]["story_id"] == rows["b"]["story_id"]
```
이후 `test_processor.py`에 `InMemoryVectorIndex` 참조가 0이어야 Task 9 grep이 깨끗하다. **나머지 6개 기존 테스트는 `index`/`threshold`를 안 넘기므로**(전부 기본값 호출) 시그니처 교체 후에도 그대로 통과(`process_once`가 `clusterer`/`open_stories`를 None→내부 구성).
  > **배치 내 stale centroid(v1 한계, 정직히):** 합류 스토리의 `centroid_sum`는 배치 내 미갱신(다음 배치 재읽기로 반영). 같은 배치 3번째 동일사건은 1-멤버 centroid와 비교될 수 있어 미세 편차 가능 — v1 허용(코사인 스케일 불변으로 신규 스토리 append 가시성은 보장, 누적 갱신은 후속). `_assign_and_persist`에 1줄 주석으로 명시.

- [ ] **Step 7: 전체 processor 통과(회귀 포함)** — `... pytest tests/test_processor.py -v` → PASS

- [ ] **Step 8: Commit** — `git commit -m "feat(enrich): cutover story assignment to vendored gray-band clusterer"`

### Task 7: `run_enrich` 배선 + threshold 제거

**Files:** Modify `src/newsstore/entrypoints/run_enrich.py`

- [ ] **Step 1: imports** — 7·9행 `DEFAULT_THRESHOLD`·`InMemoryVectorIndex` 삭제, `from ..enrich import cluster_adapter` 추가.

- [ ] **Step 2: `_run_cluster` 교체**:
```python
def _run_cluster(store, client, taxonomy, *, noncluster, batch, concurrency) -> dict:
    """Pass 1 — embed(병렬) + gray-band 배정. clusterer/open_stories 1회 구성·배치 간 공유."""
    now0 = datetime.now(timezone.utc)
    clusterer = cluster_adapter.build_clusterer(client)
    open_stories = cluster_adapter.to_stories(store.get_open_stories(now0 - OPEN_WINDOW))
    log.info("cluster pass: seeded %d open-story candidates", len(open_stories))
    totals = {"processed": 0, "stories_created": 0, "stories_joined": 0, "closed": 0}
    for _ in range(MAX_BATCHES or 1_000_000):
        now = datetime.now(timezone.utc)
        stats = process_once(store, client, taxonomy, now=now, batch=batch,
                             noncluster_sources=noncluster, tag=False,
                             clusterer=clusterer, open_stories=open_stories,
                             close=False, embed_concurrency=concurrency)
        for k in totals:
            totals[k] += stats[k]
        if stats["processed"] == 0:
            break
    totals["closed"] = store.close_stale_stories(cutoff=datetime.now(timezone.utc) - CLOSE_AFTER)
    return totals
```

- [ ] **Step 3: `main`에서 threshold 제거** — 72행 `threshold = ...` 삭제, `_run_cluster` 호출(79-82행)에서 `threshold=threshold` 제거.

- [ ] **Step 4: 임포트 스모크** — `... docker compose run --rm test python -c "from newsstore.entrypoints import run_enrich; print('ok')"` → `ok`

- [ ] **Step 5: 전체 그린** — `MSYS_NO_PATHCONV=1 docker compose run --rm test` → FAIL=0

- [ ] **Step 6: Commit** — `git commit -m "refactor(enrich): wire run_enrich to vendored clusterer (drop threshold plumbing)"`

---

## Phase C — 골든/테스트 이식

### Task 8: 클러스터링 골든·메트릭 이식

**Files:** Create `tests/test_clustering_golden.py`(가능 시), `tests/clustering_metrics.py`

- [ ] **Step 1: 원천 확인** — `D:\projects\news-analytics\tests\`의 클러스터링 단위/메트릭 테스트(`metrics.py` B-cubed, 골든 불변식)와 fixture(`golden_members.jsonl`)를 식별. eval-tier(실 Gemini, `gemini_eval.py`)는 GEMINI_API_KEY 의존이라 **skip 마킹**.

- [ ] **Step 2: 순수 로직 메트릭 이식** — `metrics.py`(B-cubed + '자명해 격파' 불변식, 매직넘버 없음)를 `tests/clustering_metrics.py`로 verbatim 복사. 임포트 경로 조정(있으면).

- [ ] **Step 3: 골든 불변식 테스트(키 불요분만)** — `cluster_articles`로 동일사건 수렴을 fake embed/llm로 검증하는 테스트를 `tests/test_clustering_golden.py`에 작성(실 Gemini eval은 `@pytest.mark.skipif(not GEMINI_API_KEY)`). 매직넘버 금지 — 자명해(전부병합·전부분리) 격파 불변식 사용.
  > **정직히(F1 범위):** CI(키 없음)는 **불변식만** 검증(같은사건→같은 cluster_id, 다른사건→다른 id, 자명해 격파). **실 F1=0.821은 GEMINI 키로 오프라인/수동 측정**이며 통합으로 자동 보장되지 않는다 — "이식했으니 F1 보장"으로 표기하지 않는다. 통합 후 라이브 배치 스폿체크로 회귀 관측(후속).

- [ ] **Step 4: 통과** — `... pytest tests/test_clustering_golden.py -v` → PASS(또는 키 없을 때 skip)

- [ ] **Step 5: Commit** — `git commit -m "test(enrich): vendor clustering golden + B-cubed metric (eval-tier skipped without key)"`

---

## Phase D — 옛 코드 제거 (대체 검증 후, 비파괴 순서)

### Task 9: `cluster.py`·`vector_index.py` 삭제

**Files:** Delete `src/newsstore/enrich/cluster.py`, `src/newsstore/enrich/vector_index.py`, `tests/test_vector_index.py`(+ cluster 단위 테스트)

- [ ] **Step 1: 잔존 참조 확인(코드+문서+스크립트)** — Phase B가 **완전 그린**인 상태에서: `grep -rn "vector_index\|InMemoryVectorIndex\|enrich\.cluster import\|DEFAULT_THRESHOLD\|NEWSSTORE_CLUSTER_THRESHOLD" src tests docs scripts web`로 남은 참조 0 확인(문자열 리터럴·문서 링크·env 키 포함). 0 아니면 삭제 보류하고 해당 참조부터 정리.

- [ ] **Step 2: 삭제** — `git rm src/newsstore/enrich/cluster.py src/newsstore/enrich/vector_index.py tests/test_vector_index.py`. (cluster.py 전용 테스트 있으면 함께.)

- [ ] **Step 3: 전체 그린** — `MSYS_NO_PATHCONV=1 docker compose run --rm test` → FAIL=0, ImportError 0

- [ ] **Step 4: Commit** — `git commit -m "refactor(enrich): remove superseded cluster.py/vector_index.py (gray-band cutover live)"`

---

## Phase E — 문서 정리

### Task 10: 로드맵 이관 + 문서 정리·축소

**Files:** Create `docs/analysis-roadmap.md`; Modify `docs/firestore-contract.md`, `CLAUDE.md`; Delete 보류 cutover spec/plan + handoff 2종(또는 슬림)

- [ ] **Step 1: 분석 로드맵 이관** — news-analytics `docs/superpowers/specs/2026-06-28-news-analytics-design.md`의 §3·§4(방법론: ERL·촉매·델타·impact·risk)·§5(build-adopt)·§9(능력 단계)·§12(참고문헌)를 `docs/analysis-roadmap.md`로 정리 이관(newsstore 통합 맥락으로 재서술 — "라이브러리" 전제 제거). 클러스터링은 ✅ 이식됨, 나머지는 통합 개발 백로그로 명시.

- [ ] **Step 2: `firestore-contract.md` 갱신** — "분리·import 안 함"을 "통합 — 인리치/분석을 newsstore 내 개발. stories/items 인리치 필드는 newsstore가 직접 write. 미래 재분리 시 GitHub main 기준" 으로. 소유권 표 writer를 newsstore로. (또는 문서를 슬림 `stories`/`items` 스키마 정의로 축소.)

- [ ] **Step 3: `CLAUDE.md` 스코프 줄 갱신** — line 20을 "통합 개발(분석을 newsstore 내), 안정 시 news-analytics로 1회 분리(보류). 상세: docs/analysis-roadmap.md, 메모리 integration-strategy" 로 교체.

- [ ] **Step 4: 보류·무용 문서 정리** — `git rm` 또는 슬림:
  - 삭제: `docs/handoff/2026-06-28-news-analytics-v1-handoff.md`(위임서 — 통합으로 무용), `docs/superpowers/plans/2026-06-29-na-clusterer-cutover.md`·`specs/2026-06-29-na-clusterer-cutover-design.md`(보류 컷오버 — 통합으로 대체. 단 gray-band 근거는 analysis-roadmap에 흡수됐는지 확인 후).
  - 슬림: `docs/handoff/2026-06-28-session-handoff.md`(역사 기록은 1줄 요약만).
  - 검토: `docs/superpowers/specs/2026-06-28-newsstore-topic-lens-redesign-design.md`(DEPRECATED 마킹된 마스터 — analysis-roadmap이 대체하면 삭제).

- [ ] **Step 5: 드리프트 0 확인** — `grep -rn "import 없음\|Firestore 스키마로만\|news-analytics 소유\|news-analytics를 import" docs CLAUDE.md`로 통합과 충돌하는 잔존 문구 0(또는 "미래 재분리" 맥락으로 정정됨) 확인.

- [ ] **Step 6: Commit** — `git commit -m "docs: integrate analysis roadmap into newsstore; retire split/cutover/handoff docs"`

---

## 검증 (완료 기준)
- `MSYS_NO_PATHCONV=1 docker compose run --rm test` → **FAIL=0**(gray-band 단위·어댑터·processor 회귀·골든 포함).
- gray-band 동작 증거: 같은 사건 합류 / 다른 사건 분리 / 모호권 LLM SAME→합류 / LLM 장애→보수적 신규(테스트로).
- 새 의존성 0 — docker-compose/pyproject 의존성 변경 없음.
- 문서 드리프트 0 — 통합과 충돌하는 "분리·import" 문구 없음.

## 후속 (이 플랜 밖)
- 분석 능력 통합 개발: score(impact·risk) → extract_delta → classify_lenses → brief(각 골든셋 red→green, analysis-roadmap 순서).
- gray-band 임계값 newsstore 코퍼스 캘리브레이션(현재 이란+코스피 eval값).
- 미래 재분리(인터페이스 안정·MCP/agent 목표 구체화 시).

<!-- spec-review: passed lenses=3 date=2026-06-29 -->

