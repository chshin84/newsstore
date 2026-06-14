# Step-2 인리치먼트 — Plan 3: LLM 태깅 + 리뷰어 + 임베딩 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:test-driven-development.
> **이 기능은 런타임 LLM 호출** → `disciplined-coder:advisor-nonfunctional`(비기능 체크리스트)·`advisor-fit`(적합성) 적용. **각 서브에이전트에 `coding-principles` + `solved_problems`의 '핵심 gotchas' 주입**(`docs/subagent-context.md`). unsolved는 주입 X.

**Goal:** raw 기사를 Gemini Flash로 통제어휘 태깅하고 Gemini 임베딩으로 벡터화한다. **결정론 검증을 코드로 먼저**(어휘 멤버십·티커 수·스키마), LLM 리뷰 콜은 결정론으로 못 잡는 grounding에만 리스크 비례로(현재 보류, 훅만 남김).

**Architecture:** LLM 클라이언트를 **Protocol로 추상화(DI)** — 로직(tagger/embedder)은 fake 클라이언트로 TDD(google-genai 불요), 실 `GeminiClient`만 SDK에 의존(lazy import). 스토어 계층(Store Protocol + 주입 client)과 동일 패턴. 비기능 요건(timeout/retry/None가드/구조화에러/비용상한/관측/비밀분리)은 `GeminiClient` 래퍼에 배선하되, **저수준 호출 callable을 주입**받게 해 retry/None가드 로직 자체도 fake callable로 테스트.

**Tech Stack:** Python 3.12, google-genai(실 클라이언트만, lazy import), pytest, Docker. 결제 $0(Tier3 한도).

**Spec:** `docs/superpowers/specs/2026-06-13-newsstore-step2-enrichment-design.md` §2·§5·§6·§9.

**테스트:** `MSYS_NO_PATHCONV=1 docker run --rm -v "D:/projects/newsstore:/app" newsstore pytest -q <파일>`.

---

## 설계 결정 (disciplined-coder 적용)
- **결정론 우선(advisor-fit)**: entities/topics는 taxonomy SSOT 멤버십, tickers는 정규식+개수 상한(≤5)을 **코드로** 검증·필터(비파괴: 원본 raw 응답은 로깅, 저장 tags는 검증 통과분). LLM 리뷰 콜은 결정론 불가한 환각 grounding에만 — **이번 Plan은 훅(`review_grounding` 미구현 stub)만, 실호출 보류**(비용·$0, 리스크 재평가 후).
- **비기능(advisor-nonfunctional)**: `GeminiClient`에 timeout·지수백오프 retry·`None가드`·구조화 에러(`LLMError`)·배치 상한(10)·관측 로깅·`GEMINI_API_KEY` env(로그/프롬프트 비노출). 전부 결정론 → 정적·단위 테스트로 검증.
- **차원 계약**: 임베딩 벡터 길이를 `EMBED_DIM`(768)로 검증(fail-loud) — Plan 1의 `cosine`/`add_vectors` dim 가드와 정합.

## File Structure
- Create `src/newsstore/enrich/llm.py` — `LLMClient` Protocol + `GeminiClient`(주입 callable 래퍼, 비기능) + `LLMError`.
- Create `src/newsstore/enrich/tagger.py` — 프롬프트 빌드 + 결정론 검증 + `tag_items`.
- Create `src/newsstore/enrich/embedder.py` — 텍스트 준비 + `embed_items` + dim 검증.
- Create `tests/test_llm_client.py`, `tests/test_tagger.py`, `tests/test_embedder.py`.
- Modify `pyproject.toml` — optional extra `enrich = ["google-genai>=1.0"]`.

---

## Task 1: GeminiClient 비기능 래퍼 (timeout/retry/None가드/구조화에러)

**Files:** Create `src/newsstore/enrich/llm.py`, `tests/test_llm_client.py`.

저수준 호출을 `call_fn: Callable[[], Any]`로 주입받아 retry/None가드/에러형식을 입힌다(실 SDK 호출은 `GeminiClient`가 `call_fn`으로 감쌈). 테스트는 fake `call_fn`(예외 N회 후 성공, None 반환 등)으로 검증.

- [ ] **Step 1: 실패 테스트** — `tests/test_llm_client.py`:
```python
import pytest
from newsstore.enrich.llm import call_with_retry, LLMError

def test_retry_succeeds_after_transient():
    calls = {"n": 0}
    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise TimeoutError("transient")
        return {"ok": True}
    assert call_with_retry(flaky, attempts=3, base_delay=0) == {"ok": True}
    assert calls["n"] == 3

def test_retry_exhausts_raises_llmerror():
    def always():
        raise TimeoutError("nope")
    with pytest.raises(LLMError):
        call_with_retry(always, attempts=2, base_delay=0)

def test_none_response_raises_llmerror():
    with pytest.raises(LLMError):
        call_with_retry(lambda: None, attempts=1, base_delay=0)
```

- [ ] **Step 2: 실패 확인** — `ImportError`/`AttributeError`.

- [ ] **Step 3: 구현** — `llm.py`:
```python
from __future__ import annotations
import logging, time
from typing import Any, Callable, Protocol

log = logging.getLogger("newsstore.enrich.llm")

class LLMError(RuntimeError):
    """LLM 호출 실패(타임아웃/레이트리밋/빈 응답)를 호출자가 처리할 구조화 에러."""

class LLMClient(Protocol):
    def generate_json(self, prompt: str, *, timeout: float) -> dict: ...
    def embed(self, text: str, *, timeout: float) -> list[float]: ...

def call_with_retry(call_fn: Callable[[], Any], *, attempts: int = 3,
                    base_delay: float = 0.5) -> Any:
    """지수 백오프 retry + None가드. 모두 실패 시 LLMError. (비기능: advisor-nonfunctional)"""
    last = None
    for i in range(attempts):
        try:
            r = call_fn()
        except Exception as e:               # transient (timeout/ratelimit/5xx)
            last = e
            log.warning("LLM call failed (attempt %d/%d): %s", i + 1, attempts, e)
            if i + 1 < attempts:
                time.sleep(base_delay * (2 ** i))
            continue
        if r is None:                        # 빈/실패 응답 None 가드
            last = LLMError("empty response")
            log.warning("LLM empty response (attempt %d/%d)", i + 1, attempts)
            if i + 1 < attempts:
                time.sleep(base_delay * (2 ** i))
            continue
        return r
    raise LLMError(f"LLM call failed after {attempts} attempts") from last
```
`GeminiClient`(lazy import, 실 경로 — 단위테스트는 안 함, Task4 라이브 스모크):
```python
class GeminiClient:
    """실 Gemini(google-genai). API key는 env GEMINI_API_KEY(로그/프롬프트 비노출)."""
    DEFAULT_TIMEOUT = 30.0
    def __init__(self, api_key: str, *, model: str = "gemini-2.0-flash",
                 embed_model: str = "text-multilingual-embedding-002"):
        from google import genai            # lazy: SDK 없어도 모듈 import 가능
        self._client = genai.Client(api_key=api_key)
        self._model, self._embed_model = model, embed_model
    def generate_json(self, prompt: str, *, timeout: float = DEFAULT_TIMEOUT) -> dict:
        import json
        def _call():
            from google.genai import types
            r = self._client.models.generate_content(
                model=self._model, contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    http_options=types.HttpOptions(timeout=int(timeout * 1000))))
            return getattr(r, "text", None)
        raw = call_with_retry(_call)
        try:
            return json.loads(raw)
        except (TypeError, ValueError) as e:
            raise LLMError(f"non-JSON response: {e}") from e
    def embed(self, text: str, *, timeout: float = DEFAULT_TIMEOUT) -> list[float]:
        def _call():
            r = self._client.models.embed_content(model=self._embed_model, contents=text)
            embs = getattr(r, "embeddings", None)
            return embs[0].values if embs else None
        return list(call_with_retry(_call))
```

- [ ] **Step 4: 통과 확인** — `pytest -q tests/test_llm_client.py` (3 passed).
- [ ] **Step 5: 커밋** — `feat: GeminiClient retry/None-guard/structured-error wrapper (nonfunctional)`.

---

## Task 2: 태거 — 프롬프트 빌드 + 결정론 검증(어휘/티커/스키마)

**Files:** Create `src/newsstore/enrich/tagger.py`, `tests/test_tagger.py`.

- [ ] **Step 1: 실패 테스트** — `tests/test_tagger.py`:
```python
from newsstore.enrich.tagger import validate_tags, MAX_TICKERS

TAX = {"entities": ["Fed", "ECB"], "topics": ["rates", "inflation"]}

def test_validate_keeps_only_vocab_entities_topics():
    raw = {"tickers": ["NVDA"], "entities": ["Fed", "BOGUS"], "topics": ["rates", "xxx"]}
    out = validate_tags(raw, TAX)
    assert out["entities"] == ["Fed"]
    assert out["topics"] == ["rates"]
    assert out["tickers"] == ["NVDA"]

def test_validate_caps_tickers():
    raw = {"tickers": [f"T{i}" for i in range(MAX_TICKERS + 3)], "entities": [], "topics": []}
    assert len(validate_tags(raw, TAX)["tickers"]) == MAX_TICKERS

def test_validate_rejects_bad_ticker_format():
    raw = {"tickers": ["NVDA", "not a ticker!", "AAPL"], "entities": [], "topics": []}
    assert validate_tags(raw, TAX)["tickers"] == ["NVDA", "AAPL"]

def test_validate_missing_keys_default_empty():
    assert validate_tags({}, TAX) == {"tickers": [], "entities": [], "topics": []}
```

- [ ] **Step 2: 실패 확인**.

- [ ] **Step 3: 구현** — `tagger.py`:
```python
from __future__ import annotations
import re
from .llm import LLMClient

MAX_TICKERS = 5
_TICKER_RE = re.compile(r"^[A-Z0-9]{1,6}(\.[A-Z]{1,3})?$")   # NVDA, 000660.KS

def validate_tags(raw: dict, taxonomy: dict) -> dict:
    """결정론 적합성 검증(advisor-fit): 어휘 밖·형식위반·과다 티커 제거. 비파괴(저장 전 필터)."""
    ent = [e for e in (raw or {}).get("entities", []) if e in set(taxonomy["entities"])]
    top = [t for t in (raw or {}).get("topics", []) if t in set(taxonomy["topics"])]
    tick = [t for t in (raw or {}).get("tickers", []) if isinstance(t, str) and _TICKER_RE.match(t)]
    return {"tickers": tick[:MAX_TICKERS], "entities": ent, "topics": top}

def build_prompt(items: list, taxonomy: dict) -> str:
    """통제어휘를 프롬프트에 SSOT로 주입. 사건명은 태그 아님(스토리)."""
    ents = ", ".join(taxonomy["entities"]); tops = ", ".join(taxonomy["topics"])
    lines = [f'{i}. {it.title} :: {(it.body or "")[:200]}' for i, it in enumerate(items)]
    return (
        "You tag financial news. For each item return tickers (extract), "
        f"entities (ONLY from: {ents}), topics (ONLY from: {tops}). "
        "Events (e.g. a war) are NOT tags. Return JSON {\"results\":[{\"tickers\":[],"
        "\"entities\":[],\"topics\":[]}]} in item order.\n" + "\n".join(lines))

def tag_items(items: list, client: LLMClient, taxonomy: dict, *, batch: int = 10) -> list[dict]:
    """≤batch건씩 태깅 → 결정론 검증. 결과 수 불일치 시 빈 태그로 정렬 보존(fail-soft)."""
    out: list[dict] = []
    for s in range(0, len(items), batch):
        chunk = items[s:s + batch]
        resp = client.generate_json(build_prompt(chunk, taxonomy), timeout=30.0)
        results = (resp or {}).get("results", [])
        for j in range(len(chunk)):
            raw = results[j] if j < len(results) else {}
            out.append(validate_tags(raw, taxonomy))
    return out
```

- [ ] **Step 4: 통과 확인** — `pytest -q tests/test_tagger.py` (4 passed).
- [ ] **Step 5: 커밋** — `feat: tagger — deterministic vocab/ticker fit-validation + batch tagging`.

---

## Task 3: 임베더 — 텍스트 준비 + dim 검증

**Files:** Create `src/newsstore/enrich/embedder.py`, `tests/test_embedder.py`.

- [ ] **Step 1: 실패 테스트** — `tests/test_embedder.py`:
```python
import pytest
from datetime import datetime, timezone
from newsstore.models import RawItem
from newsstore.enrich.embedder import embed_text, embed_items, EMBED_DIM

NOW = datetime(2026, 6, 14, tzinfo=timezone.utc)
def _item(t, b=""):
    return RawItem(id="a", feed_id="f", source="S", url="https://e/a", title=t, body=b, fetched_at=NOW)

class _FakeClient:
    def __init__(self, vec): self.vec = vec; self.seen = []
    def generate_json(self, *a, **k): ...
    def embed(self, text, *, timeout=30.0): self.seen.append(text); return list(self.vec)

def test_embed_text_joins_title_body_capped():
    assert embed_text(_item("T", "B" * 1000)).startswith("T")
    assert len(embed_text(_item("T", "B" * 1000))) <= 1 + 1 + 500

def test_embed_items_returns_vectors():
    c = _FakeClient([0.1] * EMBED_DIM)
    out = embed_items([_item("T", "B")], c)
    assert out == [[0.1] * EMBED_DIM]

def test_embed_items_rejects_wrong_dim():
    c = _FakeClient([0.1] * 3)               # 잘못된 차원
    with pytest.raises(ValueError):
        embed_items([_item("T")], c)
```

- [ ] **Step 2: 실패 확인**.

- [ ] **Step 3: 구현** — `embedder.py`:
```python
from __future__ import annotations
from .llm import LLMClient

EMBED_DIM = 768
BODY_CAP = 500

def embed_text(item) -> str:
    """title + 본문(≤500자). spec §5.4."""
    return f"{item.title} {(item.body or '')[:BODY_CAP]}".strip()

def embed_items(items: list, client: LLMClient) -> list[list[float]]:
    """기사당 1회 임베딩. 차원 불일치는 fail-loud(원칙3, cosine/add_vectors와 정합)."""
    out = []
    for it in items:
        vec = client.embed(embed_text(it), timeout=30.0)
        if len(vec) != EMBED_DIM:
            raise ValueError(f"embedding dim {len(vec)} != {EMBED_DIM}")
        out.append(vec)
    return out
```

- [ ] **Step 4: 통과 + 전체 회귀** — `pytest -q tests/test_embedder.py`(3) → 전체 `pytest -q`(79 + 3+4+3 = **89 passed**).
- [ ] **Step 5: 커밋** — `feat: embedder — title+body prep + 768-dim fail-loud check`.

---

## Task 4 (보류 — 라이브, 키 필요): google-genai 의존성 + 라이브 스모크
- `pyproject.toml`에 `enrich` extra 추가, `infra/requirements.lock` 재생성, Dockerfile `INSTALL_ENRICH` build-arg.
- `GeminiClient`로 소량(3~5건) 실태깅·실임베딩 스모크(별도 스크립트, CI 제외). **이미지 재빌드 필요·`GEMINI_API_KEY` 주입** → 사용자 게이트.
- → 이후 **Plan 4**: Processor 오케스트레이션(get_unprocessed→classify→tag→embed→assign→save_enrichment/mark_processed) + base.py 뷰 read 계약 + Cloud Run Job#2/Scheduler#2.

## Self-Review (작성자 체크)
- **Spec 커버리지**: §2 모델·§5.2 태깅·§5.4 임베딩·§6 어휘 = Task1~3. §5.3 리뷰어 = 결정론 검증으로 대체(LLM grounding은 훅 보류).
- **disciplined-coder**: 비기능 8항목 = Task1(timeout/retry/None/에러/비용배치/관측/비밀) · 적합성 = Task2 결정론 validator(코드 우선) · 차원계약 = Task3.
- **타입 일관**: `LLMClient.generate_json(prompt,*,timeout)->dict` · `embed(text,*,timeout)->list[float]` 전 모듈 일관. DI라 google-genai 없이 로직 테스트.
- **비파괴**: 검증 탈락 태그는 제거하되 원본 raw는 로깅(저장 tags만 필터). 결과수 불일치는 빈 태그로 정렬 보존.
