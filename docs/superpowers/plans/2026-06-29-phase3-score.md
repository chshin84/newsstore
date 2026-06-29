# Phase 3 — Dual Score (risk/impact) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:test-driven-development. Steps use checkbox (`- [ ]`). 매 Task: 실패 테스트 먼저 → 구현 → 통과 → commit.

**Goal:** 열린 스토리에 dual score(`risk`/`impact` 0~3) + advisory reason을 LLM 1콜로 매겨 비파괴 저장한다. type-aware 게이트(standing/watch=상시, 그 외=멤버수≥MIN) + incremental(`count>scored_count`).

**Architecture:** `enrich/scorer.py`(순수 로직: gate `should_score` + `validate_score` + `build_score_input`/`build_score_prompt` + `score_story` + 오케스트레이션 `run_score_pass`) → store `get_stories_for_scoring`/`save_story_score`(merge·비파괴) → `run_enrich --mode score`. 토대: `topics.lens_type`(Phase 1), `get_story_members`(요약 패스), `GeminiClient.generate_json`(retry/None가드).

**Tech Stack:** Python 3.12, Docker(`MSYS_NO_PATHCONV=1 docker compose run --rm test`). 새 의존성 0.

**Spec:** `docs/superpowers/specs/2026-06-29-phase3-score-design.md` (3렌즈 리뷰 passed)

**핵심 gotchas:** 매직넘버 금지(`SCORE_MIN`/`SCORE_MAX`/`MATERIALITY_MIN_MEMBERS` 상수, 불변식 테스트) · LLM None/장애 가드(fail-soft, 스토리 단위) · merge=비파괴(자기 필드만, read 없음) · incremental 멱등(`count>scored_count`) · unknown lens id → KeyError 금지, emergent 강등 · 멤버 0+요약 없음 → None(크래시 금지) · reason은 advisory(결측→빈문자열, 드롭 아님).

---

## File Structure
| 파일 | 책임 | 변경 |
|---|---|---|
| `src/newsstore/enrich/scorer.py` | gate + validator + score_story + run_score_pass | Create |
| `src/newsstore/store/firestore_store.py` | `get_stories_for_scoring` + `save_story_score` | Modify |
| `src/newsstore/contracts/ports.py` | Store 계약에 두 메서드 | Modify |
| `src/newsstore/entrypoints/run_enrich.py` | `--mode score` 패스 | Modify |
| `docs/firestore-contract.md` | `stories.{risk,impact,risk_reason,impact_reason,scored_count}` 필드 | Modify |
| `tests/test_scorer.py` | validator·gate·score_story 단위(fake LLM, no emulator) | Create |
| `tests/test_score_pass.py` | run_score_pass 통합(에뮬레이터 store) | Create |
| `tests/test_firestore_store.py` | store 계약(라운드트립·비파괴·incremental) | Modify |

---

## Task 1: scorer 순수 로직 — validator + gate (단위, 에뮬레이터 불필요)

**Files:** Create `src/newsstore/enrich/scorer.py`, `tests/test_scorer.py`

- [ ] **Step 1: 실패 테스트** — `tests/test_scorer.py`:
```python
from newsstore.enrich import topics
from newsstore.enrich.scorer import (validate_score, should_score,
                                      SCORE_MIN, SCORE_MAX, MATERIALITY_MIN_MEMBERS)

T = topics.load_topics()


def test_validate_in_range_keeps_scores():
    v = validate_score({"risk": 2, "impact": 3, "risk_reason": "war", "impact_reason": "oil"})
    assert v == {"risk": 2, "impact": 3, "risk_reason": "war", "impact_reason": "oil"}


def test_validate_out_of_range_drops():
    assert validate_score({"risk": SCORE_MAX + 1, "impact": 1}) is None
    assert validate_score({"risk": SCORE_MIN - 1, "impact": 1}) is None
    assert validate_score({"risk": 1}) is None              # impact 결측
    assert validate_score({"risk": "high", "impact": 1}) is None  # 비정수
    assert validate_score({"risk": True, "impact": 1}) is None    # bool 거부
    assert validate_score(None) is None


def test_validate_reason_advisory_optional():
    v = validate_score({"risk": 0, "impact": 0})           # reason 결측 → 빈문자열, 점수 보존
    assert v["risk"] == 0 and v["impact"] == 0
    assert v["risk_reason"] == "" and v["impact_reason"] == ""


def test_gate_standing_watch_always():
    assert should_score(["kr_rates"], T, count=1) is True        # standing 멤버 1
    assert should_score(["watch_samsung"], T, count=1) is True   # watch 멤버 1


def test_gate_nonfinancial_needs_min_members():
    assert should_score(["kr_econ"], T, count=1) is False        # development 1 → 차단
    assert should_score(["kr_econ"], T, count=MATERIALITY_MIN_MEMBERS) is True
    assert should_score(["risk"], T, count=1) is False
    assert should_score([], T, count=1) is False                 # emergent 무렌즈
    assert should_score([], T, count=MATERIALITY_MIN_MEMBERS) is True


def test_gate_mixed_financial_wins():
    assert should_score(["kr_econ", "watch_samsung"], T, count=1) is True


def test_gate_unknown_id_demoted_to_emergent():
    assert should_score(["NOT_A_LENS"], T, count=1) is False     # KeyError 안 남, 보수 차단
    assert should_score(["NOT_A_LENS"], T, count=MATERIALITY_MIN_MEMBERS) is True
```

- [ ] **Step 2: 실패 확인** — FAIL(ModuleNotFound).

- [ ] **Step 3: 구현** — `src/newsstore/enrich/scorer.py` (gate + validator 부분, 나머지는 Task 2). 상수: `SCORE_MIN=0, SCORE_MAX=3, MATERIALITY_MIN_MEMBERS=2, ALWAYS_SCORE_TYPES={"standing","watch"}, MAX_REASON=200`. `should_score(lenses, t, count, *, min_members=MATERIALITY_MIN_MEMBERS)`: lens id→`lens_type` 역참조(unknown id는 try/except로 무시=emergent), 타입 ∩ ALWAYS_SCORE_TYPES면 True, 아니면 `count>=min_members`. `validate_score(raw)`: `_is_int`(bool 거부) + 범위 → 아니면 None; reason은 str이면 strip[:MAX_REASON] 아니면 "".

- [ ] **Step 4: 통과** — `... pytest tests/test_scorer.py -v` → PASS.

- [ ] **Step 5: Commit** — `feat(enrich): dual-score gate + deterministic validator (range 0-3, type-aware materiality)`

---

## Task 2: score_story + 프롬프트/입력 구성 (단위, fake LLM)

**Files:** Modify `src/newsstore/enrich/scorer.py`, `tests/test_scorer.py`

- [ ] **Step 1: 실패 테스트** 추가:
```python
class _FakeLLM:
    def __init__(self, resp): self.resp = resp; self.seen = None
    def generate_json(self, prompt, *, timeout=30.0):
        self.seen = prompt; return self.resp


def test_score_story_uses_summary():
    from newsstore.enrich.scorer import score_story
    llm = _FakeLLM({"risk": 2, "impact": 1, "risk_reason": "r", "impact_reason": "i"})
    out = score_story({"title": "Hormuz", "summary": "tanker strike", "developments": []},
                      members=None, client=llm)
    assert out["risk"] == 2 and out["impact"] == 1
    assert "tanker strike" in llm.seen


def test_score_story_member_fallback():
    from newsstore.enrich.scorer import score_story
    llm = _FakeLLM({"risk": 0, "impact": 0})
    out = score_story({"title": "t", "summary": "", "developments": []},
                      members=[{"title": "Fed hikes"}], client=llm)
    assert out["risk"] == 0 and "Fed hikes" in llm.seen


def test_score_story_empty_input_returns_none():
    from newsstore.enrich.scorer import score_story
    llm = _FakeLLM({"risk": 1, "impact": 1})
    assert score_story({"title": "", "summary": "", "developments": []},
                       members=[], client=llm) is None    # 빈 입력 → 스킵(크래시 금지)


def test_score_story_failsoft_on_llm_error():
    from newsstore.enrich.scorer import score_story
    class _Boom:
        def generate_json(self, prompt, *, timeout=30.0): raise RuntimeError("down")
    out = score_story({"title": "x", "summary": "s", "developments": []},
                      members=None, client=_Boom())
    assert out is None
```

- [ ] **Step 2: 실패 확인** — FAIL.

- [ ] **Step 3: 구현** — `build_score_input(story, members)`: summary + dev texts; 비면 members[:N] 제목; title은 항상 프롬프트 헤더. `build_score_prompt(title, body)`: 한국어, risk/impact 0~3 루브릭(§3) 명시, JSON `{risk,impact,risk_reason,impact_reason}`만. `score_story(story, members, client, *, timeout=30.0)`: 입력 비면 None; `try: raw=client.generate_json(...) except Exception: return None`; `validate_score(raw)`.

- [ ] **Step 4: 통과** — PASS.

- [ ] **Step 5: Commit** — `feat(enrich): score_story (summary→member fallback, fail-soft, dual-score prompt)`

---

## Task 3: store — get_stories_for_scoring + save_story_score

**Files:** Modify `firestore_store.py`, `ports.py`, `tests/test_firestore_store.py`

- [ ] **Step 1: 실패 테스트** 추가(에뮬레이터):
```python
def test_save_and_read_story_score(store):
    from datetime import datetime, timezone, timedelta
    now = datetime(2026, 6, 29, tzinfo=timezone.utc)
    store.create_story("s1", title="t", vec=[1.0], member_id="a", entities=[], now=now)
    store.save_story_lenses("s1", ["kr_rates"], count=1)
    store.save_story_summary("s1", title="t", summary="sum", latest="l",
                             developments=[{"text": "d", "time": now, "source_count": 1}],
                             summary_count=1, now=now)
    rows = store.get_stories_for_scoring(cutoff=now - timedelta(hours=1))
    assert rows and rows[0]["id"] == "s1"
    assert rows[0]["lenses"] == ["kr_rates"] and rows[0]["summary"] == "sum"
    store.save_story_score("s1", risk=2, impact=1, risk_reason="r", impact_reason="i",
                           count=1, now=now)
    # 비파괴: 점수 저장 후 summary/lenses 보존
    d = store.db.collection("stories").document("s1").get().to_dict()
    assert d["risk"] == 2 and d["impact"] == 1 and d["summary"] == "sum" and d["lenses"] == ["kr_rates"]
    # incremental: scored_count=1 == count → 재조회 안 뜸
    assert store.get_stories_for_scoring(cutoff=now - timedelta(hours=1)) == [] \
        or all(r["id"] != "s1" for r in store.get_stories_for_scoring(cutoff=now - timedelta(hours=1)))
```
(테스트는 store.db 직접 read로 *검증만* — 프로덕션 코드는 store.db 직접접근 안 함.)

- [ ] **Step 2: 실패 확인** — FAIL.

- [ ] **Step 3: 구현** — `firestore_store.py`:
  - `get_stories_for_scoring(cutoff)`: `get_stories_for_lensing` 미러, `count<=scored_count` 스킵, 반환 `{id,title,count,lenses,summary,developments}`.
  - `save_story_score(story_id, *, risk, impact, risk_reason, impact_reason, count=None, now=None)`: 점수 필드 단일 `set(merge=True)`; count 있으면 `scored_count`, now 있으면 `scored_at`. read 없음.
  - `ports.py` Store에 두 시그니처 + docstring.

- [ ] **Step 4: 통과 + 회귀** — `... pytest tests/test_firestore_store.py -v` → PASS.

- [ ] **Step 5: Commit** — `feat(store): get_stories_for_scoring + save_story_score (incremental, non-destructive merge)`

---

## Task 4: run_score_pass + `--mode score` 배선 (통합, 에뮬레이터)

**Files:** Modify `scorer.py`, `run_enrich.py`, `tests/test_score_pass.py`

- [ ] **Step 1: 실패 테스트** — `tests/test_score_pass.py`(lens_pass 미러):
```python
from datetime import datetime, timezone, timedelta
from newsstore.contracts.models import RawItem
from newsstore.enrich.scorer import run_score_pass

NOW = datetime(2026, 6, 29, tzinfo=timezone.utc)


def _item(i, **kw):
    base = dict(id=i, feed_id="f", source="S", url=f"https://e/{i}", title="t",
                fetched_at=NOW, asset_hint="", body="b")
    base.update(kw); return RawItem(**base)


class _LLM:
    def generate_json(self, prompt, *, timeout=30.0):
        return {"risk": 2, "impact": 1, "risk_reason": "r", "impact_reason": "i"}


def _score(store, sid):
    return store.db.collection("stories").document(sid).get().to_dict() or {}


def test_standing_story_scored_with_single_member(store):
    store.upsert_items([_item("a", asset_hint="kr_bond")])
    store.create_story("s1", title="한은 금리", vec=[1.0], member_id="a", entities=[], now=NOW)
    store.save_story_lenses("s1", ["kr_rates"], count=1)
    n = run_score_pass(store, _LLM(), now=NOW, cutoff=NOW - timedelta(hours=1))
    assert n["scored"] == 1 and _score(store, "s1")["risk"] == 2


def test_nonfinancial_single_member_gated(store):
    store.upsert_items([_item("b")])
    store.create_story("s2", title="econ", vec=[1.0], member_id="b", entities=[], now=NOW)
    store.save_story_lenses("s2", ["kr_econ"], count=1)
    n = run_score_pass(store, _LLM(), now=NOW, cutoff=NOW - timedelta(hours=1))
    assert n["gated"] == 1 and "risk" not in _score(store, "s2")


def test_incremental_skips_then_rescores(store):
    store.upsert_items([_item("c", asset_hint="crypto")])
    store.create_story("s3", title="btc", vec=[1.0], member_id="c", entities=[], now=NOW)
    store.save_story_lenses("s3", ["crypto"], count=1)
    cut = NOW - timedelta(hours=1)
    assert run_score_pass(store, _LLM(), now=NOW, cutoff=cut)["scored"] == 1
    assert run_score_pass(store, _LLM(), now=NOW, cutoff=cut)["scored"] == 0   # 변화 없음
    store.append_to_story("s3", vec=[1.0], member_id="c2", entities=[], now=NOW)
    assert run_score_pass(store, _LLM(), now=NOW, cutoff=cut)["scored"] == 1   # 새 멤버
```

- [ ] **Step 2: 실패 확인** — FAIL.

- [ ] **Step 3: 구현** — `run_score_pass(store, client, *, now, cutoff, min_members=MATERIALITY_MIN_MEMBERS)`: `t=load_topics()`; totals `{scored,gated,skipped}`; `for st in store.get_stories_for_scoring(cutoff)`: `should_score` 아니면 gated++ continue; members=None, summary/dev 없으면 `store.get_story_members(id)`; `score_story` None이면 skipped; else `save_story_score(... count=st["count"], now=now)` scored++; LLMError/Exception→skipped+log(traceback). `run_enrich.py`: `--mode choices`에 `score` 추가 + 분기(lens_pass 미러, `cutoff=now-OPEN_WINDOW`).

- [ ] **Step 4: 통과** — `... pytest tests/test_score_pass.py -v` → PASS.

- [ ] **Step 5: 전체 그린** — `MSYS_NO_PATHCONV=1 docker compose run --rm test` → FAIL=0.

- [ ] **Step 6: Commit** — `feat(enrich): score pass (--mode score) + run_enrich wiring`

---

## Task 5: 계약 문서

**Files:** Modify `docs/firestore-contract.md`

- [ ] **Step 1** — `stories` 스키마에 `risk·impact·risk_reason·impact_reason·scored_count·scored_at`(newsstore 점수 패스 write, UI read, 없으면 폴백·비파괴) 한 줄 추가. `items` 인리치 줄의 "향후 risk/impact"를 "stories에 산출(Phase 3 완료)"로 갱신.

- [ ] **Step 2: Commit** — `docs: firestore-contract stories risk/impact/scored_count fields (Phase 3)`

---

## 검증 (완료 기준)
- `MSYS_NO_PATHCONV=1 docker compose run --rm test` → **FAIL=0**(scorer 단위·score_pass 통합·store 계약·기존 회귀).
- 불변식: 저장 점수 ∈[0,3] 정수(validator) · standing/watch 멤버 1 채점 · 비금융 멤버 1 게이트 · incremental 멱등 · 비파괴(summary/lenses 보존) · fail-soft.
- 매직넘버 0(상수+불변식). store.db 직접접근 0(프로덕션). 새 의존성 0.

## 후속 (이 플랜 밖)
- Phase 4 UI(impact 임계 노출·emergent 게이트·렌즈 risk 집계·Now Brief) · 스포츠 마킹 · 캘리브레이션(βₖ) · 소스 tier prior · 라이브 배포(`--mode score` Scheduler).

<!-- spec-review: passed lenses=3 date=2026-06-29 (derives from reviewed spec 2026-06-29-phase3-score-design.md) -->
