# Step-2 인리치먼트 — Plan 1: 순수 로직 (taxonomy · classify · cluster) 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (권장) 또는 executing-plans. 스텝은 `- [ ]` 체크박스.
> **SDD 시 각 서브에이전트 프롬프트에 `docs/coding-principles.md` + `docs/solved_problems.md`의 '핵심 gotchas'를 주입**(`docs/subagent-context.md`). unsolved는 주입 X.

**Goal:** 인리치먼트의 *순수 로직* — 통제 어휘 로더, kind 선필터(story/spam/digest), centroid 클러스터링(cosine/assign/centroid) — 을 외부 의존성 없이 TDD로 구현.

**Architecture:** 새 패키지 `src/newsstore/enrich/`에 순수 함수만. 임베딩·LLM·Firestore는 *입력으로 받음*(여기서 생성 X) → 고정 벡터·샘플로 완전 단위 테스트. 후속 Plan(Store확장·LLM·Processor)이 이 위에 얹음.

**Tech Stack:** Python 3.12, pyyaml(기존), pytest, Docker(`docker compose run --rm test`).

**Spec:** `docs/superpowers/specs/2026-06-13-newsstore-step2-enrichment-design.md` (§5 선필터, §6 어휘, §7 클러스터).

**테스트 실행(Docker-only):** `docker compose run --rm test pytest -q <파일>` (전체: `docker compose run --rm test`). compose가 `.`를 자체 마운트 → `$(pwd)` 폴백 회피.

---

## File Structure
- Create `src/newsstore/enrich/__init__.py` — 패키지 마커.
- Create `config/taxonomy.yaml` — 통제 어휘(entities/topics) **SSOT**.
- Create `src/newsstore/enrich/taxonomy.py` — 어휘 로더.
- Create `src/newsstore/enrich/classify.py` — `classify_kind` (선필터, 순수).
- Create `src/newsstore/enrich/cluster.py` — `cosine`, `centroid`, `assign` (순수).
- Create `tests/test_taxonomy.py`, `tests/test_classify.py`, `tests/test_cluster.py`.

---

## Task 1: enrich 패키지 + 통제 어휘 로더

**Files:** Create `src/newsstore/enrich/__init__.py`, `config/taxonomy.yaml`, `src/newsstore/enrich/taxonomy.py`, `tests/test_taxonomy.py`.

- [ ] **Step 1: 실패 테스트**

`tests/test_taxonomy.py`:
```python
from newsstore.enrich.taxonomy import load_taxonomy

def test_load_taxonomy(tmp_path):
    p = tmp_path / "tax.yaml"
    p.write_text("entities: [Fed, ECB]\ntopics: [rates, fx]\n", encoding="utf-8")
    tax = load_taxonomy(p)
    assert tax["entities"] == ["Fed", "ECB"]
    assert tax["topics"] == ["rates", "fx"]

def test_real_taxonomy_has_core_terms():
    tax = load_taxonomy("config/taxonomy.yaml")
    assert "Fed" in tax["entities"]
    assert "rates" in tax["topics"] and "crypto" in tax["topics"]
```

- [ ] **Step 2: 실패 확인**

Run: `docker compose run --rm test pytest -q tests/test_taxonomy.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'newsstore.enrich'`.

- [ ] **Step 3: 구현**

`src/newsstore/enrich/__init__.py`: (빈 파일)
```python
```

`config/taxonomy.yaml`:
```yaml
# 통제 어휘 (SSOT). tickers는 LLM이 기사에서 추출(여기 정의 안 함).
entities: [Fed, ECB, BOJ, PBOC, BOE, 한국은행, Treasury, OPEC, IMF, SEC, WhiteHouse]
topics: [rates, inflation, bonds, fx, crypto, equities, earnings, m&a, ipo, energy,
         tech, regulation, jobs, central_bank, recession, trade, geopolitics,
         commodities, housing, banking]
```

`src/newsstore/enrich/taxonomy.py`:
```python
from __future__ import annotations
from pathlib import Path
import yaml

def load_taxonomy(path="config/taxonomy.yaml") -> dict:
    """통제 어휘 로드 → {'entities': [...], 'topics': [...]}. (tickers는 LLM 추출)"""
    d = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return {"entities": list(d.get("entities", [])), "topics": list(d.get("topics", []))}
```

- [ ] **Step 4: 통과 확인**

Run: `docker compose run --rm test pytest -q tests/test_taxonomy.py`
Expected: PASS (2 passed).

- [ ] **Step 5: 커밋**

```bash
git add src/newsstore/enrich/__init__.py config/taxonomy.yaml src/newsstore/enrich/taxonomy.py tests/test_taxonomy.py
git commit -m "feat: enrich package + controlled taxonomy loader (SSOT)"
```

---

## Task 2: kind 선필터 (story / spam / digest)

**Files:** Create `src/newsstore/enrich/classify.py`, `tests/test_classify.py`.

- [ ] **Step 1: 실패 테스트**

`tests/test_classify.py`:
```python
from newsstore.enrich.classify import classify_kind

def test_digest_more_suffix():
    assert classify_kind("SpaceX IPO, US Vows Interim Deal Will Reopen Hormuz, More") == "digest"

def test_digest_podcast():
    assert classify_kind("Balance of Power: SpaceX Jumps After Record IPO (Podcast)") == "digest"

def test_spam_lawfirm():
    assert classify_kind("FS KKR CAPITAL ALERT: Bragar Eagel Reminds Investors",
                         "lead plaintiff role with the firm") == "spam"

def test_spam_clickbait():
    assert classify_kind("$1000 Invested In KLA 15 Years Ago Would Be Worth This Much Today") == "spam"

def test_normal_story():
    assert classify_kind("Fed holds rates steady amid inflation concerns",
                         "The Federal Reserve kept rates unchanged.") == "story"
```

- [ ] **Step 2: 실패 확인**

Run: `docker compose run --rm test pytest -q tests/test_classify.py`
Expected: FAIL — `ModuleNotFoundError: ...classify`.

- [ ] **Step 3: 구현**

`src/newsstore/enrich/classify.py`:
```python
from __future__ import annotations

# 집단소송 로펌 PR + "$X 투자했다면" 클릭베이트 (web/index.html의 JUNK에서 이식·통합)
SPAM_SIGNALS = [
    "lead plaintiff", "class action", "deadline alert", "shareholder rights law firm",
    "suffered losses in", "encourages investors", "reminds investors", "securities fraud",
    "bragar eagel", "rosen law", "pomerantz", "levi & korsinsky", "glancy prongay",
    "kahn swick", "robbins geller", "faruqi", "schall law", "hagens berman",
    "kessler topaz", "bronstein, gewirtz", "gross law firm", "johnson fistel",
    "kirby mcinerney", "would be worth this much today", "if an investor had bought",
]
# Bloomberg 다이제스트/미디어 롤업 (단일 스토리 아님)
DIGEST_SIGNALS = ["balance of power", "(podcast)", "(video)"]

def classify_kind(title: str, body: str = "") -> str:
    """story | spam | digest. 비파괴 분류 — 저장은 보존, 임베딩/클러스터 제외 여부만 결정."""
    t = (title or "").strip().lower()
    s = f"{t} {(body or '').lower()}"
    if t.endswith(", more") or any(k in s for k in DIGEST_SIGNALS):
        return "digest"
    if any(k in s for k in SPAM_SIGNALS):
        return "spam"
    return "story"
```

- [ ] **Step 4: 통과 확인**

Run: `docker compose run --rm test pytest -q tests/test_classify.py`
Expected: PASS (5 passed).

- [ ] **Step 5: 커밋**

```bash
git add src/newsstore/enrich/classify.py tests/test_classify.py
git commit -m "feat: kind pre-filter (story/spam/digest) — backend port of view JUNK + digest patterns"
```

---

## Task 3: cosine 유사도

**Files:** Create `src/newsstore/enrich/cluster.py`, `tests/test_cluster.py`.

- [ ] **Step 1: 실패 테스트**

`tests/test_cluster.py`:
```python
from newsstore.enrich.cluster import cosine

def test_cosine_identical():
    assert cosine([1, 0, 0], [1, 0, 0]) == 1.0

def test_cosine_orthogonal():
    assert cosine([1, 0], [0, 1]) == 0.0

def test_cosine_similar_high():
    assert cosine([1, 1, 0], [1, 0.9, 0]) > 0.9

def test_cosine_zero_vector_safe():
    assert cosine([0, 0], [1, 1]) == 0.0
```

- [ ] **Step 2: 실패 확인**

Run: `docker compose run --rm test pytest -q tests/test_cluster.py`
Expected: FAIL — `ModuleNotFoundError: ...cluster`.

- [ ] **Step 3: 구현**

`src/newsstore/enrich/cluster.py`:
```python
from __future__ import annotations
import math

def cosine(a: list[float], b: list[float]) -> float:
    """코사인 유사도. 영벡터면 0.0 (0division 회피)."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0
```

- [ ] **Step 4: 통과 확인**

Run: `docker compose run --rm test pytest -q tests/test_cluster.py`
Expected: PASS (4 passed).

- [ ] **Step 5: 커밋**

```bash
git add src/newsstore/enrich/cluster.py tests/test_cluster.py
git commit -m "feat: cosine similarity (zero-vector safe)"
```

---

## Task 4: centroid + assign (스토리 배정)

**Files:** Modify `src/newsstore/enrich/cluster.py`, `tests/test_cluster.py`.

- [ ] **Step 1: 실패 테스트 추가**

`tests/test_cluster.py`에 추가:
```python
from newsstore.enrich.cluster import centroid, assign

def test_centroid_mean():
    assert centroid([2, 4, 6], 2) == [1.0, 2.0, 3.0]

def test_assign_joins_most_similar_open_story():
    stories = [{"id": "s1", "centroid": [1, 0, 0]}, {"id": "s2", "centroid": [0, 1, 0]}]
    assert assign([0.99, 0.01, 0], stories) == "s1"

def test_assign_new_story_when_dissimilar():
    stories = [{"id": "s1", "centroid": [1, 0, 0]}]
    assert assign([0, 1, 0], stories) is None        # 새 스토리 신호

def test_assign_respects_threshold():
    stories = [{"id": "s1", "centroid": [1, 0, 0]}]
    assert assign([0.9, 0.1, 0], stories, threshold=0.999) is None   # 높은 임계 → 불합격
    assert assign([0.9, 0.1, 0], stories, threshold=0.5) == "s1"     # 낮은 임계 → 합격

def test_assign_empty_stories_is_new():
    assert assign([1, 0, 0], []) is None
```

- [ ] **Step 2: 실패 확인**

Run: `docker compose run --rm test pytest -q tests/test_cluster.py::test_assign_joins_most_similar_open_story`
Expected: FAIL — `ImportError: cannot import name 'assign'`.

- [ ] **Step 3: 구현 (cluster.py에 추가)**

`src/newsstore/enrich/cluster.py` 끝에 추가:
```python
DEFAULT_THRESHOLD = 0.83

def centroid(centroid_sum: list[float], count: int) -> list[float]:
    """중심 = 누적합 / 개수."""
    return [x / count for x in centroid_sum]

def assign(vec: list[float], open_stories: list[dict],
           threshold: float = DEFAULT_THRESHOLD) -> str | None:
    """가장 유사한 '열린 스토리' id를 반환(코사인 ≥ threshold). 없으면 None(=새 스토리).
    open_stories: [{'id': str, 'centroid': list[float]}]. centroid 기준이라 전이 연쇄 없음."""
    best_id, best_sim = None, 0.0
    for st in open_stories:
        s = cosine(vec, st["centroid"])
        if s > best_sim:
            best_sim, best_id = s, st["id"]
    return best_id if best_sim >= threshold else None
```

- [ ] **Step 4: 통과 확인 (전체 cluster 테스트)**

Run: `docker compose run --rm test pytest -q tests/test_cluster.py`
Expected: PASS (9 passed).

- [ ] **Step 5: 전체 스위트 회귀 확인 + 커밋**

Run: `docker compose run --rm test`
Expected: 기존 47 + 신규(taxonomy 2 + classify 5 + cluster 9 = 16) → 63 passed, 회귀 0.

```bash
git add src/newsstore/enrich/cluster.py tests/test_cluster.py
git commit -m "feat: centroid + assign (online story matching, threshold 0.83, no transitive chaining)"
```

---

## Self-Review (작성자 체크 완료)
- **Spec 커버리지**: §6 어휘=Task1 · §5 선필터=Task2 · §7 cosine/centroid/assign=Task3·4. (LLM 태깅·임베딩·Store·Processor는 후속 Plan — 범위 밖 명시.)
- **플레이스홀더**: 없음(모든 스텝에 실제 코드·명령·기대값).
- **타입 일관성**: `cosine(a,b)`·`centroid(sum,count)`·`assign(vec, open_stories, threshold)` 전 태스크 일관. open_stories 스키마 `{'id','centroid'}` 일관.

## 다음 Plan (이 Plan 그린 후)
- **Plan 2** — Store 확장: `items` enrichment 쓰기(kind/tags/embedding/story_id) + `stories` 컬렉션 + `get_open_stories(window)` + `create_story`/`append_to_story`(centroid 증분). sqlite+firestore, mock 테스트.
- **Plan 3** — Gemini Flash 태깅(10배치)+리뷰어 + Gemini 임베딩(Tier3 키). 모킹 테스트 + 라이브 소량.
- **Plan 4** — Processor 오케스트레이션 + Cloud Run Job #2 + Scheduler 배포.
