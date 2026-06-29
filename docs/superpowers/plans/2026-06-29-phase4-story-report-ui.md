# Phase 4 — 스토리 리포트 리더 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 스토리를 "기사 더미"가 아니라 합성 보고서(헤드라인·리드·bullet 아티클 + 발생/보도 2-타임스탬프 타임라인 + 전일대비)로 보여주는 백엔드 생성 패스 + UI 재설계.

**Architecture:** summary 패스가 같은 LLM 콜로 `developments[].event_time`(발생시각)을 추가 채워 developments **단일 writer** 유지(비파괴). 새 `--mode article` 패스가 score 다음에 돌며 `headline`/`lead`/`article`(bullet) + 전일대비 ref를 **자기 필드만** merge(developments 안 건드림 = save_story_score와 동일 안전성). UI는 `stories`를 클라가 직접 read해 가로 셀렉터 + 보고서로 렌더, 정렬·delta·NEW는 순수함수로 라이브 도출.

**Tech Stack:** Python 3.11(Docker), Firestore(에뮬레이터 테스트), Gemini flash-lite(`generate_json`), vanilla JS(web/index.html, node 순수함수 테스트). 전 테스트: `MSYS_NO_PATHCONV=1 docker compose run --rm test`. UI 로직: `node tests/web/stories_logic.test.mjs`.

**상위 문서**: spec `docs/superpowers/specs/2026-06-29-phase4-story-report-ui-design.md` · 목업 `docs/superpowers/specs/assets/phase4-report-mockup.html` · 계약 `docs/firestore-contract.md`. **핵심 gotcha(주입)**: ① 비파괴 — 패스는 자기 필드만 `set(merge=True)`, developments는 summary 단독 writer ② fail-soft 스토리 단위(예외 traceback 로그) ③ 매직넘버 금지(모듈 상수) ④ Docker 전용(로컬 Python 없음) ⑤ store 추상화(`store.db` 직접접근 금지, `get_all` 배치) ⑥ Firestore Timestamp는 `.toDate()` 가드, `published_at` None 가드.

> ✅ **구현·머지 완료(2026-06-29)** — Group A~D 전부 main에 커밋. 전체 스위트 **207 passed, 1 skipped** + UI 로직 **17 passed**(docker node). **남은 건 배포(Cloud Run + Hosting)와 캘리브레이션** — 핸드오프 `docs/HANDOFF-phase4.md` 참조. 체크박스는 히스토리로 미체크 보존.

---

## Group A — summary 패스 `event_time` 확장 (developments 단일 writer)

### Task A1: build_summary_prompt가 event_time을 요청

**Files:**
- Modify: `src/newsstore/enrich/summarizer.py`
- Test: `tests/test_summarizer.py`

- [ ] **Step 1: 실패 테스트 추가** (`tests/test_summarizer.py` 끝에)

```python
# --- Phase 4: event_time 추출 ---
def test_prompt_requests_event_time():
    p = build_summary_prompt(_members(3))
    assert "event_time" in p          # 발생시각을 항상 요청(prior 유무 무관)
```

- [ ] **Step 2: 실패 확인** — Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test tests/test_summarizer.py::test_prompt_requests_event_time -v` · Expected: FAIL (event_time 없음)

- [ ] **Step 3: 프롬프트에 event_time 추가** — `summarizer.py`의 `build_summary_prompt` 반환 JSON 스키마에 `event_time`을 넣고 설명 문장 추가. 현재:

```python
        '{"title":"스토리 캐노니컬 제목(≤40자)","summary":"2~3문장 요약(최근 가중)",'
        '"developments":[{"text":"전개 한 줄","first_idx":0,"source_count":1'
        + (',"is_new":true' if ptexts else '') + '}]}\n'
```

로 교체:

```python
        "각 전개에 event_time(그 전개의 사건이 실제로 일어난 시각, 본문에서 추론한 "
        "ISO8601 예 2026-06-29T09:30:00Z. 불명확하면 null)도 넣어라.\n"
        '{"title":"스토리 캐노니컬 제목(≤40자)","summary":"2~3문장 요약(최근 가중)",'
        '"developments":[{"text":"전개 한 줄","first_idx":0,"source_count":1,'
        '"event_time":null'
        + (',"is_new":true' if ptexts else '') + '}]}\n'
```

- [ ] **Step 4: 통과 확인** — Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test tests/test_summarizer.py -v` · Expected: PASS (전체 summarizer 테스트 green — 기존 회귀 없음)

- [ ] **Step 5: 커밋**

```bash
git add src/newsstore/enrich/summarizer.py tests/test_summarizer.py
git commit -m "feat(summary): event_time 추출 요청 프롬프트 (Phase 4)"
```

### Task A2: event_time 파싱 + sanity + developments 보존

**Files:**
- Modify: `src/newsstore/enrich/summarizer.py` (상수·헬퍼·validate_summary·summarize_story)
- Modify: `src/newsstore/enrich/milestone.py` (assign_delta_times가 event_time 보존)
- Test: `tests/test_summarizer.py`

- [ ] **Step 1: 실패 테스트 추가**

```python
def test_summarize_parses_event_time_in_range():
    m = _members(3)                                   # m[i].published_at = T0 + i시간
    ev = (T0 + timedelta(hours=2)).isoformat().replace("+00:00", "Z")
    resp = {"title": "T", "summary": "S", "developments": [
        {"text": "a", "first_idx": 2, "source_count": 1, "event_time": ev}]}
    res = summarize_story(m, FakeLLM(resp), now=T0)
    assert res["developments"][0]["event_time"] == T0 + timedelta(hours=2)

def test_summarize_event_time_null_or_out_of_range_is_none():
    m = _members(3)
    for bad in [None, "not-a-date", "1990-01-01T00:00:00Z"]:    # null·비ISO·sanity 밖
        resp = {"title": "T", "summary": "S", "developments": [
            {"text": "a", "first_idx": 0, "source_count": 1, "event_time": bad}]}
        res = summarize_story(m, FakeLLM(resp), now=T0)
        assert res["developments"][0]["event_time"] is None
```

- [ ] **Step 2: 실패 확인** — Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test tests/test_summarizer.py::test_summarize_parses_event_time_in_range -v` · Expected: FAIL (KeyError event_time)

- [ ] **Step 3: 구현** — `summarizer.py` 상단에 상수·헬퍼 추가(`from datetime import datetime, timezone` import 추가):

```python
from datetime import datetime, timezone

EVENT_SANITY_DAYS = 14          # event_time이 보도시각에서 이만큼 벗어나면 환각으로 보고 드롭

def _parse_event_time(raw, ref):
    """ISO8601 문자열을 ref(보도시각) ±EVENT_SANITY_DAYS 안이면 datetime, 아니면 None."""
    if not isinstance(raw, str):
        return None
    try:
        dt = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    if ref is not None and abs((dt - ref).days) > EVENT_SANITY_DAYS:
        return None
    return dt
```

`validate_summary`의 out.append에 `event_time` 원문 통과 추가(형식만 — 파싱은 summarize_story):

```python
        out.append({"text": text.strip(), "first_idx": idx,
                    "source_count": min(sc, n_members),
                    "event_time": d.get("event_time"),         # 원문(str|null), 파싱은 summarize_story
                    "is_new": d.get("is_new") is True})
```

`summarize_story`의 devs 빌드 루프에서 event_time 파싱:

```python
    for d in v["developments"]:
        pub = members_fed[d["first_idx"]].get("published_at")
        if pub is None:                                # 시각 grounding 불가 → 드롭
            continue
        devs.append({"text": d["text"], "time": pub,
                     "source_count": d["source_count"], "is_new": d["is_new"],
                     "event_time": _parse_event_time(d.get("event_time"), pub)})
```

- [ ] **Step 4: milestone이 event_time 보존** — `milestone.py`의 `assign_delta_times` out.append에 event_time 추가:

```python
        out.append({"text": d["text"], "time": d["time"],
                    "source_count": d["source_count"], "delta_time": dt,
                    "event_time": d.get("event_time")})
```

- [ ] **Step 5: 통과 확인** — Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test tests/test_summarizer.py tests/test_milestone.py -v` · Expected: PASS (전부 green, 기존 회귀 없음)

- [ ] **Step 6: 커밋**

```bash
git add src/newsstore/enrich/summarizer.py src/newsstore/enrich/milestone.py tests/test_summarizer.py
git commit -m "feat(summary): event_time 파싱·sanity + milestone 보존 (Phase 4)"
```

---

## Group B — `--mode article` 생성 패스 (자기 필드만 merge)

### Task B1: enrich/article.py — 상수 + validate_article

**Files:**
- Create: `src/newsstore/enrich/article.py`
- Test: `tests/test_article.py` (새 파일)

- [ ] **Step 1: 실패 테스트**

```python
# tests/test_article.py
from newsstore.enrich.article import (validate_article, MAX_BULLETS,
                                      MAX_HEADLINE, MAX_LEAD, MAX_BULLET_LEN)

def test_validate_good():
    v = validate_article({"headline": "마이크론 블로아웃", "lead": "어닝 서프라이즈.",
                          "article": ["FQ3 EPS 상회", "BofA 목표 상향"]})
    assert v["headline"] == "마이크론 블로아웃" and v["article"] == ["FQ3 EPS 상회", "BofA 목표 상향"]

def test_validate_missing_keys_none():
    assert validate_article({"lead": "x", "article": ["a"]}) is None       # headline 결측
    assert validate_article({"headline": "h", "article": ["a"]}) is None   # lead 결측
    assert validate_article({"headline": "h", "lead": "l"}) is None        # article 결측
    assert validate_article({"headline": "h", "lead": "l", "article": "x"}) is None  # 비-list
    assert validate_article({"headline": "", "lead": "l", "article": ["a"]}) is None # 빈 headline
    assert validate_article(None) is None

def test_validate_caps_bullets_and_lengths():
    v = validate_article({"headline": "H" * 999, "lead": "L" * 999,
                          "article": ["b" * 999] + ["x"] * 50})
    assert len(v["headline"]) <= MAX_HEADLINE and len(v["lead"]) <= MAX_LEAD
    assert len(v["article"]) <= MAX_BULLETS and all(len(b) <= MAX_BULLET_LEN for b in v["article"])

def test_validate_drops_non_str_bullets():
    v = validate_article({"headline": "h", "lead": "l", "article": ["ok", 5, "", "  ", "ok2"]})
    assert v["article"] == ["ok", "ok2"]
```

- [ ] **Step 2: 실패 확인** — Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test tests/test_article.py -v` · Expected: FAIL (모듈 없음)

- [ ] **Step 3: 구현** (`src/newsstore/enrich/article.py`)

```python
"""스토리 아티클 생성 패스(Phase 4) — headline/lead/article(bullet) + 전일대비 ref를
비파괴로 저장한다. **developments는 절대 안 건드림**(summary 단독 writer) — 자기 필드만 merge.

설계: docs/superpowers/specs/2026-06-29-phase4-story-report-ui-design.md
순서: cluster → summary(+event_time) → score(risk/impact) → article(마지막).
"""
from __future__ import annotations
import logging
from datetime import timedelta

from .gemini import LLMError

log = logging.getLogger("newsstore.enrich.article")

MAX_BULLETS = 6                 # article bullet 상한
MAX_HEADLINE = 100              # 헤드라인 길이 상한
MAX_LEAD = 300                  # 리드 길이 상한
MAX_BULLET_LEN = 240            # bullet 1개 길이 상한
ARTICLE_MAX_MEMBERS = 40        # LLM에 먹이는 멤버 발췌 상한(토큰)
REF_WINDOW = timedelta(hours=24)   # 전일대비 ref 롤링 창
IMPACT_PRIOR = 1                # 미채점 스토리 정렬 prior(UI와 공유 의미 — UI는 자체 상수)


def _nonempty_str(x):
    return isinstance(x, str) and x.strip()


def validate_article(raw: dict | None) -> dict | None:
    """결정론 검증. 필수키 headline/lead/article(비어있지 않은 str·list[str]). 길이·개수 상한.
    실패 → None(스토리 스킵)."""
    raw = raw or {}
    headline, lead, article = raw.get("headline"), raw.get("lead"), raw.get("article")
    if not _nonempty_str(headline) or not _nonempty_str(lead):
        return None
    if not isinstance(article, list):
        return None
    bullets = [b.strip()[:MAX_BULLET_LEN] for b in article if _nonempty_str(b)][:MAX_BULLETS]
    if not bullets:
        return None
    return {"headline": headline.strip()[:MAX_HEADLINE],
            "lead": lead.strip()[:MAX_LEAD], "article": bullets}
```

- [ ] **Step 4: 통과 확인** — Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test tests/test_article.py -v` · Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add src/newsstore/enrich/article.py tests/test_article.py
git commit -m "feat(article): validate_article + 상수 (Phase 4)"
```

### Task B2: article.py — ref 스냅샷 + 입력 구성 + prompt + article_story

**Files:**
- Modify: `src/newsstore/enrich/article.py`
- Test: `tests/test_article.py`

- [ ] **Step 1: 실패 테스트 추가**

```python
from datetime import datetime, timezone, timedelta
from newsstore.enrich.article import compute_ref, article_story, build_article_input, REF_WINDOW
NOW = datetime(2026, 6, 29, 12, tzinfo=timezone.utc)

def test_compute_ref_snapshots_when_missing():
    assert compute_ref(now=NOW, risk=2, impact=3, risk_ref=None, impact_ref=None,
                       score_ref_at=None) == (2, 3, NOW)

def test_compute_ref_holds_when_fresh():
    fresh = NOW - timedelta(hours=1)
    assert compute_ref(now=NOW, risk=2, impact=3, risk_ref=1, impact_ref=1,
                       score_ref_at=fresh) == (1, 1, fresh)

def test_compute_ref_advances_when_stale():
    stale = NOW - REF_WINDOW - timedelta(hours=1)
    assert compute_ref(now=NOW, risk=2, impact=3, risk_ref=1, impact_ref=1,
                       score_ref_at=stale) == (2, 3, NOW)

def test_compute_ref_skips_when_unscored():
    assert compute_ref(now=NOW, risk=None, impact=None, risk_ref=None, impact_ref=None,
                       score_ref_at=None) == (None, None, None)

def test_build_input_prefers_summary_then_members():
    assert "tanker" in build_article_input({"summary": "tanker strike", "developments": []}, None)
    out = build_article_input({"summary": "", "developments": []}, [{"title": "Fed hikes"}])
    assert "Fed hikes" in out
    assert build_article_input({"summary": "", "developments": []}, []) == ""

class _FakeLLM:
    def __init__(self, resp): self.resp, self.seen = resp, None
    def generate_json(self, prompt, *, timeout=30.0):
        self.seen = prompt; return self.resp

def test_article_story_ok_and_sets_ref():
    llm = _FakeLLM({"headline": "H", "lead": "L", "article": ["b1", "b2"]})
    out = article_story({"title": "t", "summary": "s", "developments": [], "risk": 2,
                         "impact": 3, "risk_ref": None, "impact_ref": None, "score_ref_at": None},
                        members=None, client=llm, now=NOW)
    assert out["headline"] == "H" and out["article"] == ["b1", "b2"]
    assert out["risk_ref"] == 2 and out["impact_ref"] == 3 and out["score_ref_at"] == NOW

def test_article_story_empty_input_none():
    llm = _FakeLLM({"headline": "H", "lead": "L", "article": ["b"]})
    assert article_story({"title": "", "summary": "", "developments": []},
                         members=[], client=llm, now=NOW) is None

def test_article_story_failsoft_llm_error():
    class _Boom:
        def generate_json(self, prompt, *, timeout=30.0): raise RuntimeError("down")
    assert article_story({"title": "x", "summary": "s", "developments": []},
                         members=None, client=_Boom(), now=NOW) is None

def test_article_story_drops_invalid_output():
    llm = _FakeLLM({"headline": "", "lead": "L", "article": ["b"]})   # 빈 headline → validator None
    assert article_story({"title": "x", "summary": "s", "developments": []},
                         members=None, client=llm, now=NOW) is None
```

- [ ] **Step 2: 실패 확인** — Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test tests/test_article.py -v` · Expected: FAIL (compute_ref 등 없음)

- [ ] **Step 3: 구현 추가** (`article.py`에 append)

```python
def compute_ref(*, now, risk, impact, risk_ref, impact_ref, score_ref_at):
    """전일대비 기준 스냅샷(24h 롤링). 미채점(risk/impact None)이면 갱신 안 함.
    score_ref_at 없거나 REF_WINDOW 지났으면 현재 점수를 ref로 전진, 아니면 유지."""
    if risk is None or impact is None:
        return risk_ref, impact_ref, score_ref_at
    if score_ref_at is None or (now - score_ref_at) >= REF_WINDOW:
        return risk, impact, now
    return risk_ref, impact_ref, score_ref_at


def build_article_input(story: dict, members: list | None) -> str:
    """생성 입력. summary·developments(text, 신선도 순) 1차 → 없으면 멤버 제목 폴백. 둘 다 비면 ''."""
    parts: list[str] = []
    if story.get("summary"):
        parts.append(str(story["summary"]))
    for d in (story.get("developments") or []):
        if isinstance(d, dict) and d.get("text"):
            parts.append(str(d["text"]))
    if not parts and members:
        for m in members[:ARTICLE_MAX_MEMBERS]:
            if m.get("title"):
                parts.append(str(m["title"]))
    return "\n".join(parts)


def build_article_prompt(title: str, impact, body: str) -> str:
    """헤드라인(가장 최신 전개 주도)+리드(1~2문장)+bullet 아티클. impact는 텍스트 입력 아님(톤 참고만)."""
    return (
        "당신은 한국어 금융 뉴스 스토리를 합성하는 에디터다. 아래 스토리(같은 사건 클러스터)의 "
        "요약·전개를 읽고 투자자용 보고서를 만들어라.\n"
        "- headline: 가장 최신 전개를 전면에 둔 한 줄 제목(≤80자). 단정적이되 출처 밖 추측 금지.\n"
        "- lead: 핵심과 '왜 중요한가'를 1~2문장으로.\n"
        "- article: 핵심 근거를 bullet 리스트로(최대 6개, 각 한 줄). 본문에서 합리적으로 추론한 "
        "맥락을 채우되 사실에 근거. 마지막 bullet은 '변수/리스크'를 다뤄도 좋다.\n"
        "아래 JSON만 출력:\n"
        '{"headline":"...","lead":"...","article":["...", "..."]}\n\n'
        f"제목: {title}\n내용:\n{body[:3000]}"
    )


def article_story(story: dict, members: list | None, client, *, now,
                  timeout: float = 30.0) -> dict | None:
    """한 스토리 생성. 입력 비면 None. LLM 장애·무효 출력 → None(fail-soft). ref 스냅샷 포함."""
    body = build_article_input(story, members)
    if not body.strip():
        return None
    try:
        raw = client.generate_json(
            build_article_prompt(story.get("title", ""), story.get("impact"), body),
            timeout=timeout)
    except Exception:                       # LLM 장애 → fail-soft
        return None
    v = validate_article(raw)
    if v is None:
        return None
    rr, ir, ra = compute_ref(now=now, risk=story.get("risk"), impact=story.get("impact"),
                             risk_ref=story.get("risk_ref"), impact_ref=story.get("impact_ref"),
                             score_ref_at=story.get("score_ref_at"))
    return {**v, "risk_ref": rr, "impact_ref": ir, "score_ref_at": ra}
```

- [ ] **Step 4: 통과 확인** — Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test tests/test_article.py -v` · Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add src/newsstore/enrich/article.py tests/test_article.py
git commit -m "feat(article): compute_ref + 입력/프롬프트 + article_story fail-soft (Phase 4)"
```

### Task B3: store 메서드 + ports Protocol

**Files:**
- Modify: `src/newsstore/store/firestore_store.py` (get_stories_for_article, save_story_article)
- Modify: `src/newsstore/contracts/ports.py` (Store Protocol)
- Test: `tests/test_firestore_store.py`

- [ ] **Step 1: 실패 테스트 추가** (`tests/test_firestore_store.py` 끝에 — 기존 파일 import/픽스처 사용)

```python
from datetime import datetime, timezone, timedelta as _td
_NOW4 = datetime(2026, 6, 29, 12, tzinfo=timezone.utc)

def test_article_roundtrip_and_nondestructive(store):
    store.create_story("a1", title="t", vec=[1.0], member_id="m1", entities=[], now=_NOW4)
    store.save_story_lenses("a1", ["kr_rates"], count=1)
    store.save_story_summary("a1", title="t", summary="sum", latest="l",
                             developments=[{"text": "d", "time": _NOW4, "source_count": 1,
                                            "event_time": _NOW4}], summary_count=1, now=_NOW4)
    store.save_story_article("a1", headline="H", lead="L", article=["b1", "b2"],
                             risk_ref=2, impact_ref=3, score_ref_at=_NOW4, count=1, now=_NOW4)
    rows = store.get_stories_for_article(cutoff=_NOW4 - _td(hours=1))
    # count(1) <= articled_count(1) → incremental 스킵(반환 안 됨)
    assert all(r["id"] != "a1" for r in rows)
    doc = store.db.collection("stories").document("a1").get().to_dict()
    assert doc["headline"] == "H" and doc["article"] == ["b1", "b2"] and doc["articled_count"] == 1
    assert doc["lenses"] == ["kr_rates"] and doc["summary"] == "sum"           # 비파괴 보존
    assert doc["developments"][0]["event_time"] is not None                    # developments 보존

def test_get_for_article_returns_score_and_ref_fields(store):
    store.create_story("a2", title="t", vec=[1.0], member_id="m2", entities=[], now=_NOW4)
    store.save_story_score("a2", risk=2, impact=1, risk_reason="", impact_reason="",
                           count=1, now=_NOW4)
    store.append_to_story("a2", vec=[1.0], member_id="m3", entities=[], now=_NOW4)  # count=2 > articled(0)
    rows = {r["id"]: r for r in store.get_stories_for_article(cutoff=_NOW4 - _td(hours=1))}
    assert rows["a2"]["risk"] == 2 and rows["a2"]["impact"] == 1
    assert "risk_ref" in rows["a2"] and "score_ref_at" in rows["a2"] and "first_seen" in rows["a2"]
```

- [ ] **Step 2: 실패 확인** — Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test tests/test_firestore_store.py -k article -v` · Expected: FAIL (메서드 없음)

- [ ] **Step 3: store 구현** — `firestore_store.py`의 Phase 3 블록 아래에 추가(get_stories_for_scoring를 미러):

```python
    # --- Phase 4 article(보고서 생성) 패스 ---
    def get_stories_for_article(self, cutoff) -> list[dict]:
        # incremental: count>articled_count 또는 미생성. get_stories_for_scoring 미러 +
        # 생성/헤드라인/ref 갱신에 필요한 필드(developments·risk·impact·*_ref·first_seen).
        out = []
        for snap in self.db.collection("stories").where("status", "==", "open").stream():
            d = snap.to_dict() or {}
            if not (d.get("last_seen") and d["last_seen"] >= cutoff):
                continue
            count = d.get("count", len(d.get("member_ids", [])))
            if count <= d.get("articled_count", -1):
                continue
            out.append({"id": snap.id, "title": d.get("title", ""), "count": count,
                        "lenses": d.get("lenses", []), "summary": d.get("summary", ""),
                        "developments": d.get("developments", []),
                        "risk": d.get("risk"), "impact": d.get("impact"),
                        "risk_ref": d.get("risk_ref"), "impact_ref": d.get("impact_ref"),
                        "score_ref_at": d.get("score_ref_at"), "first_seen": d.get("first_seen")})
        return out

    def save_story_article(self, story_id, *, headline, lead, article,
                           risk_ref=None, impact_ref=None, score_ref_at=None,
                           count=None, now=None) -> None:
        # merge=True + 자기 필드만(read 없음, cross-field batch 없음, developments 미포함)
        # → summary/lenses/score/cluster/developments 보존(비파괴 by construction).
        doc = {"headline": headline, "lead": lead, "article": list(article)}
        if risk_ref is not None:
            doc["risk_ref"] = int(risk_ref)
        if impact_ref is not None:
            doc["impact_ref"] = int(impact_ref)
        if score_ref_at is not None:
            doc["score_ref_at"] = score_ref_at
        if count is not None:
            doc["articled_count"] = int(count)
        if now is not None:
            doc["articled_at"] = now
        self.db.collection("stories").document(story_id).set(doc, merge=True)
```

- [ ] **Step 4: ports Protocol** — `src/newsstore/contracts/ports.py`의 `Store` Protocol에 Phase 3 메서드 옆에 시그니처 추가:

```python
    def get_stories_for_article(self, cutoff) -> list[dict]: ...
    def save_story_article(self, story_id, *, headline, lead, article,
                           risk_ref=None, impact_ref=None, score_ref_at=None,
                           count=None, now=None) -> None: ...
```

- [ ] **Step 5: 통과 확인** — Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test tests/test_firestore_store.py -v` · Expected: PASS

- [ ] **Step 6: 커밋**

```bash
git add src/newsstore/store/firestore_store.py src/newsstore/contracts/ports.py tests/test_firestore_store.py
git commit -m "feat(store): get_stories_for_article + save_story_article 비파괴 (Phase 4)"
```

### Task B4: run_article_pass + run_enrich --mode article

**Files:**
- Modify: `src/newsstore/enrich/article.py` (run_article_pass)
- Modify: `src/newsstore/entrypoints/run_enrich.py` (--mode article)
- Test: `tests/test_article_pass.py` (새 파일, 에뮬레이터)

- [ ] **Step 1: 실패 테스트** (`tests/test_article_pass.py` — test_score_pass.py 패턴 미러)

```python
from datetime import datetime, timezone, timedelta
from newsstore.enrich.article import run_article_pass

NOW = datetime(2026, 6, 29, 12, tzinfo=timezone.utc)
CUT = NOW - timedelta(hours=1)

class _LLM:
    def generate_json(self, prompt, *, timeout=30.0):
        return {"headline": "H", "lead": "L", "article": ["b1", "b2"]}

def _doc(store, sid):
    return store.db.collection("stories").document(sid).get().to_dict() or {}

def test_generates_and_saves(store):
    store.create_story("s1", title="t", vec=[1.0], member_id="a", entities=[], now=NOW)
    store.save_story_summary("s1", title="t", summary="sum", latest="l",
                             developments=[{"text": "d", "time": NOW, "source_count": 1}],
                             summary_count=1, now=NOW)
    n = run_article_pass(store, _LLM(), now=NOW, cutoff=CUT)
    assert n["articled"] == 1 and _doc(store, "s1")["headline"] == "H"

def test_incremental_skips_then_regenerates(store):
    store.create_story("s2", title="t", vec=[1.0], member_id="a", entities=[], now=NOW)
    store.save_story_summary("s2", title="t", summary="sum", latest="l",
                             developments=[{"text": "d", "time": NOW, "source_count": 1}],
                             summary_count=1, now=NOW)
    assert run_article_pass(store, _LLM(), now=NOW, cutoff=CUT)["articled"] == 1
    assert run_article_pass(store, _LLM(), now=NOW, cutoff=CUT)["articled"] == 0   # 변화 없음 스킵
    store.append_to_story("s2", vec=[1.0], member_id="b", entities=[], now=NOW)
    assert run_article_pass(store, _LLM(), now=NOW, cutoff=CUT)["articled"] == 1   # 새 멤버 재생성

def test_nondestructive_keeps_developments_when_summary_added_later(store):
    # 비파괴 핵심: article 저장이 summary가 만든 developments를 되돌리지 않는다.
    store.create_story("s3", title="t", vec=[1.0], member_id="a", entities=[], now=NOW)
    store.save_story_summary("s3", title="t", summary="sum", latest="l",
                             developments=[{"text": "D1", "time": NOW, "source_count": 1}],
                             summary_count=1, now=NOW)
    store.append_to_story("s3", vec=[1.0], member_id="b", entities=[], now=NOW)
    run_article_pass(store, _LLM(), now=NOW, cutoff=CUT)
    # 이후 summary가 새 전개 추가 → article은 이미 저장됨. developments는 summary 소유라 살아있음.
    store.save_story_summary("s3", title="t", summary="sum2", latest="l",
                             developments=[{"text": "D1", "time": NOW, "source_count": 1},
                                           {"text": "D2", "time": NOW, "source_count": 1}],
                             summary_count=2, now=NOW)
    d = _doc(store, "s3")
    assert d["headline"] == "H" and len(d["developments"]) == 2   # 둘 다 생존

class _Boom:
    def generate_json(self, prompt, *, timeout=30.0): raise RuntimeError("down")

def test_failsoft(store):
    store.create_story("s4", title="t", vec=[1.0], member_id="a", entities=[], now=NOW)
    store.save_story_summary("s4", title="t", summary="s", latest="l",
                             developments=[{"text": "d", "time": NOW, "source_count": 1}],
                             summary_count=1, now=NOW)
    n = run_article_pass(store, _Boom(), now=NOW, cutoff=CUT)
    assert n["skipped"] == 1 and n["articled"] == 0 and "headline" not in _doc(store, "s4")
```

- [ ] **Step 2: 실패 확인** — Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test tests/test_article_pass.py -v` · Expected: FAIL (run_article_pass 없음)

- [ ] **Step 3: run_article_pass 구현** (`article.py`에 append — run_score_pass 미러)

```python
def run_article_pass(store, client, *, now, cutoff) -> dict:
    """열린 스토리(incremental: count>articled_count)에 보고서 생성·저장. fail-soft(스토리 단위)."""
    totals = {"articled": 0, "skipped": 0}
    for st in store.get_stories_for_article(cutoff=cutoff):
        sid = st["id"]
        try:
            members = None
            if not (st.get("summary") or st.get("developments")):
                members = store.get_story_members(sid)   # 요약 없을 때만 멤버 폴백
            res = article_story(st, members, client, now=now)
            if res is None:
                totals["skipped"] += 1
                continue
            store.save_story_article(sid, headline=res["headline"], lead=res["lead"],
                                     article=res["article"], risk_ref=res["risk_ref"],
                                     impact_ref=res["impact_ref"], score_ref_at=res["score_ref_at"],
                                     count=st.get("count"), now=now)
            totals["articled"] += 1
        except LLMError as e:
            log.warning("article skip story %s (LLM): %s", sid, e)
            totals["skipped"] += 1
        except Exception:                # fail-soft: 한 스토리 버그가 전체를 안 죽임(traceback 로그)
            log.exception("article unexpected error story %s", sid)
            totals["skipped"] += 1
    log.info("article pass: %s", totals)
    return totals
```

- [ ] **Step 4: run_enrich 배선** — `run_enrich.py`의 `--mode` choices에 `"article"` 추가하고 분기 추가(score 분기 아래):

```python
    ap.add_argument("--mode", choices=["cluster", "tag", "summary", "lenses", "score", "article"],
```

```python
            elif args.mode == "article":
                from ..enrich.article import run_article_pass
                now = datetime.now(timezone.utc)
                totals = run_article_pass(store, client, now=now, cutoff=now - OPEN_WINDOW)
```

- [ ] **Step 5: 통과 확인** — Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test tests/test_article_pass.py -v` · Expected: PASS

- [ ] **Step 6: 전체 회귀** — Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test` · Expected: FAIL=0 (전 스위트 green)

- [ ] **Step 7: 커밋**

```bash
git add src/newsstore/enrich/article.py src/newsstore/entrypoints/run_enrich.py tests/test_article_pass.py
git commit -m "feat(article): run_article_pass + --mode article 배선 (Phase 4)"
```

---

## Group C — UI 재설계 (web/index.html)

### Task C1: 순수함수 (storyRank/deltaBadge/isNew/nodeTimes) + node 테스트

**Files:**
- Modify: `web/index.html` (STORIES-LOGIC 마커 블록 안)
- Test: `tests/web/stories_logic.test.mjs`

- [ ] **Step 1: 실패 테스트 추가** (`stories_logic.test.mjs`의 destructure에 함수 추가 + 테스트). 14번째 줄 destructure를 교체:

```javascript
const { toMs, groupItemsByDevelopment, pickDisplayItems,
        storyRank, deltaBadge, isNew, nodeTimes, IMPACT_PRIOR } =
  new Function(block + "\nreturn { toMs, groupItemsByDevelopment, pickDisplayItems, storyRank, deltaBadge, isNew, nodeTimes, IMPACT_PRIOR };")();
```

그리고 `console.log` 위에 테스트 추가:

```javascript
const NOW = Date.UTC(2026, 5, 29, 12, 0, 0);
// --- storyRank ---
test("impact 높을수록·신선할수록 rank↑, 미채점은 IMPACT_PRIOR(0 아님)", () => {
  const hi = storyRank({ impact: 3, last_seen: new Date(NOW) }, NOW);
  const lo = storyRank({ impact: 1, last_seen: new Date(NOW) }, NOW);
  const un = storyRank({ impact: null, last_seen: new Date(NOW) }, NOW);  // 미채점
  assert.ok(hi > lo, "impact 3 > 1");
  assert.ok(un > 0, "미채점도 0 아님(매몰 방지)");
  assert.ok(un >= storyRank({ impact: IMPACT_PRIOR, last_seen: new Date(NOW) }, NOW) - 1e-9);
});
test("같은 impact면 더 신선한 쪽 rank↑", () => {
  const fresh = storyRank({ impact: 2, last_seen: new Date(NOW) }, NOW);
  const old = storyRank({ impact: 2, last_seen: new Date(NOW - 48 * 3600000) }, NOW);
  assert.ok(fresh > old);
});
// --- deltaBadge ---
test("delta: ref 있으면 ▲▼, 없으면 null, 0이면 null", () => {
  assert.deepEqual(deltaBadge(3, 2), { dir: "up", n: 1 });
  assert.deepEqual(deltaBadge(1, 2), { dir: "down", n: 1 });
  assert.equal(deltaBadge(2, 2), null);
  assert.equal(deltaBadge(3, null), null);     // ref 없음 → 화살표 생략
  assert.equal(deltaBadge(null, 2), null);
});
// --- isNew ---
test("isNew: first_seen이 REF_WINDOW 이내", () => {
  assert.equal(isNew(new Date(NOW - 3600000), NOW), true);    // 1h 전 → NEW
  assert.equal(isNew(new Date(NOW - 48 * 3600000), NOW), false);
  assert.equal(isNew(null, NOW), false);
});
// --- nodeTimes ---
test("nodeTimes: event_time 있으면 그것, 없으면 time(보도)로 폴백", () => {
  const ev = new Date(NOW - 7200000), rep = new Date(NOW);
  const a = nodeTimes({ time: rep, event_time: ev });
  assert.equal(a.event, ev.getTime()); assert.equal(a.report, rep.getTime());
  assert.equal(a.eventIsActual, true);
  const b = nodeTimes({ time: rep, event_time: null });
  assert.equal(b.event, rep.getTime()); assert.equal(b.eventIsActual, false);
});
```

- [ ] **Step 2: 실패 확인** — Run: `node tests/web/stories_logic.test.mjs` · Expected: FAIL (storyRank 등 undefined)

- [ ] **Step 3: 순수함수 구현** — `web/index.html`의 `// === STORIES-LOGIC-END` 직전(pickDisplayItems 아래)에 추가:

```javascript
    // --- Phase 4: 정렬·delta·신선 순수함수 (라이브 도출, LLM 0콜) ---
    const IMPACT_PRIOR = 1;                 // 미채점 스토리 정렬 prior(0 매몰 방지)
    const FRESH_TAU_H = 12;                 // 신선도 감쇠 시정수(시간)
    const REF_WINDOW_MS = 24 * 3600 * 1000; // 전일대비/NEW 창
    function latestDeltaMs(s) {
      let best = null;
      for (const d of (s.developments || [])) {
        const m = toMs(d && (d.delta_time || d.time));
        if (m != null && (best == null || m > best)) best = m;
      }
      return best != null ? best : toMs(s.last_seen);
    }
    function storyRank(s, now) {
      const impact = (s.impact == null ? IMPACT_PRIOR : Number(s.impact));
      const ms = latestDeltaMs(s);
      const ageH = (now != null && ms != null) ? Math.max(0, (now - ms) / 3600000) : 1e9;
      return impact * (1 / (1 + ageH / FRESH_TAU_H));     // impact × 신선도
    }
    function deltaBadge(cur, ref) {
      if (cur == null || ref == null) return null;        // ref 없으면 화살표 생략(best-effort)
      const d = Number(cur) - Number(ref);
      if (!d) return null;
      return { dir: d > 0 ? "up" : "down", n: Math.abs(d) };
    }
    function isNew(firstSeen, now) {
      const ms = toMs(firstSeen);
      return ms != null && (now - ms) < REF_WINDOW_MS;
    }
    function nodeTimes(dev) {
      const report = toMs(dev && dev.time);
      const ev = toMs(dev && dev.event_time);
      return { event: ev != null ? ev : report, report, eventIsActual: ev != null };
    }
```

- [ ] **Step 4: 통과 확인** — Run: `node tests/web/stories_logic.test.mjs` · Expected: PASS (전 테스트 green, 기존 회귀 없음)

- [ ] **Step 5: 커밋**

```bash
git add web/index.html tests/web/stories_logic.test.mjs
git commit -m "feat(ui): storyRank/deltaBadge/isNew/nodeTimes 순수함수 + 테스트 (Phase 4)"
```

### Task C2: 셀렉터·보고서 렌더 + Warm Light 팔레트

**Files:**
- Modify: `web/index.html` (CSS `:root`/스토리 스타일, `storyCardHtml`, `renderDetail`, `loadStories` 정렬, 번역/원문·정렬 토글 핸들러)

> **시각 기준 = 목업** `docs/superpowers/specs/assets/phase4-report-mockup.html`. 아래는 *실제 데이터 필드*에 맞춘 렌더 코드. 기존 `groupItemsByDevelopment`/`pickDisplayItems`/`articleCardHtml`/라우팅은 보존, 호출부만 확장. 이 태스크는 DOM 렌더라 node 테스트 대상이 아님 → **수동 검증**: 로컬에서 `web/index.html`을 Firestore 실데이터로 열어(또는 config.js 가리키는 프로젝트) 셀렉터·보고서·토글·delta 배지를 눈으로 확인(spec §9·목업과 일치).

- [ ] **Step 1: Warm Light 팔레트** — `:root` 토큰을 목업 값으로 교체(기존 `--bg:#f1f0ec` 등 줄):

```css
    :root {
      --bg:#fdfcf8; --card:#fffefc; --line:#ece6da; --fg:#2f2a23;
      --sub:#4a4236; --mut:#9c9385; --accent:#c0764a; --pill:#f0ebe0; --pill-fg:#6e6558;
      --imp:#bf8f3c; --risk:#c0606d; --green:#4f9e80; --off:#ddd6c9;
    }
```

- [ ] **Step 2: 셀렉터 카드 렌더** — `storyCardHtml(s)`를 교체(헤드라인 폴백 title, impact/risk 점 + delta 배지/NEW). 헬퍼 `dotsHtml`·`badgeHtml` 추가:

```javascript
    function metersHtml(s) {
      const dot = (on, cls) => `<span class="dot ${cls}${on ? " on" : ""}"></span>`;
      const row = (label, val, ref, cls) => {
        if (val == null) return "";
        const dots = [0,1,2].map(i => dot(i < Number(val), cls)).join("");
        const db = deltaBadge(val, ref);
        const badge = db ? `<span class="delta ${db.dir}">${db.dir==="up"?"▲":"▼"}${db.n}</span>` : "";
        return `<span class="mtr"><b style="color:var(--${cls==="imp"?"imp":"risk"})">${label}</b>${dots}${badge}</span>`;
      };
      return row("impact", s.impact, s.impact_ref, "imp") + row("risk", s.risk, s.risk_ref, "risk");
    }
    function storyCardHtml(s) {
      const c = srcColors(s.id);
      const head = txt(s.headline || s.title) || "(제목 없음)";
      const last = s.last_seen && s.last_seen.toDate ? s.last_seen.toDate() : null;
      const newb = isNew(s.first_seen, Date.now()) ? `<span class="newb">NEW</span>` : "";
      return `<div class="scard" data-id="${esc(s.id)}" style="--bar:${c.bar}">
        <div class="st">${head}</div>
        <div class="sfoot"><span class="scnt">${Number(s.count) || 0}건</span>
          ${metersHtml(s)}${newb}<span class="stm">${relTime(last)}</span></div></div>`;
    }
```

CSS 추가(스토리 스트립 스타일 근처):

```css
    .scard .sfoot { flex-wrap:wrap; gap:6px; }
    .mtr { display:inline-flex; align-items:center; gap:2px; font-size:10px; color:var(--mut); }
    .dot { width:7px; height:7px; border-radius:50%; background:var(--off); display:inline-block; margin-left:1px; }
    .dot.imp.on { background:var(--imp); } .dot.risk.on { background:var(--risk); }
    .delta { font-size:10px; font-weight:800; margin-left:3px; }
    .delta.up { color:var(--risk); } .delta.down { color:var(--mut); }
    .newb { font-size:9px; font-weight:800; color:#fff; background:var(--accent); padding:1px 5px; border-radius:5px; }
```

- [ ] **Step 3: 정렬을 storyRank로** — `loadStories`의 정렬을 교체(현재 `orderBy("last_seen","desc")` 쿼리는 유지하되 클라에서 storyRank로 재정렬):

```javascript
        const now = Date.now();
        const stories = all.filter(s => (Number(s.count) || 0) >= 2)
          .sort((a, b) => storyRank(b, now) - storyRank(a, now)).slice(0, 20);
```

- [ ] **Step 4: 보고서 렌더** — `renderDetail(s, items)`를 확장: 헤드라인·리드·article bullet·번역/원문 토글·2-타임스탬프 타임라인. 기존 `groupItemsByDevelopment`/`pickDisplayItems`/`articleCardHtml` 재사용. 타임라인 노드에 `nodeTimes` 사용:

```javascript
    let detailMode = "translated";        // translated | original (번역/원문 토글 상태)
    let detailSort = "report";            // report | event (보도순/발생순)
    function bulletsHtml(article) {
      if (!Array.isArray(article) || !article.length) return "";
      return `<ul class="abul">${article.map(b => `<li>${txt(b)}</li>`).join("")}</ul>`;
    }
    function fmtTime(ms) { return ms == null ? "" : new Date(ms).toLocaleString("ko-KR",
      { month:"2-digit", day:"2-digit", hour:"2-digit", minute:"2-digit" }); }
    function renderDetail(s, items) {
      let groups = groupItemsByDevelopment(s.developments || [], items);
      // 발생순 토글: nodeTimes.event 기준 재정렬(보도순은 기존 time DESC 유지)
      if (detailSort === "event")
        groups = [...groups].sort((a, b) =>
          (b.dev ? nodeTimes(b.dev).event : 0) - (a.dev ? nodeTimes(a.dev).event : 0));
      detailGroups = groups;
      const head = txt(s.headline || s.title) || "(제목 없음)";
      const lead = s.lead || s.summary;
      const meta = `${Number(s.count) || items.length}개 기사 · ${groups.filter(g=>g.dev).length}개 전개`;
      const toggle = `<div class="dtoggle">
        <button data-m="translated" class="${detailMode==='translated'?'on':''}">번역</button>
        <button data-m="original" class="${detailMode==='original'?'on':''}">원문</button></div>`;
      const sortT = `<span class="htoggle">
        <button data-s="report" class="${detailSort==='report'?'on':''}">보도순</button>
        <button data-s="event" class="${detailSort==='event'?'on':''}">발생순</button></span>`;
      const rows = groups.map((g, gi) => {
        const isDev = !!g.dev;
        const nt = isDev ? nodeTimes(g.dev) : null;
        const devText = isDev ? txt(g.dev.text) : "전체 기사";
        const times = isDev ? `<span class="tp ev">발생 <b>${fmtTime(nt.event)}</b>${nt.eventIsActual?"":" (보도기준)"}</span>
          <span class="tp">보도 <b>${fmtTime(nt.report)}</b></span>` : "";
        const { shown, moreCount } = pickDisplayItems(g.items, 2);
        const arts = (shown.map(articleCardHtml).join("") || `<div class="sempty">기사 없음</div>`) +
          (moreCount > 0 ? `<button class="amore" data-gi="${gi}">+${moreCount}개 더</button>` : "");
        return `<div class="dgroup"><div class="tcol"><div class="tnode ${gi===0?'last':''}">
          <span class="tdot"></span><div class="times">${times}</div>
          <div class="tdev">${devText}</div></div></div>
          <div class="darts" data-gi="${gi}">${arts}</div></div>`;
      }).join("");
      detailEl.innerHTML = `<div class="sdetail">
        <div class="dt">${head}</div>
        ${lead ? `<div class="dlead">${txt(lead)}</div>` : ""}
        ${bulletsHtml(s.article)}
        ${toggle}<div class="dmeta">${meta} ${sortT}</div>
        ${rows || '<div class="sempty">표시할 기사가 없습니다.</div>'}</div>`;
    }
```

CSS 추가:

```css
    .sdetail .dlead { font-size:14px; color:var(--fg); background:#f3ede2;
      border-left:3px solid var(--accent); padding:9px 12px; border-radius:0 8px 8px 0; margin:6px 0 12px; }
    .abul { list-style:none; padding:0; margin:0 0 14px; }
    .abul li { position:relative; padding:3px 0 3px 16px; color:var(--sub); }
    .abul li::before { content:""; position:absolute; left:2px; top:11px; width:5px; height:5px; border-radius:50%; background:var(--accent); }
    .dtoggle, .htoggle { display:inline-flex; gap:2px; background:var(--pill); border-radius:7px; padding:2px; }
    .dtoggle button, .htoggle button { border:0; background:transparent; color:var(--mut); font-weight:600;
      font-size:11px; padding:3px 11px; border-radius:5px; cursor:pointer; font-family:inherit; }
    .dtoggle button.on { background:var(--accent); color:#fff; } .htoggle button.on { background:var(--green); color:#fff; }
    .times { display:flex; flex-wrap:wrap; gap:4px 8px; }
    .tp { font-size:10px; color:var(--mut); } .tp b { color:var(--sub); } .tp.ev b { color:var(--green); }
```

- [ ] **Step 5: 토글 핸들러** — `detailEl.addEventListener("click", ...)`의 `.amore` 핸들러 옆에 번역/원문·정렬 토글 추가(같은 리스너 안):

```javascript
      const mt = e.target.closest(".dtoggle button");
      if (mt) { detailMode = mt.dataset.m;
        const s = storyById.get(openStoryId); if (s) renderDetail(s, memberCache.get(openStoryId) || []); return; }
      const st = e.target.closest(".htoggle button");
      if (st) { detailSort = st.dataset.s;
        const s = storyById.get(openStoryId); if (s) renderDetail(s, memberCache.get(openStoryId) || []); return; }
```

(원문/번역의 실제 멤버 원어 노출은 v1에서 `articleCardHtml`이 이미 원문 title/body를 보여주므로, `detailMode`는 향후 한국어 번역 필드 도입 시 확장점 — 현재는 토글 UI + 상태만. spec §8.)

- [ ] **Step 6: 수동 검증** — 로컬 브라우저로 `web/index.html` 열어 스토리 탭 확인: 셀렉터에 헤드라인·impact/risk 점·delta/NEW, 클릭 시 보고서(헤드라인·리드·bullet·발생/보도 타임라인·토글). 콘솔 에러 0. (실데이터 없으면 빈 목록 강등 확인.)

- [ ] **Step 7: node 로직 회귀** — Run: `node tests/web/stories_logic.test.mjs` · Expected: PASS (C1 함수 회귀)

- [ ] **Step 8: 커밋**

```bash
git add web/index.html
git commit -m "feat(ui): 가로 셀렉터 + 보고서(헤드라인/리드/bullet/2축타임라인/토글) + Warm Light (Phase 4)"
```

---

## Group D — 계약 문서 갱신

### Task D1: firestore-contract.md + analysis-design.md §8

**Files:**
- Modify: `docs/firestore-contract.md` (§stories)
- Modify: `docs/analysis-design.md` (§8 — 글로벌 Now Brief → per-story 리드로 정정)

- [ ] **Step 1: firestore-contract §stories에 추가** — `developments[].delta_time` 항목 아래에 추가:

```markdown
- **`developments[].event_time`** (datetime\|null, Phase 4) — 그 전개의 **사건 실제 시각**(요약 패스가 본문에서 추출, ISO·sanity 검증, 실패 시 null). UI는 null이면 `time`(보도시각)으로 폴백. `delta_time`과 같은 추가 타임스탬프(비파괴·레거시 안전).
- **`headline`·`lead`·`article[]`** (str·str·string[], Phase 4) — 생성 보고서. `article 패스`(`--mode article`)가 write, UI가 헤드라인/리드/bullet로 read. **article 패스는 `developments`를 안 쓴다(자기 필드만 merge — 비파괴 by construction).** 없으면 UI 폴백(`headline`→`title`, `lead`→`summary`, `article`→생략).
- **`risk_ref`·`impact_ref`** (int 0~3) · **`score_ref_at`** (datetime, Phase 4) — 전일대비 24h 롤링 기준. UI가 `risk−risk_ref`로 ▲▼ 도출(ref 없으면 화살표 생략, best-effort). `NEW`는 `first_seen`만으로 판정(ref 무관).
- **`articled_count`** (int) · **`articled_at`** (datetime, Phase 4) — incremental 가드(`summary_count`·`scored_count` 컨벤션).
```

- [ ] **Step 2: analysis-design §8 정정** — §8의 "상단 Now Brief(글로벌 합성)" 문단에 정정 노트 추가(삭제 아닌 mark — 비파괴 문서 원칙):

```markdown
> **Phase 4 확정 변경(2026-06-29, 사용자):** 글로벌 Now Brief는 **per-story 리드(`lead`)로 대체**(스토리=보고서 철학 — 셀렉터에서 스토리 선택 → 보고서). 좌/우 타임라인은 **발생/보도 2-타임스탬프 단일 타임라인 + 정렬 토글**로 단순화(지연막대 폐기). 스펙: `docs/superpowers/specs/2026-06-29-phase4-story-report-ui-design.md`.
```

- [ ] **Step 3: 전체 회귀 확인** — Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test` · Expected: FAIL=0. Run: `node tests/web/stories_logic.test.mjs` · Expected: PASS.

- [ ] **Step 4: 커밋 + main 머지**

```bash
git add docs/firestore-contract.md docs/analysis-design.md
git commit -m "docs: Phase 4 stories 필드(headline/lead/article/event_time/ref) 계약 + §8 정정"
# 작업 브랜치였다면: git checkout main && git merge --no-ff <branch>
git push origin main
```

---

## Self-Review (작성자 점검)

**1. Spec coverage:**
- spec §1 포함 ①(summary event_time)=Group A ✓ ②(article 패스)=Group B ✓ ③(store/ports)=B3 ✓ ④(UI 재설계)=Group C ✓ ⑤(계약 문서)=Group D ✓.
- §5 event_time(summary 단일 writer)=A1·A2 ✓ · §6 ref(best-effort, first_seen NEW)=B2·C1 ✓ · §7 storyRank(IMPACT_PRIOR)=C1 ✓ · §8 번역/원문(상태만, v1)=C2 Step5 ✓ · §9 UI 직접 read=C2 ✓.
- **비파괴 critical**: article이 `developments` 미저장 — B3 `save_story_article`에 developments 파라미터 없음 + B4 `test_nondestructive_keeps_developments_when_summary_added_later`로 강제 ✓.

**2. Placeholder scan:** 모든 코드 스텝에 실제 코드·정확한 명령·기대 출력 포함. "TODO/적절히/등" 없음 ✓.

**3. Type consistency:**
- `validate_article` 반환 키 `{headline, lead, article}` ↔ `article_story` `{**v, risk_ref, impact_ref, score_ref_at}` ↔ `save_story_article(headline, lead, article, risk_ref, impact_ref, score_ref_at, count, now)` ↔ store doc 키 일치 ✓.
- `compute_ref` 반환 튜플 `(risk_ref, impact_ref, score_ref_at)` ↔ article_story 언팩 ✓.
- `developments[].event_time`: summarizer 생성 → milestone 보존 → store 저장 → UI `nodeTimes(dev.event_time)` 일치 ✓.
- UI 상수 `IMPACT_PRIOR`(C1) ↔ 백엔드 `IMPACT_PRIOR`(B1) 의미 동일(별도 정의 — UI/py 분리는 불가피, 둘 다 1) ✓.
- store `get_stories_for_article` 반환 키 ↔ `article_story`가 읽는 `story.get(...)` 키(summary/developments/risk/impact/risk_ref/impact_ref/score_ref_at/title) 일치 ✓.

gaps: 없음. 실행 순서 = Group A → B → C → D(상단부터). 각 태스크 독립 커밋, 그린 게이트 후 진행.

<!-- spec-review: passed lenses=adversarial+self+TDD date=2026-06-29 (구현 완료·207 tests green) -->
