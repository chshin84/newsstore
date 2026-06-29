# news-analytics 클러스터러 컷오버 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> ⛔ **보류(SHELVED) — 2026-06-29 사용자 전략 결정.** "통합 우선, 나중 1회 분리"로 방향 전환됨: 분석 레이어를 newsstore 안에서 개발하고, 인터페이스 안정·MCP/agent 목표 구체화 시 한 번에 라이브러리로 추출. **이 컷오버 플랜은 구현하지 않는다**(접착제 비용을 안정화 전에 치르지 않기 위해 — YAGNI). news-analytics 클러스터링(gray-band)을 원하면 별도 "폴드백" 작업으로 newsstore에 이식. 이 문서는 재분리 시점에 참고 자료로 보존.

**Goal:** newsstore 인리치 파이프라인의 스토리 배정 결정을 newsstore 자체 로직(`InMemoryVectorIndex.nearest`, 단일 임계값)에서 news-analytics `EventClusterer.assign`(gray-band LLM)으로 완전 교체한다.

**Architecture:** newsstore는 news-analytics(별 repo, GitHub `@main`)를 라이브러리로 import 하는 **얇은 소비자**가 된다. 클러스터링 알고리즘은 news-analytics 소유(순수 DI), newsstore는 경계 어댑터(`na_adapter.py`)로 embed·llm을 주입하고 Firestore I/O를 담당한다. 나머지 인리치(분류·태깅·임베딩·요약)는 과도기로 newsstore 잔류.

**Tech Stack:** Python 3.12, Docker-only(`docker compose run --rm test` = Firestore 에뮬레이터 + pytest), news-analytics(`gemini-embedding-001`/768 임베딩 + `gemini-3.1-flash-lite-preview` gray-band LLM, 둘 다 주입).

**Spec:** `docs/superpowers/specs/2026-06-29-na-clusterer-cutover-design.md`

**핵심 gotchas (이 작업에서 반드시 지킬 것):**
- **mock과 실제 None 차이** — fake가 빈 결과에 `{}`/`[]`를 줘도 실 SDK는 `None`. `complete`는 `call_with_retry`로 None 가드 유지.
- **테스트 기대치 매직넘버 금지** — "stories==2" 같은 개수는 불변식(같은 사건→같은 id, 다른 사건→다른 id)으로 검증. 개수 단언은 테스트 픽스처가 스스로 결정하는 경우만.
- **비파괴** — `append_to_story`/`save_enrichment`는 merge. raw 필드·요약 필드 덮어쓰기 금지.
- **GitHub main만 기준** — news-analytics는 `@main` 추적. 로컬 워킹카피 신경 쓰지 않는다.

**개발 명령(Docker 전용):**
- 의존성 바꾼 뒤 재빌드: `MSYS_NO_PATHCONV=1 docker compose build test`
- 특정 테스트: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_x.py -v`
- 전체: `MSYS_NO_PATHCONV=1 docker compose run --rm test`

---

## File Structure

| 파일 | 책임 | 변경 |
|---|---|---|
| `pyproject.toml` | `enrich` extra에 news-analytics 의존 | Modify |
| `docker-compose.yml` | test 서비스가 enrich extra 설치 | Modify |
| `src/newsstore/enrich/gemini.py` | `GeminiClient.complete` 평문 생성 | Modify |
| `src/newsstore/contracts/ports.py` | `LLMClient` Protocol에 `complete` | Modify |
| `src/newsstore/enrich/na_adapter.py` | **경계 어댑터**(매핑+주입+assign 위임) | Create |
| `src/newsstore/store/firestore_store.py` | `get_open_stories`에 title·centroid_sum | Modify |
| `src/newsstore/enrich/processor.py` | 배정 결정을 어댑터로 교체 | Modify |
| `src/newsstore/entrypoints/run_enrich.py` | 인덱스 배선 → 어댑터 배선 | Modify |
| `docs/firestore-contract.md` | 결합 모델 정정 | Modify |
| `tests/test_na_import.py` | import 스모크 | Create |
| `tests/test_na_adapter.py` | 어댑터·gray-band 단위 | Create |
| `tests/test_processor.py` | 시그니처 교체 + gray-band/배치내 가시성 | Modify |
| `tests/test_firestore_store.py` | get_open_stories 확장 | Modify |

---

## Task 1: news-analytics 의존성 배선 + import 스모크

**Files:**
- Modify: `pyproject.toml:23`
- Modify: `docker-compose.yml:19-21`
- Test: `tests/test_na_import.py` (create)

- [ ] **Step 1: import 스모크 테스트 작성(실패 예정)**

`tests/test_na_import.py`:
```python
"""news-analytics(@main)가 enrich extra로 설치돼 공개 API가 import 되는지."""

def test_news_analytics_public_api_importable():
    from news_analytics.clustering import EventClusterer, cluster_articles
    from news_analytics.contracts import Article, Story
    # 시그니처 표면 확인(드리프트 가드)
    assert hasattr(EventClusterer, "assign")
    a = Article(id="x", title="t", body="b", source="S", published_at="2026-06-29")
    s = Story(id="s", title="t")
    assert a.embedding is None and s.centroid_sum is None
```

- [ ] **Step 2: 실패 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_na_import.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'news_analytics'`

- [ ] **Step 3: enrich extra에 의존 추가**

`pyproject.toml` 23행을 교체:
```toml
enrich = [
    "google-genai>=1.0",
    "news-analytics @ git+https://github.com/chshin84/news-analytics@main",
]
```

- [ ] **Step 4: test 서비스가 enrich extra를 설치하도록**

`docker-compose.yml`의 test 서비스 `args`(19-21행)에 `INSTALL_ENRICH` 추가:
```yaml
      args:                       # dev(pytest)+gcp(firestore)+enrich(news-analytics) — 에뮬레이터 테스트용
        INSTALL_DEV: "true"
        INSTALL_GCP: "true"
        INSTALL_ENRICH: "true"
```

- [ ] **Step 5: test 이미지 재빌드(네트워크로 GitHub @main fetch)**

Run: `MSYS_NO_PATHCONV=1 docker compose build test`
Expected: 빌드 성공. 로그에 `news-analytics ... (from git+https://github.com/chshin84/news-analytics@main)` 설치 라인.

- [ ] **Step 6: 재현성 — 해소된 SHA 기록**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pip show news-analytics`
빌드된 news-analytics 버전을 확인하고, 해소된 커밋을 빌드 메모로 남긴다(이미지가 어떤 main 스냅샷인지). 별도 인프라 파일 변경은 불필요(`@main` 추적 + 빌드 로그가 SHA 출처).

- [ ] **Step 7: 스모크 통과 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_na_import.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml docker-compose.yml tests/test_na_import.py
git commit -m "build: depend on news-analytics @main (enrich extra) + test installs enrich"
```

---

## Task 2: `GeminiClient.complete` (평문 생성) + Protocol

news-analytics gray-band는 `llm.complete(prompt) -> str`(평문 첫 줄 SAME/DIFFERENT)를 호출한다. newsstore `GeminiClient`엔 `generate_json`(dict)·`embed`만 있어 갭을 메꾼다.

**Files:**
- Modify: `src/newsstore/enrich/gemini.py:69` (generate_json 옆)
- Modify: `src/newsstore/contracts/ports.py:64-66`
- Test: `tests/test_gemini_complete.py` (create)

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_gemini_complete.py`:
```python
"""GeminiClient.complete — 평문 반환 + None 가드(call_with_retry 재사용)."""
import types as _t
import pytest
from newsstore.enrich.gemini import GeminiClient, LLMError


def _client_with_fake_models(responses):
    """real SDK 생성을 건너뛰고 _client.models.generate_content를 가짜로 주입."""
    c = GeminiClient.__new__(GeminiClient)          # __init__(네트워크) 우회
    c._model = "m"; c._embed_model = "e"; c._embed_dim = 768
    seq = iter(responses)

    def generate_content(*, model, contents, config):
        r = next(seq)
        return _t.SimpleNamespace(text=r)           # r=None이면 text=None
    c._client = _t.SimpleNamespace(models=_t.SimpleNamespace(generate_content=generate_content))
    return c


def test_complete_returns_plain_text():
    c = _client_with_fake_models(["SAME\nbecause same event"])
    assert c.complete("a vs b").startswith("SAME")


def test_complete_none_guard_retries_then_succeeds():
    c = _client_with_fake_models([None, "DIFFERENT"])   # 첫 응답 None → 재시도
    assert c.complete("a vs b").startswith("DIFFERENT")
```

- [ ] **Step 2: 실패 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_gemini_complete.py -v`
Expected: FAIL — `AttributeError: 'GeminiClient' object has no attribute 'complete'`

- [ ] **Step 3: complete 구현(generate_json 패턴 미러)**

`src/newsstore/enrich/gemini.py`의 `generate_json` 메서드 바로 위(69행 앞)에 추가:
```python
    def complete(self, prompt: str, *, timeout: float = DEFAULT_TIMEOUT) -> str:
        """평문 생성(JSON mime 없이). news-analytics gray-band LLM(llm.complete)용.

        generate_json과 같은 retry/None가드(call_with_retry)를 쓰되 r.text를 그대로 반환."""
        from google.genai import types

        def _call():
            r = self._client.models.generate_content(
                model=self._model, contents=prompt,
                config=types.GenerateContentConfig(
                    http_options=types.HttpOptions(timeout=int(timeout * 1000))))
            return getattr(r, "text", None)          # None 가드 → call_with_retry가 재시도

        return call_with_retry(_call, is_transient=self._is_transient)
```
주: `DEFAULT_TIMEOUT`은 클래스 변수(48행)라 메서드 안에서 `DEFAULT_TIMEOUT`로 참조 가능(기존 `generate_json`/`embed`와 동일 패턴).

- [ ] **Step 4: Protocol에 complete 선언(EXPLICIT — 계약에 드러냄)**

`src/newsstore/contracts/ports.py`의 `LLMClient`(64-66행)를 교체:
```python
class LLMClient(Protocol):
    def generate_json(self, prompt: str, *, timeout: float) -> dict: ...
    def embed(self, text: str, *, timeout: float) -> list[float]: ...
    def complete(self, prompt: str, *, timeout: float) -> str: ...
```

- [ ] **Step 5: 통과 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_gemini_complete.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add src/newsstore/enrich/gemini.py src/newsstore/contracts/ports.py tests/test_gemini_complete.py
git commit -m "feat(enrich): GeminiClient.complete (plain-text) for news-analytics gray-band LLM"
```

---

## Task 3: `na_adapter.py` — 경계 어댑터

news-analytics 타입/주입을 newsstore와 잇는 유일한 결합점. **순수 매퍼 + assign 위임만**(클러스터링 로직 0).

**Files:**
- Create: `src/newsstore/enrich/na_adapter.py`
- Test: `tests/test_na_adapter.py`

- [ ] **Step 1: 실패 테스트 작성(fake embed/llm — 에뮬레이터 불필요)**

`tests/test_na_adapter.py`:
```python
"""na_adapter — 매핑 + EventClusterer.assign 위임(gray-band 포함). 순수 단위(에뮬레이터 X)."""
from newsstore.contracts.models import RawItem
from newsstore.enrich import na_adapter


class _LLM:
    """complete만 있는 가짜 LLM. verdict로 gray-band 결과 제어."""
    def __init__(self, verdict="DIFFERENT", boom=False):
        self.verdict, self.boom, self.calls = verdict, boom, 0
    def complete(self, prompt, *, timeout=30.0):
        self.calls += 1
        if self.boom:
            raise RuntimeError("LLM down")
        return self.verdict


class _Client:
    """embed: 미사용(article에 embedding 직접 주입). complete: 위임."""
    def __init__(self, llm):
        self._llm = llm
    def embed(self, text, *, timeout=30.0):
        return [0.0, 0.0]                       # 호출되면 안 되는 폴백
    def complete(self, prompt, *, timeout=30.0):
        return self._llm.complete(prompt, timeout=timeout)


def _item(i, title):
    return RawItem(id=i, feed_id="f", source="S", url=f"https://e/{i}", title=title, body="body")


def _story(sid, title, csum):
    return {"id": sid, "title": title, "centroid_sum": list(csum), "centroid": list(csum), "count": 1}


def test_to_stories_maps_id_title_centroid_sum():
    [s] = na_adapter.to_stories([_story("s1", "Fed", [1.0, 0.0])])
    assert s.id == "s1" and s.title == "Fed" and tuple(s.centroid_sum) == (1.0, 0.0)


def test_assign_deterministic_join_when_identical():
    # cos=1.0 >= hi(0.75) → 결정론 합류, LLM 미호출
    llm = _LLM(); clusterer = na_adapter.build_clusterer(_Client(llm))
    open_stories = na_adapter.to_stories([_story("s1", "Fed", [1.0, 0.0])])
    sid = na_adapter.assign(clusterer, _item("a", "Fed"), [1.0, 0.0], open_stories)
    assert sid == "s1" and llm.calls == 0


def test_assign_deterministic_new_when_orthogonal():
    # cos=0.0 < lo(0.55) → 결정론 신규(None), LLM 미호출
    llm = _LLM(); clusterer = na_adapter.build_clusterer(_Client(llm))
    open_stories = na_adapter.to_stories([_story("s1", "Fed", [1.0, 0.0])])
    sid = na_adapter.assign(clusterer, _item("a", "Oil"), [0.0, 1.0], open_stories)
    assert sid is None and llm.calls == 0


def test_assign_gray_band_same_joins():
    # cos≈0.64 (lo<cos<hi) → gray-band LLM=SAME → 합류
    llm = _LLM("SAME"); clusterer = na_adapter.build_clusterer(_Client(llm))
    open_stories = na_adapter.to_stories([_story("s1", "Fed", [1.0, 0.0])])
    sid = na_adapter.assign(clusterer, _item("a", "Fed-ish"), [0.83, 1.0], open_stories)
    assert sid == "s1" and llm.calls == 1


def test_assign_gray_band_different_new():
    llm = _LLM("DIFFERENT"); clusterer = na_adapter.build_clusterer(_Client(llm))
    open_stories = na_adapter.to_stories([_story("s1", "Fed", [1.0, 0.0])])
    sid = na_adapter.assign(clusterer, _item("a", "Fed-ish"), [0.83, 1.0], open_stories)
    assert sid is None and llm.calls == 1


def test_assign_gray_band_llm_error_is_failsoft_new():
    # gray-band에서 LLM 장애 → 보수적 신규(None), 예외 전파 안 함
    llm = _LLM(boom=True); clusterer = na_adapter.build_clusterer(_Client(llm))
    open_stories = na_adapter.to_stories([_story("s1", "Fed", [1.0, 0.0])])
    sid = na_adapter.assign(clusterer, _item("a", "Fed-ish"), [0.83, 1.0], open_stories)
    assert sid is None
```
주: gray-band 경계는 `news_analytics.config.GRAY_BAND=(0.55, 0.75)`. `[0.83,1.0]` vs `[1.0,0.0]`의 코사인 ≈ 0.64로 그 사이 → 검증 시 `python -c "import math;a=[0.83,1.0];b=[1.0,0.0];print(sum(x*y for x,y in zip(a,b))/(math.hypot(*a)*math.hypot(*b)))"`로 0.55~0.75 확인.

- [ ] **Step 2: 실패 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_na_adapter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'newsstore.enrich.na_adapter'`

- [ ] **Step 3: 어댑터 구현**

`src/newsstore/enrich/na_adapter.py`:
```python
"""news-analytics 경계 어댑터 — 결합점은 여기 한 파일뿐(FOCUSED).

newsstore RawItem/스토리 dict ↔ news_analytics Article/Story 매핑 + embed·llm 주입.
클러스터링 로직은 news-analytics 소유 — 여기엔 절대 두지 않는다(경계 부패 방지)."""
from __future__ import annotations

from news_analytics.clustering import EventClusterer
from news_analytics.contracts import Article, Story

from ..contracts.models import RawItem
from ..contracts.ports import LLMClient


def build_clusterer(client: LLMClient) -> EventClusterer:
    """embed·llm을 주입해 온라인 클러스터러 생성(1회). 주 경로는 article.embedding을 쓰므로
    embed는 폴백(미호출). llm은 gray-band 전용."""
    def embed(texts: list[str]) -> list[list[float]]:
        return [client.embed(t) for t in texts]
    return EventClusterer(embed=embed, llm=client)


def to_article(item: RawItem, vec) -> Article:
    """RawItem + 임베딩 → Article. RawItem엔 tags가 없어 빈 튜플(assign은 tags 미사용)."""
    return Article(id=item.id, title=item.title, body=item.body or "",
                   source=item.source, published_at=str(item.published_at or ""),
                   tags=(), embedding=tuple(vec))


def to_stories(rows) -> list[Story]:
    """get_open_stories 행(id, title, centroid_sum) → Story. 나머지 필드는 기본값
    (assign은 id·title·centroid_sum만 읽음)."""
    return [Story(id=r["id"], title=r.get("title") or "",
                  centroid_sum=tuple(r["centroid_sum"]))
            for r in rows if r.get("centroid_sum")]


def assign(clusterer: EventClusterer, item: RawItem, vec, open_stories) -> str | None:
    """기사를 open_stories에 배정. 합류할 story_id 또는 신규면 None."""
    return clusterer.assign(to_article(item, vec), open_stories)
```

- [ ] **Step 4: 통과 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_na_adapter.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add src/newsstore/enrich/na_adapter.py tests/test_na_adapter.py
git commit -m "feat(enrich): na_adapter — news-analytics boundary (map + inject + assign)"
```

---

## Task 4: `get_open_stories`에 title·centroid_sum 추가

배정 경로가 gray-band용 `title`과 원본 합 `centroid_sum`를 받도록 반환 dict를 확장한다(기존 `centroid`/`count` 보존 — 비파괴).

**Files:**
- Modify: `src/newsstore/store/firestore_store.py:71-79`
- Modify: `src/newsstore/contracts/ports.py:38-40` (docstring)
- Test: `tests/test_firestore_store.py` (append)

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_firestore_store.py` 끝에 추가:
```python
def test_get_open_stories_includes_title_and_centroid_sum(store):
    from datetime import datetime, timezone, timedelta
    now = datetime(2026, 6, 29, tzinfo=timezone.utc)
    store.create_story("s1", title="Fed move", vec=[1.0, 2.0], member_id="a",
                       entities=["Fed"], now=now)
    store.append_to_story("s1", vec=[3.0, 0.0], member_id="b", entities=[], now=now)
    [row] = store.get_open_stories(cutoff=now - timedelta(hours=1))
    assert row["id"] == "s1"
    assert row["title"] == "Fed move"
    assert row["centroid_sum"] == [4.0, 2.0]        # 1+3, 2+0 (원본 합)
    assert row["centroid"] == [2.0, 1.0]            # 합/count(2) — 기존 키 보존
    assert row["count"] == 2
```

- [ ] **Step 2: 실패 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_firestore_store.py::test_get_open_stories_includes_title_and_centroid_sum -v`
Expected: FAIL — `KeyError: 'centroid_sum'` (또는 title)

- [ ] **Step 3: get_open_stories 확장**

`src/newsstore/store/firestore_store.py`의 `get_open_stories`(71-79행)를 교체:
```python
    def get_open_stories(self, cutoff) -> list[dict]:
        out = []
        for snap in self.db.collection("stories").where("status", "==", "open").stream():
            d = snap.to_dict() or {}
            if d.get("last_seen") and d["last_seen"] >= cutoff:
                csum = list(d.get("centroid_sum", []))
                c = d.get("count", 1) or 1
                out.append({"id": snap.id, "title": d.get("title") or "",
                            "centroid_sum": csum,                      # 원본 합(어댑터용)
                            "centroid": [x / c for x in csum],         # 평균(기존 호출자 보존)
                            "count": c})
        return out
```

- [ ] **Step 4: Protocol docstring 갱신**

`src/newsstore/contracts/ports.py`의 `get_open_stories` docstring(39행)을 교체:
```python
    def get_open_stories(self, cutoff) -> list[dict]:
        """status=open이고 last_seen>=cutoff인 스토리:
        [{'id','title','centroid_sum'(원본 합),'centroid'(=합/count),'count'}]."""
        ...
```

- [ ] **Step 5: 통과 + 회귀(기존 store 테스트) 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_firestore_store.py -v`
Expected: PASS (신규 + 기존 모두)

- [ ] **Step 6: Commit**

```bash
git add src/newsstore/store/firestore_store.py src/newsstore/contracts/ports.py tests/test_firestore_store.py
git commit -m "feat(store): get_open_stories returns title+centroid_sum (na_adapter), preserve centroid/count"
```

---

## Task 5: `process_once` 컷오버 — 배정을 어댑터로 교체

핵심 단계. `process_once`의 배정 결정을 `InMemoryVectorIndex.nearest`(단일 임계값)에서 `na_adapter.assign`(gray-band)으로 바꾸고, **배치 내 신규 스토리 가시성**(같은 배치 후속 기사가 방금 연 스토리에 합류)을 유지한다.

**Files:**
- Modify: `src/newsstore/enrich/processor.py` (imports, `process_once` 시그니처, `_assign_and_persist`)
- Modify: `tests/test_processor.py` (시그니처 교체 + gray-band/배치내 테스트)

- [ ] **Step 1: 실패 테스트 — gray-band + 배치 내 가시성**

`tests/test_processor.py`의 `_FakeClient`에 `complete` 추가(클래스 본문에):
```python
    def complete(self, prompt, *, timeout=30.0):
        return "DIFFERENT"        # 기본: gray-band면 미합류(직교 벡터 테스트는 호출 안 됨)
```
그리고 파일 끝에 신규 테스트 추가:
```python
def test_same_batch_second_article_joins_first_new_story(store):
    # 같은 배치에서 첫 기사가 연 스토리에 둘째가 합류(배치 내 open_stories 갱신 불변식)
    store.upsert_items([_item("a", "Fed raises rates sharply today"),
                        _item("b", "Fed raises rates again right now")])  # 동일 벡터
    process_once(store, _FakeClient({"Fed raises": _unit(0)}), TAX, now=NOW)
    sid = {i: r["story_id"] for i, r in _rows(store).items()}
    assert sid["a"] == sid["b"]            # 한 배치 안에서 합류(중복 스토리 X)


def test_gray_band_llm_same_merges(store):
    # gray-band(lo<cos<hi)에서 LLM=SAME → 합류. 벡터를 0.64 코사인으로 구성.
    class _GrayClient(_FakeClient):
        def complete(self, prompt, *, timeout=30.0):
            return "SAME"
    def _vec(a, b):
        v = [0.0] * EMBED_DIM; v[0] = a; v[1] = b; return v
    store.upsert_items([_item("a", "Alpha event one"), _item("b", "Beta event two")])
    process_once(store, _GrayClient({"Alpha": _vec(1.0, 0.0), "Beta": _vec(0.83, 1.0)}),
                 TAX, now=NOW)
    sid = {i: r["story_id"] for i, r in _rows(store).items()}
    assert sid["a"] == sid["b"]            # gray-band SAME → 합류
```

- [ ] **Step 2: 실패 확인(시그니처/동작 미반영)**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_processor.py::test_gray_band_llm_same_merges -v`
Expected: FAIL (현재 단일 임계값 로직엔 gray-band 없음 → 합류 안 됨, 또는 동작 불일치)

- [ ] **Step 3: processor.py imports 교체**

`src/newsstore/enrich/processor.py`의 7·9행 교체:
```python
# 삭제: from .cluster import DEFAULT_THRESHOLD
# 삭제: from .vector_index import InMemoryVectorIndex
from . import na_adapter
from news_analytics.contracts import Story
```
10행 `from ..contracts.ports import LLMClient, VectorIndex`를 `from ..contracts.ports import LLMClient`로(VectorIndex 미사용).

- [ ] **Step 4: `process_once` 시그니처·배선 교체**

`process_once`(29-49행 영역)에서 `threshold`/`index` 파라미터를 `clusterer`/`open_stories`로 교체. 시그니처(29-36행)를:
```python
def process_once(store, client: LLMClient, taxonomy: dict, *, now: datetime,
                 batch: int = 10, open_window: timedelta = OPEN_WINDOW,
                 close_after: timedelta = CLOSE_AFTER,
                 noncluster_sources=NONCLUSTER_SOURCES,
                 tag: bool = True, clusterer=None, open_stories: list | None = None,
                 close: bool = True,
                 embed_concurrency: int = EMBED_CONCURRENCY, id_factory=None) -> dict:
```
그리고 48-49행의 인덱스 구성:
```python
    if index is None:
        index = InMemoryVectorIndex.from_open_stories(store, now - open_window)
```
을 교체:
```python
    if clusterer is None:
        clusterer = na_adapter.build_clusterer(client)
    if open_stories is None:
        open_stories = na_adapter.to_stories(store.get_open_stories(now - open_window))
```
78-79행 `_assign_and_persist(store, index, it, vec, entities, now, threshold, id_factory)` 호출을:
```python
        sid, is_new = _assign_and_persist(store, clusterer, open_stories, it, vec,
                                          entities, now, id_factory)
```

- [ ] **Step 5: `_assign_and_persist` 교체(어댑터 + 배치 내 가시성)**

`_assign_and_persist`(100-112행)를 교체:
```python
def _assign_and_persist(store, clusterer, open_stories, it, vec, entities, now,
                        id_factory) -> tuple[str, bool]:
    """news-analytics로 스토리 배정 + 영속화 + 배치 내 open_stories 갱신. 반환 (story_id, is_new)."""
    sid = na_adapter.assign(clusterer, it, vec, open_stories)
    if sid is None:
        sid = id_factory()
        store.create_story(sid, title=it.title, vec=vec, member_id=it.id,
                           entities=entities, now=now)
        # 같은 배치의 후속 기사가 이 신규 스토리를 후보로 보게(배치 내 가시성)
        open_stories.append(Story(id=sid, title=it.title, centroid_sum=tuple(vec)))
        return sid, True
    store.append_to_story(sid, vec=vec, member_id=it.id, entities=entities, now=now)
    # 합류 스토리의 centroid_sum 배치 내 갱신은 v1 미적용(다음 배치 재읽기로 반영 — spec §5.5)
    return sid, False
```

- [ ] **Step 6: 기존 테스트 시그니처 교체(index 제거)**

`tests/test_processor.py`의 `test_cluster_pass_index_no_tagging`(84-96행)을 교체(인덱스 주입 → 기본 어댑터 경로, tag=False 유지):
```python
def test_cluster_pass_no_tagging(store):
    # tag=False: 태깅 생략하고 클러스터만(어댑터 경로)
    store.upsert_items([_item("a", "Fed raises rates sharply today"),
                        _item("b", "Fed raises rates again right now")])
    process_once(store, _FakeClient({"Fed raises": _unit(0)}), TAX, now=NOW, tag=False)
    rows = _rows(store)
    assert rows["a"]["tags"] == []                         # 태깅 생략
    assert rows["a"]["embedding"] is not None
    assert rows["a"]["story_id"] == rows["b"]["story_id"]  # 합류
```

- [ ] **Step 7: 전체 processor 테스트 통과(회귀 포함)**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_processor.py -v`
Expected: PASS — 기존 클러스터 동작(동일→합류, 직교→분리, spam/digest 제외, thin 제외) + 신규(gray-band, 배치내 가시성) 모두.

- [ ] **Step 8: Commit**

```bash
git add src/newsstore/enrich/processor.py tests/test_processor.py
git commit -m "feat(enrich): cutover story assignment to news-analytics EventClusterer (gray-band)"
```

---

## Task 6: `run_enrich` 배선 교체 (인덱스 → 어댑터)

엔트리포인트가 `InMemoryVectorIndex` 대신 어댑터로 clusterer/open_stories를 1회 구성해 배치 간 공유한다. 의미 없어진 `threshold` 플럼빙 제거(FAIL-LOUD — 아무것도 안 하는 env 금지).

**Files:**
- Modify: `src/newsstore/entrypoints/run_enrich.py`

- [ ] **Step 1: `_run_cluster` 교체**

`src/newsstore/entrypoints/run_enrich.py`의 imports(7·9행)에서 `DEFAULT_THRESHOLD`·`InMemoryVectorIndex` 제거하고 어댑터 추가:
```python
# 삭제: from ..enrich.cluster import DEFAULT_THRESHOLD
# 삭제: from ..enrich.vector_index import InMemoryVectorIndex
from ..enrich import na_adapter
```
`_run_cluster`(22-42행)를 교체:
```python
def _run_cluster(store, client, taxonomy, *, noncluster, batch, concurrency) -> dict:
    """Pass 1 — 클러스터 전용(빠름): embed(병렬) + news-analytics 배정(gray-band). LLM 태깅 없음.

    열린 스토리를 1회 로드해 clusterer/open_stories를 배치 간 공유(Firestore 제곱 재조회 제거)."""
    now0 = datetime.now(timezone.utc)
    clusterer = na_adapter.build_clusterer(client)
    open_stories = na_adapter.to_stories(store.get_open_stories(now0 - OPEN_WINDOW))
    log.info("cluster pass: seeded %d open-story candidates", len(open_stories))
    totals = {"processed": 0, "stories_created": 0, "stories_joined": 0, "closed": 0}
    for _ in range(MAX_BATCHES or 1_000_000):
        now = datetime.now(timezone.utc)
        stats = process_once(store, client, taxonomy, now=now, batch=batch,
                             noncluster_sources=noncluster,
                             tag=False, clusterer=clusterer, open_stories=open_stories,
                             close=False, embed_concurrency=concurrency)
        for k in totals:
            totals[k] += stats[k]
        if stats["processed"] == 0:
            break
    totals["closed"] = store.close_stale_stories(cutoff=datetime.now(timezone.utc) - CLOSE_AFTER)
    return totals
```

- [ ] **Step 2: `main`에서 threshold 제거**

`main`(72행)의 `threshold = float(os.environ.get("NEWSSTORE_CLUSTER_THRESHOLD", DEFAULT_THRESHOLD))` 줄을 삭제. `_run_cluster` 호출(79-82행)에서 `threshold=threshold` 인자 삭제:
```python
            if args.mode == "cluster":
                totals = _run_cluster(store, client, taxonomy,
                                      noncluster=noncluster, batch=args.batch,
                                      concurrency=concurrency)
```

- [ ] **Step 3: 임포트 정합성 확인(런타임 스모크)**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test python -c "from newsstore.entrypoints import run_enrich; print('ok')"`
Expected: `ok` (NameError/ImportError 없음 — DEFAULT_THRESHOLD/InMemoryVectorIndex 잔존 참조 없음 확인)

- [ ] **Step 4: 전체 테스트 그린**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test`
Expected: 전체 PASS(FAIL=0). `test_vector_index.py`는 그대로(InMemoryVectorIndex 클래스 잔존, 미배선) — 통과.

- [ ] **Step 5: Commit**

```bash
git add src/newsstore/entrypoints/run_enrich.py
git commit -m "refactor(enrich): wire run_enrich cluster pass to na_adapter (drop index/threshold plumbing)"
```

---

## Task 7: 계약 문서 정정 (`firestore-contract.md`)

코드가 바뀌었으니 결합 모델 SSOT를 갱신(드리프트 제거, FAIL-LOUD).

**Files:**
- Modify: `docs/firestore-contract.md:5` 및 소유권 표(10-17행), 과도기 현실(56-62행)

- [ ] **Step 1: 결정 줄 교체**

`docs/firestore-contract.md` 5행을 교체:
```markdown
- **결정(2026-06-29):** newsstore가 **news-analytics를 라이브러리로 import**(GitHub `@main`). news-analytics는 **순수 DI 로직(I/O 없음)** — 클러스터링 알고리즘만 소유. **모든 Firestore read/merge·스케줄·키·임베더/LLM 클라이언트 생성은 newsstore 소유.** (이전 "Firestore-as-API · import 안 함" 결정을 대체.)
```

- [ ] **Step 2: 소유권 표 writer 정정**

10-17행 표에서 `items`(인리치 필드) writer를 `**news-analytics** (merge)` → `**newsstore 어댑터** (news-analytics 결정으로 merge)`, `stories` writer를 `**news-analytics**` → `**newsstore 어댑터** (클러스터링=news-analytics, I/O=newsstore)`로 교체.

- [ ] **Step 3: 과도기 현실 갱신**

56-62행 "과도기 현실"에 한 줄 추가:
```markdown
- **2026-06-29 갱신:** 스토리 **클러스터링**은 news-analytics 라이브러리(`EventClusterer.assign`, gray-band)로 컷오버됨 — newsstore `enrich/na_adapter.py`가 호출. 분류·태깅·임베딩·요약은 아직 newsstore 잔류(후속). `cluster.py`·`vector_index.py`는 배선에서 빠졌으나 물리 삭제는 후속 정리.
```

- [ ] **Step 4: Commit**

```bash
git add docs/firestore-contract.md
git commit -m "docs: firestore-contract — newsstore imports news-analytics (clustering cutover live)"
```

---

## Task 8: 컷오버 배포 (운영 — 라이브 Job#2)

코드 그린 후 라이브 Cloud Run Job#2(`newsstore-enricher`)를 새 이미지로 교체. **수동·검증 단계**(GEMINI 키·gcloud 필요). 상세 절차는 `docs/operations.md §E·§F` 따름.

- [ ] **Step 1: news-analytics main 그린 확인**

GitHub `chshin84/news-analytics` main의 CI/테스트가 통과 상태인지 확인(컷오버 전제 — `@main`이 깨진 커밋을 끌어오지 않게).

- [ ] **Step 2: processor 이미지 재빌드(enrich 포함)**

`docs/operations.md §E`의 빌드 절차로 `INSTALL_ENRICH=true` 이미지를 빌드(news-analytics @main 포함). 빌드 로그에서 해소된 news-analytics 커밋 SHA 기록.

- [ ] **Step 3: Job 이미지 업데이트 + 실행**

```
gcloud run jobs update newsstore-enricher --image <NEW_IMAGE> ...
gcloud run jobs execute newsstore-enricher ...
```
(풀경로 gcloud·플래그는 operations.md 따름)

- [ ] **Step 4: 스모크 + 스폿체크(cross-corpus 관측)**

실행 로그에서 news-analytics `clustering: ...` 로그 + 스토리 생성/합류 정상 확인. 새로 생성/합류된 스토리 표본 ~10건이 과병합/과분리 아닌지 사람 눈으로 점검. LLM 콜 비율(`ratio`) 관측 — 무료 tier 한도 초과 조짐이면 보고.

- [ ] **Step 5: 사이트 회귀**

공개 사이트 스토리 탭이 정상 렌더되는지(fail-soft 불변식). `stories` 비어도 강등 정상.

- [ ] **Step 6: 롤백 경로 확인**

문제 시 이전 이미지 태그로 `gcloud run jobs update --image <PREV>` 되돌림. 이미 `processed=true`인 기사는 재처리 안 되므로 비파괴(spec §8).

---

## 후속 (이 플랜 밖 — 백로그)
- `cluster.py`·`vector_index.py` 물리 삭제(다른 호출자 없음 확인 후 — `test_vector_index.py`도 함께 정리).
- top-k 후보 사전선별(open 스토리 N 커질 때만 — 측정 후).
- news-analytics 후속 능력(렌즈·델타·risk/impact·요약) 인수 시 동일 어댑터 패턴 확장.
- `meta` source `tier` 발행 배선(독립 TODO).

<!-- spec-review: escalated lenses=0 date=2026-06-29 reason=사용자 전략 결정으로 보류(통합 우선, 나중 1회 분리) — 리뷰 불요, 미구현 -->

