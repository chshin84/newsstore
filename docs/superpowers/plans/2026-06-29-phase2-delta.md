# Phase 2 — 델타(2-타임스탬프 + milestone) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** 요약 패스 각 development에 `delta_time`(우리 스토어 새 정보 편입 시각)을 부여하고, LLM milestone(`is_new`) 게이트로 recap이 새 델타로 안 올라오게 한다.

**Architecture:** 순수 배정 로직은 신규 `enrich/milestone.py`(`assign_delta_times`)에 격리. milestone은 기존 요약 LLM 콜에 편승(`build_summary_prompt`에 prior 섹션 + `is_new` 요청, 추가 콜 0). store는 `get_stories_needing_summary`가 prior developments를 함께 반환(추가 read 0). 전부 additive·비파괴.

**Tech Stack:** Python, Firestore(에뮬레이터), pytest, FakeLLM 단위. 테스트는 Docker 전용: `MSYS_NO_PATHCONV=1 docker compose run --rm test`.

**규율:** TDD(실패 먼저). 매직넘버 금지(명명 상수). None 가드. 비파괴 merge. 검증 후 주장(FAIL=0 증거). 인라인 주석 남발 금지(설계 의도만).

---

## File Structure
- Create: `src/newsstore/enrich/milestone.py` — `MILESTONE_PRIOR_MAX`, `assign_delta_times`, `prior_texts`(순수).
- Create: `tests/test_milestone.py` — 순수 단위(fake 없음).
- Modify: `src/newsstore/enrich/summarizer.py` — `build_summary_prompt`(prior_developments), `validate_summary`(is_new), `summarize_story`(prior_developments→assign_delta_times), `run_summary_pass`(prior 배선).
- Modify: `tests/test_summarizer.py` — prior/is_new/delta_time 확장(+ 하위호환 유지).
- Modify: `src/newsstore/store/firestore_store.py` — `get_stories_needing_summary` developments 추가.
- Modify: `src/newsstore/contracts/ports.py` — docstring 갱신.
- Modify: `tests/test_store_summary.py` — developments 반환 + delta_time 저장.
- Modify: `docs/firestore-contract.md` — delta_time 현재화.

---

## Task 1: milestone.py 순수 배정 로직

**Files:** Create `src/newsstore/enrich/milestone.py`, Test `tests/test_milestone.py`

- [ ] **Step 1: 실패 테스트 작성** (`tests/test_milestone.py`)

```python
"""Phase 2 — delta_time 배정 순수 로직(LLM·store 없음)."""
from datetime import datetime, timezone, timedelta
from newsstore.enrich.milestone import assign_delta_times, prior_texts, MILESTONE_PRIOR_MAX

T0 = datetime(2026, 6, 20, 7, 0, tzinfo=timezone.utc)


def _dev(text, h, *, is_new=None, delta_h=None):
    d = {"text": text, "time": T0 + timedelta(hours=h), "source_count": 1}
    if is_new is not None:
        d["is_new"] = is_new
    if delta_h is not None:
        d["delta_time"] = T0 + timedelta(hours=delta_h)
    return d


def test_no_prior_all_get_time():
    devs = [_dev("a", 0, is_new=True), _dev("b", 2, is_new=False)]
    out = assign_delta_times(devs, prior_developments=[])
    assert [d["delta_time"] for d in out] == [T0, T0 + timedelta(hours=2)]
    assert all("is_new" not in d for d in out)            # is_new는 내부 신호, 저장 안 함


def test_is_new_true_with_prior_uses_time():
    prior = [_dev("old", 0, delta_h=0)]
    out = assign_delta_times([_dev("fresh", 5, is_new=True)], prior_developments=prior)
    assert out[0]["delta_time"] == T0 + timedelta(hours=5)


def test_recap_inherits_frontier():
    prior = [_dev("p1", 0, delta_h=0), _dev("p2", 2, delta_h=2)]   # frontier = T0+2h
    out = assign_delta_times([_dev("recap", 9, is_new=False)], prior_developments=prior)
    assert out[0]["delta_time"] == T0 + timedelta(hours=2)         # not its own 9h


def test_recap_of_old_still_frontier_approximation():
    prior = [_dev("p1", 0, delta_h=0), _dev("p2", 2, delta_h=2)]
    out = assign_delta_times([_dev("recap-of-p1", 9, is_new=False)], prior_developments=prior)
    assert out[0]["delta_time"] == T0 + timedelta(hours=2)         # 근사: 프런티어 미초과 불변식


def test_legacy_prior_without_delta_time_backfills_time():
    prior = [{"text": "p", "time": T0, "source_count": 1}]          # no delta_time → frontier None
    out = assign_delta_times([_dev("x", 3, is_new=False)], prior_developments=prior)
    assert out[0]["delta_time"] == T0 + timedelta(hours=3)          # frontier None → time


def test_missing_is_new_with_prior_is_recap():
    prior = [_dev("p", 0, delta_h=0)]
    out = assign_delta_times([_dev("x", 5)], prior_developments=prior)   # is_new 누락
    assert out[0]["delta_time"] == T0                               # 보수적 recap → frontier


def test_missing_is_new_no_prior_advances():
    out = assign_delta_times([_dev("x", 5), _dev("y", 6)], prior_developments=[])
    assert [d["delta_time"] for d in out] == [T0 + timedelta(hours=5), T0 + timedelta(hours=6)]


def test_non_bool_is_new_treated_as_recap():
    prior = [_dev("p", 0, delta_h=0)]
    out = assign_delta_times([{"text": "x", "time": T0 + timedelta(hours=5),
                               "source_count": 1, "is_new": "yes"}], prior_developments=prior)
    assert out[0]["delta_time"] == T0                               # "yes"!=True → recap


def test_prior_texts_caps_and_recent_first():
    prior = [_dev(f"d{i}", i, delta_h=i) for i in range(MILESTONE_PRIOR_MAX + 3)]
    texts = prior_texts(prior)
    assert len(texts) == MILESTONE_PRIOR_MAX
    assert texts[0] == f"d{MILESTONE_PRIOR_MAX + 2}"               # 최신(time desc) 먼저
```

- [ ] **Step 2: 실패 확인** — `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest -q tests/test_milestone.py`. Expected: FAIL (ModuleNotFoundError milestone).

- [ ] **Step 3: 최소 구현** (`src/newsstore/enrich/milestone.py`)

```python
"""Phase 2 델타 — delta_time 배정(순수·결정론). LLM·store 의존 없음.

delta_time = 그 전개가 우리 스토어에 새 정보로 처음 편입된 시각. milestone 게이트:
새 전개(is_new=True)는 자기 발행시각(time), recap(is_new!=True이고 프런티어 존재)은
프런티어(max prior delta_time)에 귀속해 새 델타로 앞서지 않게 한다(analysis-design §6).
"""
from __future__ import annotations

MILESTONE_PRIOR_MAX = 12          # prior를 milestone 프롬프트에 먹이는 상한(토큰 통제)


def _frontier(prior_developments: list[dict]):
    """prior delta_time 중 max(없거나 모두 None이면 None — 비교 불가=첫 요약/legacy)."""
    times = [p.get("delta_time") for p in (prior_developments or [])
             if p.get("delta_time") is not None]
    return max(times) if times else None


def assign_delta_times(developments: list[dict], *, prior_developments: list[dict]) -> list[dict]:
    """각 development에 delta_time을 배정한 새 리스트 반환. is_new는 내부 신호라 제거.

    is_new is True 또는 프런티어 None → delta_time=time(새 전개/첫요약/legacy).
    그 외(recap이고 프런티어 존재) → delta_time=프런티어(새 델타 비생성, 보수적).
    """
    frontier = _frontier(prior_developments)
    out = []
    for d in developments:
        is_new = d.get("is_new") is True            # 정확히 True만 새 전개(누락/null/비bool=recap)
        dt = d["time"] if (is_new or frontier is None) else frontier
        out.append({"text": d["text"], "time": d["time"],
                    "source_count": d["source_count"], "delta_time": dt})
    return out


def prior_texts(prior_developments: list[dict]) -> list[str]:
    """milestone 프롬프트용 prior 텍스트(time desc 최신순, MILESTONE_PRIOR_MAX 상한)."""
    ordered = sorted((p for p in (prior_developments or []) if p.get("time") is not None),
                     key=lambda p: p["time"], reverse=True)
    return [p["text"] for p in ordered[:MILESTONE_PRIOR_MAX]]
```

- [ ] **Step 4: 통과 확인** — 같은 명령. Expected: PASS(9 tests).

- [ ] **Step 5: 커밋** — `git add src/newsstore/enrich/milestone.py tests/test_milestone.py && git commit -m "feat(phase2): delta_time 배정 순수 로직(milestone.py) + 단위테스트"`

---

## Task 2: summarizer 배선(prompt·validator·summarize_story·run_pass)

**Files:** Modify `src/newsstore/enrich/summarizer.py`, Test `tests/test_summarizer.py`

- [ ] **Step 1: 실패 테스트 추가** (`tests/test_summarizer.py`) — import는 **상단 import 블록**에, 테스트 함수는 파일 끝에 추가

```python
# (상단 import 블록에 추가)
from newsstore.enrich.milestone import MILESTONE_PRIOR_MAX  # noqa

# (파일 끝에 추가)
def _prior(text, h):
    return {"text": text, "time": T0 + timedelta(hours=h),
            "source_count": 1, "delta_time": T0 + timedelta(hours=h)}


def test_prompt_includes_prior_and_is_new_when_prior_given():
    p = build_summary_prompt(_members(3), prior_developments=[_prior("known", 0)])
    assert "known" in p and "is_new" in p


def test_prompt_unchanged_without_prior():
    assert "is_new" not in build_summary_prompt(_members(3))        # 하위호환


def test_validate_passes_is_new_true():
    raw = {"title": "T", "summary": "S",
           "developments": [{"text": "d", "first_idx": 0, "source_count": 1, "is_new": True}]}
    v = validate_summary(raw, n_members=3)
    assert v["developments"][0]["is_new"] is True


def test_validate_non_true_is_new_normalized_false():
    raw = {"title": "T", "summary": "S",
           "developments": [{"text": "d", "first_idx": 0, "source_count": 1, "is_new": "x"}]}
    v = validate_summary(raw, n_members=3)
    assert v["developments"][0]["is_new"] is False


def test_summarize_adds_delta_time_recap_to_frontier():
    m = _members(6)
    resp = {"title": "T", "summary": "S",
            "developments": [{"text": "recap", "first_idx": 5, "source_count": 1, "is_new": False}]}
    prior = [_prior("p1", 0), _prior("p2", 2)]
    res = summarize_story(m, FakeLLM(resp), now=T0, prior_developments=prior)
    assert res["developments"][0]["delta_time"] == T0 + timedelta(hours=2)   # 프런티어
    assert "is_new" not in res["developments"][0]                            # 저장 안 함


def test_summarize_no_prior_delta_time_is_time():
    m = _members(3)
    resp = {"title": "T", "summary": "S",
            "developments": [{"text": "a", "first_idx": 2, "source_count": 1}]}
    res = summarize_story(m, FakeLLM(resp), now=T0)
    assert res["developments"][0]["delta_time"] == m[2]["published_at"]


def test_run_pass_passes_prior_developments():
    resp = {"title": "T", "summary": "S",
            "developments": [{"text": "recap", "first_idx": 0, "source_count": 1, "is_new": False}]}
    prior = [_prior("p1", 0), _prior("p2", 2)]
    store = FakeStore([{"id": "s1", "count": 5, "developments": prior}], {"s1": _members(5)})
    run_summary_pass(store, FakeLLM(resp), limit=10, now=T0)
    assert store.saved["s1"]["developments"][0]["delta_time"] == T0 + timedelta(hours=2)
```

Also update `FakeStore.get_stories_needing_summary` is unaffected (returns stories as-is). The prior is carried in the story dict; `run_summary_pass` must read `st.get("developments")`.

- [ ] **Step 2: 실패 확인** — `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest -q tests/test_summarizer.py`. Expected: FAIL (build_summary_prompt got unexpected kw prior_developments, etc.).

- [ ] **Step 3: 구현** (`summarizer.py`)

3a. import 추가(상단): `from .milestone import assign_delta_times, prior_texts`

3b. `build_summary_prompt` 시그니처/본문:
```python
def build_summary_prompt(members: list[dict], *, omitted: int = 0,
                         prior_developments: list[dict] | None = None) -> str:
    elen = _excerpt_len(len(members))
    lines = []
    if omitted > 0:
        lines.append(f"(참고: 아래는 최신 {len(members)}건이며 그 이전 {omitted}건은 생략됨. "
                     "first_idx는 아래 번호 기준.)")
    for i, m in enumerate(members):
        title = (m.get("title") or "").strip()
        body = (m.get("body") or "").strip()[:elen]
        source = m.get("source") or "?"
        lines.append(f"{i}. [{source}] {title} :: {body}")
    ptexts = prior_texts(prior_developments) if prior_developments else []
    milestone_rule = ""
    known_block = ""
    if ptexts:                          # prior 있을 때만(없으면 기존 프롬프트와 동일=하위호환)
        known_block = ("\n이미 알려진 전개(기존 델타):\n"
                       + "\n".join(f"- {t}" for t in ptexts) + "\n")
        milestone_rule = ("각 전개에 is_new(이 전개가 위 '이미 알려진 전개'의 단순 재탕/배경이 "
                          "아니라 진짜 새 전개면 true, 재탕이면 false)도 넣어라. ")
    return (
        "당신은 한국어 금융 뉴스 스토리를 추적하는 에디터다. 아래는 한 스토리(같은 사건 클러스터)에 "
        "속한 기사들을 시간순(오래된→최신)으로 번호를 매긴 목록이다. 전체 흐름을 전개(development) "
        "단위로 묶어 요약하라. 의미상 같은 전개의 다른 표현(출처가 달라도)은 하나의 전개로 합쳐라. "
        "최근 전개에 가중치를 둬라. 사실만 쓰고 출처 밖 내용·추측은 금지한다.\n"
        "각 전개에 first_idx(그 전개를 처음 보도한 기사 번호)와 source_count(그 전개를 다룬 서로 "
        "다른 출처 수 추정)를 넣어라. " + milestone_rule + "아래 JSON만 출력:\n"
        '{"title":"스토리 캐노니컬 제목(≤40자)","summary":"2~3문장 요약(최근 가중)",'
        '"developments":[{"text":"전개 한 줄","first_idx":0,"source_count":1' +
        (',"is_new":true' if ptexts else '') + '}]}\n'
        + known_block + "\n"
        + "\n".join(lines)
    )
```

3c. `validate_summary` — out.append에 is_new 포함:
```python
        sc = d.get("source_count")
        sc = sc if _is_int(sc) and sc >= 1 else 1
        out.append({"text": text.strip(), "first_idx": idx,
                    "source_count": min(sc, n_members),
                    "is_new": d.get("is_new") is True})    # 정확히 True만, 그 외 보수적 False
```

3d. `summarize_story` 시그니처 + delta_time 배정:
```python
def summarize_story(members_all: list[dict], client: LLMClient, *, now=None,
                    prior_developments: list[dict] | None = None,
                    max_members: int = SUMMARY_MAX_MEMBERS) -> dict | None:
    if not members_all:
        return None
    members_fed = members_all[-max_members:]
    n = len(members_fed)
    omitted = len(members_all) - n
    raw = client.generate_json(
        build_summary_prompt(members_fed, omitted=omitted,
                             prior_developments=prior_developments), timeout=30.0)
    v = validate_summary(raw, n_members=n)
    if v is None:
        return None
    devs = []
    for d in v["developments"]:
        pub = members_fed[d["first_idx"]].get("published_at")
        if pub is None:                                # 시각 grounding 불가 → 드롭
            continue
        devs.append({"text": d["text"], "time": pub,
                     "source_count": d["source_count"], "is_new": d["is_new"]})
    devs = assign_delta_times(devs, prior_developments=prior_developments or [])
    devs.sort(key=lambda x: x["time"], reverse=True)   # 안정정렬, time DESC(위=최신)
    latest = devs[0]["text"] if devs else ""
    return {"title": v["title"], "summary": v["summary"], "latest": latest,
            "developments": devs, "summary_count": len(members_all)}
```

3e. `run_summary_pass` — prior 전달:
```python
            res = summarize_story(members, client, now=now,
                                  prior_developments=st.get("developments"),
                                  max_members=max_members)
```
(`st`는 `for st in store.get_stories_needing_summary(limit)` 루프변수 — 이미 존재.)

- [ ] **Step 4: 통과 확인** — `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest -q tests/test_summarizer.py`. Expected: PASS(기존 + 신규). 기존 `test_summarize_fills_time_sorts_desc_latest` 등도 green(delta_time 추가 키는 무해).

- [ ] **Step 5: 커밋** — `git add src/newsstore/enrich/summarizer.py tests/test_summarizer.py && git commit -m "feat(phase2): 요약 콜에 milestone(is_new) 편승 + delta_time 배정"`

---

## Task 3: store prior 반환 + 계약/문서

**Files:** Modify `src/newsstore/store/firestore_store.py`, `src/newsstore/contracts/ports.py`, `tests/test_store_summary.py`, `docs/firestore-contract.md`

- [ ] **Step 1: 실패 테스트 추가** (`tests/test_store_summary.py` 끝에)

```python
def test_needing_summary_returns_prior_developments(store):
    _mk_story(store, "a", count=5, summary_count=2, last_seen=NOW)
    devs = [{"text": "p1", "time": NOW, "source_count": 1, "delta_time": NOW}]
    store.save_story_summary("a", title="T", summary="S", latest="p1",
                             developments=devs, summary_count=2, now=NOW)
    got = {s["id"]: s for s in store.get_stories_needing_summary(limit=10)}
    assert got["a"]["developments"][0]["text"] == "p1"          # prior 동봉
    assert got["a"]["developments"][0]["delta_time"] == NOW


def test_save_story_summary_persists_delta_time(store):
    _mk_story(store, "s", count=2, last_seen=NOW)
    store.save_story_summary("s", title="T", summary="S", latest="L",
                             developments=[{"text": "d", "time": NOW,
                                            "source_count": 1, "delta_time": NOW}],
                             summary_count=2, now=NOW)
    d = store.db.collection("stories").document("s").get().to_dict()
    assert d["developments"][0]["delta_time"] == NOW
    assert d["count"] == 2                                       # cluster field 보존
```

- [ ] **Step 2: 실패 확인** — `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest -q tests/test_store_summary.py`. Expected: FAIL (KeyError 'developments' in get result).

- [ ] **Step 3: 구현** — `firestore_store.py` `get_stories_needing_summary` 결과에 developments 추가:
```python
            if d.get("count", 0) > d.get("summary_count", 0):
                out.append({"id": snap.id, "count": d.get("count", 0),
                            "developments": d.get("developments", [])})
```
(`save_story_summary`는 이미 developments 리스트를 그대로 저장 → delta_time 키 포함돼도 무변경.)

- [ ] **Step 4: 통과 확인** — 같은 명령. Expected: PASS.

- [ ] **Step 5: ports.py docstring 갱신** (`get_stories_needing_summary`):
```python
    def get_stories_needing_summary(self, limit: int) -> list[dict]:
        """last_seen desc 상위 limit개 중 count>summary_count(새 멤버)인 것만.
        [{'id','count','developments'(prior, delta_time 포함 가능)}]."""
        ...
```

- [ ] **Step 6: firestore-contract.md 갱신** — `stories` 섹션의 "향후 ... delta_time(Phase 2)"를 현재형으로:
  - `lenses[]` 항목 뒤에 추가:
    `- **`developments[].delta_time`** (Phase 2) — 전개가 새 정보로 편입된 시각. milestone 게이트가 recap을 프런티어로 귀속(새 델타 비생성). 없으면 소비자가 `time`으로 폴백(비파괴). 요약 패스(`run_enrich --mode summary`)가 write.`
  - 기존 "향후 `risk·impact`(Phase 3 score), `delta_time`(Phase 2)." 줄에서 `delta_time`(Phase 2) 제거(현재화).

- [ ] **Step 7: 전체 테스트 + 커밋**

```bash
MSYS_NO_PATHCONV=1 docker compose run --rm test
# Expected: FAIL=0 (전 스위트)
git add src/newsstore/store/firestore_store.py src/newsstore/contracts/ports.py \
        tests/test_store_summary.py docs/firestore-contract.md
git commit -m "feat(phase2): store가 prior developments 반환 + delta_time 계약 현재화"
```

---

## 검증(최종, 증거 후 주장)
- `MSYS_NO_PATHCONV=1 docker compose run --rm test` → FAIL=0 로그 확인.
- 배포 금지(Phase 2 범위). 🔴 §7 사용자 결정(프런티어 근사 vs 정밀 매핑, 편승 vs 별도콜)은 리턴에 보고.

## Self-Review 결과
- **Spec 커버리지**: §2.1 delta_time 기본값=Task1/2; §2.2 milestone is_new=Task1/2; §2.3 fail-soft(no-prior→time, 콜실패→skip)=Task1 tests + 기존 None 가드; §3.1 summarizer=Task2; §3.2 milestone.py=Task1; §3.3 store=Task3; §6 비파괴=Task3 보존 테스트. 누락 없음.
- **Placeholder 스캔**: 없음(모든 코드 명시).
- **타입 일관성**: `assign_delta_times(developments, *, prior_developments)`·`prior_texts`·`MILESTONE_PRIOR_MAX`·development dict 키(`text/time/source_count/delta_time/is_new`)가 Task 전반 일치.

---
_plan-review(2026-06-29, 3렌즈 독립 서브에이전트): grounding=클린(코드 주장 전부 검증). consistency/adversarial=critical 무(지적은 cosmetic/fragility, no-action). 반영: 타깃 테스트 명령 `docker compose run --rm test pytest -q tests/...`로 정정(compose는 인자를 command 오버라이드 → `pytest` 명시 필요), test_summarizer import는 상단 블록 명시. `st.get("developments")`는 None-safe라 Task2가 Task3 전에도 우아하게 강등(broken window 없음)._

<!-- spec-review: passed lenses=3 date=2026-06-29 -->
