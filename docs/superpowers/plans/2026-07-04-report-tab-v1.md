# 리포트 탭 v1 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 스펙 `docs/superpowers/specs/2026-06-30-report-tab-design.md`(결정①~⑧)의 리포트 탭 v1 — 프레임 패스(이월+재심) + 스토리-그라운디드 섹션 리포트 + 급부상 + 단일 문서 UI.

**Architecture:** 전용 프레임 패스가 렌즈별 standing 프레임(risk/premium/watchpoints, 축당 ≤5)을 이월·재심하고, 리포트 패스가 그 프레임을 입력으로 받아 렌즈별 섹션 리포트를 생성(story_ids 인용 필수, 결정론 검증 → grounding+fit 리뷰 1콜), UI가 백드롭 서두+섹션들+급부상을 단일 문서로 결정론 조립한다. 저장은 `frames/{lens_id}`·`reports/{lens_id}`·`reports/_backdrop`(Firestore, public read).

**Tech Stack:** Python 3.12(사이드이펙트 없는 순수 로직 + Firestore 에뮬레이터 테스트, **Docker 전용** — `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest ...`), Gemini(google-genai, fake LLM으로 테스트), vanilla JS(web/index.html, node 마커 슬라이스 테스트).

**공통 규칙(모든 태스크):**
- 코드 원칙: SSOT·fail-loud·TDD·비파괴(merge)·비밀분리(GEMINI_API_KEY 로그/프롬프트 비노출). 로컬 Python 없음 — 테스트는 반드시 Docker.
- gotchas: 실 SDK/LLM은 None·`{"key": null}`을 준다 → `.get(k) or []`/`isinstance` 가드. `to_dict() or {}`. 테스트 기대 개수 매직넘버 금지(불변식으로).
- 각 태스크 마지막 스텝은 커밋. 커밋 메시지는 한국어 완결 문어체.

---

### Task 1: topics.yaml `report_group` + 도출 헬퍼

**Files:**
- Modify: `config/topics.yaml` (watch·sector 외 15개 렌즈에 `report_group` 추가)
- Modify: `src/newsstore/enrich/topics.py` (도출 함수 2개 추가)
- Test: `tests/test_topics.py`

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_topics.py`에 append:

```python
def test_report_lenses_derived_excludes_watch_and_sector():
    # 리포트 대상 = watch·sector 외 렌즈 전부(스펙 §3.5 — 손 목록 금지, 도출이 SSOT)
    t = topics.load_topics()
    ids = topics.report_lens_ids(t)
    assert "kr_equity" in ids and "fx" in ids and "risk" in ids
    assert not any(i.startswith("watch_") for i in ids)
    assert not any(i.startswith("sector_") for i in ids)
    # 불변식: 대상 렌즈는 전부 report_group을 가진다(fail-loud — 누락 시 여기서 터짐)
    for lens in t["lenses"]:
        if lens["id"] in ids:
            assert lens.get("report_group"), f"{lens['id']}: report_group 누락"


def test_report_groups_ordered_mapping():
    # 그룹 → 렌즈 목록(yaml 등장 순서 보존). UI 앵커 도출용.
    t = topics.load_topics()
    groups = topics.report_groups(t)
    assert groups["주식"] == ["kr_equity", "us_equity"]
    assert set(groups["원자재"]) == {"oil_energy", "precious_metals", "commodities"}
    flat = [lid for lids in groups.values() for lid in lids]
    assert sorted(flat) == sorted(topics.report_lens_ids(t))   # 전 대상 렌즈가 정확히 1그룹
```

- [ ] **Step 2: 실패 확인** — `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest -q tests/test_topics.py` → FAIL(`report_lens_ids` 없음)

- [ ] **Step 3: 구현** — `config/topics.yaml`의 15개 렌즈에 `report_group` 키 추가(인라인 dict에 `, report_group: 주식` 식):
  kr_equity·us_equity→`주식` / kr_rates·us_rates→`금리·채권` / kr_econ·us_econ→`경제` / kr_policy·us_policy→`정치·정책` / fx→`환율` / kr_realestate→`부동산` / oil_energy·precious_metals·commodities→`원자재` / crypto→`코인` / risk→`리스크`. watch_*·sector_*에는 추가하지 않는다.

  `src/newsstore/enrich/topics.py`에 append:

```python
def report_lens_ids(t: dict) -> list[str]:
    """리포트 대상 렌즈 id(등장 순서). watch(개별종목)·sector(층화용)는 제외 — 스펙 §3.5."""
    return [l["id"] for l in t["lenses"] if l["type"] not in ("watch", "sector")]


def report_groups(t: dict) -> dict[str, list[str]]:
    """report_group → [lens_id...] (yaml 등장 순서 보존). UI 섹션 앵커 도출(SSOT).
    대상 렌즈에 report_group이 없으면 KeyError로 fail-loud(조용한 드롭 금지)."""
    out: dict[str, list[str]] = {}
    for l in t["lenses"]:
        if l["type"] in ("watch", "sector"):
            continue
        out.setdefault(l["report_group"], []).append(l["id"])
    return out
```

- [ ] **Step 4: 통과 확인** — 같은 명령 → PASS (기존 test_asset_hint 등 포함 전부)
- [ ] **Step 5: 커밋** — `git add config/topics.yaml src/newsstore/enrich/topics.py tests/test_topics.py && git commit -m "feat(#20): topics.yaml report_group 속성 + 리포트 렌즈/그룹 도출(SSOT)"`

---

### Task 2: 계약 — ports.py TypedDict/Protocol + firestore-contract.md 등재

**Files:**
- Modify: `src/newsstore/contracts/ports.py`
- Modify: `docs/firestore-contract.md`
- Test: (컴파일/임포트는 Task 3 테스트가 겸함 — 이 태스크는 계약 선언)

- [ ] **Step 1: ports.py에 TypedDict·Store 메서드 추가** — `ArticleStory` 클래스 뒤에:

```python
class FramePole(TypedDict):
    """프레임 극 1개. id는 리포트 섹션이 pole_id로 인용(결정론 실재 검증용)."""
    id: str
    text: str


class Frame(TypedDict, total=False):
    """frames/{lens_id} — 프레임 패스 단독 writer(스펙 §3·§6). 3축, 축당 ≤FRAME_MAX_POLES."""
    risks: list[FramePole]
    premiums: list[FramePole]
    watchpoints: list[FramePole]
    updated_at: datetime
    model: str


class ReportStory(TypedDict, total=False):
    """get_stories_for_report 반환 — 리포트 입력 후보(open·72h·해당 렌즈)."""
    id: str
    title: str
    summary: str
    lenses: list[str]
    risk: int
    impact: int
    count: int
    developments: list[Development]
```

`Store` Protocol의 Phase 4 블록 뒤에:

```python
    # 리포트 탭(v1, 스펙 2026-06-30) — frames/reports 계약.
    def get_frame(self, lens_id: str) -> Frame:
        """frames/{lens_id}. 없으면 {}(첫 런)."""
        ...
    def save_frame(self, lens_id: str, frame: Frame, *, now: datetime) -> None:
        """frames/{lens_id} 통째 set(전량 재심 산출물) + 이전 판을
        frames_history/{lens_id}/snapshots/{ISO date}에 스냅샷(additive — 스펙 §6)."""
        ...
    def get_stories_for_report(self, lens_id: str, cutoff: datetime) -> list[ReportStory]:
        """status=open·last_seen>=cutoff·lenses∋lens_id. 전수 스캔+클라 필터(타 패스 패턴)."""
        ...
    def save_report(self, doc_id: str, report: dict) -> None:
        """reports/{doc_id} 통째 set(per-run 전량 재생성 — 스펙 §6). _backdrop·rising 포함."""
        ...
    def get_report(self, doc_id: str) -> dict:
        """reports/{doc_id}. 없으면 {}."""
        ...
```

- [ ] **Step 2: firestore-contract.md 등재** — 소유권 표에 행 2개 추가:

```markdown
| `frames` | report 패스(프레임 단계) | report 패스·web UI | standing 프레임(risk/premium/watchpoints, 축당≤5) — 이월·재심. history는 frames_history |
| `reports` | report 패스 | web UI | 섹션 리포트(`{lens_id}`)·백드롭(`_backdrop`)·급부상(`rising`). per-run 전량 재생성, public read |
```

컬렉션 스키마 절에 추가:

```markdown
### `frames` (report 패스 프레임 단계가 기록)
`frames/{lens_id}`: `{risks[{id,text}], premiums[{id,text}], watchpoints[{id,text}], updated_at, model}`.
갱신 시 이전 판을 `frames_history/{lens_id}/snapshots/{date}`에 보관(additive). 실패 런은 어제 판 유지(updated_at 미갱신 = 지연 신호).

### `reports` (report 패스가 기록, 공개 read)
`reports/{lens_id}`: `{topic, headline, lead, sections[{name, items[{text, story_ids[], pole_id}]}], frame_updated_at, generated_at, model, review{passed, notes}}`.
`reports/_backdrop`: `{text, generated_at, model, review{passed, notes}}`. `reports/rising`: 섹션 리포트와 같은 스키마(+`criteria` 문자열).
sections[].name ∈ {risk_triggered, premium_triggered, not_triggered, watchpoints}. per-run 통째 덮어쓰기(비-incremental — 스펙 §6).
```

- [ ] **Step 3: 커밋** — `git add src/newsstore/contracts/ports.py docs/firestore-contract.md && git commit -m "feat(#20): frames/reports 저장 계약(ports Protocol·TypedDict) + firestore-contract 등재"`

---

### Task 3: store — frames CRUD(+history) 에뮬레이터 테스트

**Files:**
- Modify: `src/newsstore/store/firestore_store.py`
- Test: `tests/test_store_frames.py` (신규)

- [ ] **Step 0: conftest 정리 목록 확장** — `tests/conftest.py`의 fsclient 컬렉션 초기화 목록에 `frames`·`reports`를 추가하고, `frames_history`는 하위컬렉션이라 명시 순회로 비운다(부모 doc 삭제로는 스냅샷이 안 지워짐 — 에뮬레이터 잔류 오염 방지):

```python
    # 기존 목록에 "frames", "reports" 추가 + frames_history 하위컬렉션 순회 삭제:
    for doc in client.collection("frames_history").list_documents():
        for snap in doc.collection("snapshots").list_documents():
            snap.delete()
        doc.delete()
```

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_store_frames.py`:

```python
"""frames/{lens_id} 계약(에뮬레이터) — 이월·스냅샷·빈 프레임."""
from datetime import datetime, timezone

NOW = datetime(2026, 7, 4, 7, 0, tzinfo=timezone.utc)
F1 = {"risks": [{"id": "r1", "text": "빅테크 capex 감속"}],
      "premiums": [{"id": "p1", "text": "HBM 수요 서프라이즈"}],
      "watchpoints": [{"id": "w1", "text": "메타 실적"}]}


def test_get_frame_empty_on_first_run(store):
    assert store.get_frame("kr_equity") == {}          # 첫 런: 없음 → {} (None 금지)


def test_save_and_get_frame_roundtrip(store):
    store.save_frame("kr_equity", dict(F1), now=NOW)
    got = store.get_frame("kr_equity")
    assert got["risks"][0]["id"] == "r1" and got["updated_at"] == NOW
    assert got["watchpoints"][0]["text"] == "메타 실적"


def test_save_frame_snapshots_previous_to_history(store):
    store.save_frame("fx", dict(F1), now=NOW)
    f2 = {"risks": [{"id": "r2", "text": "달러 초강세 재개"}], "premiums": [], "watchpoints": []}
    store.save_frame("fx", f2, now=NOW.replace(hour=8))
    snaps = list(store.db.collection("frames_history").document("fx")
                 .collection("snapshots").stream())
    assert len(snaps) == 1                             # 이전 판 1개 보관(첫 저장은 이전 판 없음)
    assert (snaps[0].to_dict() or {})["risks"][0]["id"] == "r1"
    assert store.get_frame("fx")["risks"][0]["id"] == "r2"   # 현행은 신판
```

- [ ] **Step 2: 실패 확인** — `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest -q tests/test_store_frames.py` → FAIL(`get_frame` 없음)

- [ ] **Step 3: 구현** — `firestore_store.py`의 Phase 4 블록 뒤에:

```python
    # --- 리포트 탭 v1: frames(프레임 패스 단독 writer — 스펙 §3·§6) ---
    def get_frame(self, lens_id: str) -> dict:
        snap = self.db.collection("frames").document(lens_id).get()
        return (snap.to_dict() or {}) if snap.exists else {}

    def save_frame(self, lens_id: str, frame: dict, *, now) -> None:
        ref = self.db.collection("frames").document(lens_id)
        prev = ref.get()
        if prev.exists:
            # 이전 판 스냅샷(additive) — 프레임 델타·사후 추적의 토대(스펙 §6)
            self.db.collection("frames_history").document(lens_id) \
                .collection("snapshots").document(now.strftime("%Y-%m-%dT%H%M%S")) \
                .set(prev.to_dict() or {})
        doc = dict(frame)
        doc["updated_at"] = now
        ref.set(doc)                     # 통째 set: 전량 재심 산출물(merge 아님)
```

- [ ] **Step 4: 통과 확인** — 같은 명령 → 3 passed
- [ ] **Step 5: 커밋** — `git add src/newsstore/store/firestore_store.py tests/test_store_frames.py && git commit -m "feat(#20): frames 저장(이월 조회·history 스냅샷) — 에뮬레이터 계약 테스트"`

---

### Task 4: store — reports CRUD + get_stories_for_report

**Files:**
- Modify: `src/newsstore/store/firestore_store.py`
- Test: `tests/test_store_reports.py` (신규)

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_store_reports.py`:

```python
"""reports/{doc_id} + get_stories_for_report 계약(에뮬레이터)."""
from datetime import datetime, timezone, timedelta

NOW = datetime(2026, 7, 4, 7, 0, tzinfo=timezone.utc)


def _mk_story(store, sid, *, lenses, last_seen, count=3, risk=1, impact=2):
    store.db.collection("stories").document(sid).set({
        "title": f"t-{sid}", "summary": f"s-{sid}", "lenses": lenses, "count": count,
        "risk": risk, "impact": impact, "member_ids": [], "entities": [],
        "developments": [], "first_seen": last_seen, "last_seen": last_seen, "status": "open"})


def test_report_roundtrip_and_overwrite(store):
    store.save_report("kr_equity", {"topic": "kr_equity", "headline": "h1", "review": {"passed": True}})
    store.save_report("kr_equity", {"topic": "kr_equity", "headline": "h2", "review": {"passed": False}})
    got = store.get_report("kr_equity")
    assert got["headline"] == "h2"                      # per-run 통째 덮어쓰기(스펙 §6)
    assert got["review"]["passed"] is False
    assert store.get_report("없는문서") == {}


def test_stories_for_report_filters_lens_window_status(store):
    cut = NOW - timedelta(hours=72)
    _mk_story(store, "in", lenses=["kr_equity", "sector_tech"], last_seen=NOW)
    _mk_story(store, "other-lens", lenses=["fx"], last_seen=NOW)
    _mk_story(store, "stale", lenses=["kr_equity"], last_seen=cut - timedelta(hours=1))
    store.db.collection("stories").document("closed").set(
        {"lenses": ["kr_equity"], "last_seen": NOW, "status": "closed"})
    got = store.get_stories_for_report("kr_equity", cutoff=cut)
    assert [s["id"] for s in got] == ["in"]
    assert got[0]["lenses"] == ["kr_equity", "sector_tech"]   # 층화 cap이 sector 라벨을 씀
    assert got[0]["impact"] == 2 and got[0]["summary"] == "s-in"
```

- [ ] **Step 2: 실패 확인** — FAIL(`save_report` 없음)

- [ ] **Step 3: 구현** — `firestore_store.py` frames 블록 뒤에:

```python
    # --- 리포트 탭 v1: reports(섹션·_backdrop·rising — per-run 전량 재생성) ---
    def save_report(self, doc_id: str, report: dict) -> None:
        self.db.collection("reports").document(doc_id).set(dict(report))

    def get_report(self, doc_id: str) -> dict:
        snap = self.db.collection("reports").document(doc_id).get()
        return (snap.to_dict() or {}) if snap.exists else {}

    def get_stories_for_report(self, lens_id: str, cutoff) -> list[dict]:
        # 전수 스캔(open)+클라 필터 — lensing/scoring/article과 동일 패턴(신규 인덱스 불요).
        out = []
        for snap in self.db.collection("stories").where("status", "==", "open").stream():
            d = snap.to_dict() or {}
            if not (d.get("last_seen") and d["last_seen"] >= cutoff):
                continue
            if lens_id not in (d.get("lenses") or []):
                continue
            out.append({"id": snap.id, "title": d.get("title", ""),
                        "summary": d.get("summary", ""), "lenses": d.get("lenses") or [],
                        "risk": d.get("risk"), "impact": d.get("impact"),
                        "count": d.get("count", 0),
                        "developments": d.get("developments") or []})
        return out
```

- [ ] **Step 4: 통과 확인** — 3 passed
- [ ] **Step 5: 커밋** — `git commit -m "feat(#20): reports 저장·조회 + 리포트 입력 스토리 쿼리(open·72h·렌즈)"`

---

### Task 5: frames.py — validate_frame + diff(재심 산출 검증)

**Files:**
- Create: `src/newsstore/enrich/frames.py`
- Test: `tests/test_frames.py` (신규)

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_frames.py`:

```python
"""프레임 패스 순수 로직 — validate·diff (fake LLM, 에뮬레이터 불요)."""
from newsstore.enrich.frames import validate_frame, frame_diff, FRAME_MAX_POLES

OLD = {"risks": [{"id": "r1", "text": "빅테크 capex 감속"}],
       "premiums": [{"id": "p1", "text": "HBM 수요"}], "watchpoints": []}


def test_validate_frame_schema_and_caps():
    raw = {"risks": [{"id": f"r{i}", "text": f"극{i}"} for i in range(FRAME_MAX_POLES + 2)],
           "premiums": [{"id": "p1", "text": "ok"}], "watchpoints": None}   # null 가드
    v = validate_frame(raw)
    assert len(v["risks"]) == FRAME_MAX_POLES            # 축당 상한 강제
    assert v["watchpoints"] == []                        # null → []
    assert all(p["id"] and p["text"] for p in v["risks"])


def test_validate_frame_rejects_garbage():
    assert validate_frame(None) is None
    assert validate_frame(["not", "dict"]) is None
    assert validate_frame({"risks": "문자열"}) is None    # 축이 리스트 아님 → 무효
    # 극에 id/text 없으면 그 극만 드롭(비파괴), 전부 빈 프레임도 유효(단극·무극 허용)
    v = validate_frame({"risks": [{"text": "id없음"}, {"id": "r1", "text": "ok"}],
                        "premiums": [], "watchpoints": []})
    assert [p["id"] for p in v["risks"]] == ["r1"]


def test_frame_diff_new_and_changed_only():
    new = {"risks": [{"id": "r1", "text": "빅테크 capex 감속(수정)"},   # 텍스트 변경
                     {"id": "r9", "text": "관세 재점화"}],              # 신규
           "premiums": [{"id": "p1", "text": "HBM 수요"}],             # 동일 유지
           "watchpoints": []}
    d = frame_diff(OLD, new)
    assert {p["id"] for p in d} == {"r1", "r9"}          # 유지 극(p1)은 diff 아님 → 리뷰 0대상
```

- [ ] **Step 2: 실패 확인** — FAIL(모듈 없음)

- [ ] **Step 3: 구현** — `src/newsstore/enrich/frames.py`:

```python
"""프레임 패스(리포트 탭 v1) — standing 프레임(risk/premium/watchpoints) 이월·재심.

스펙 docs/superpowers/specs/2026-06-30-report-tab-design.md §3: 전용 패스가 어제 프레임을
입력으로 전체 극을 재심(유지/수정/탈락 — 나이 기반 밀어내기 없음), diff(신규/수정)만
grounding 리뷰. 실패 시 어제 프레임 유지(이월 폴백)."""
from __future__ import annotations
import json
import logging

from .gemini import LLMError

log = logging.getLogger("newsstore.enrich.frames")

FRAME_MAX_POLES = 5           # 축당 극 상한(결정⑧ — 무상한이면 리포트 입력 폭탄)
FRAME_MAX_INPUT_STORIES = 30  # 프레임 패스 입력 캡(§3 — 프레임 패스가 새 토큰 폭탄 금지)
MAX_POLE_TEXT = 120
AXES = ("risks", "premiums", "watchpoints")


def validate_frame(raw) -> dict | None:
    """결정론 검증: 3축 스키마·축당 상한·극 id/text 필수(무효 극은 드롭). 실패 → None."""
    if not isinstance(raw, dict):
        return None
    out: dict = {}
    for axis in AXES:
        poles = raw.get(axis)
        if poles is None:
            out[axis] = []
            continue
        if not isinstance(poles, list):
            return None                       # 축 타입 위반은 프레임 전체 무효(fail-loud)
        keep = []
        for p in poles:
            if (isinstance(p, dict) and isinstance(p.get("id"), str) and p["id"].strip()
                    and isinstance(p.get("text"), str) and p["text"].strip()):
                keep.append({"id": p["id"].strip(), "text": p["text"].strip()[:MAX_POLE_TEXT]})
        out[axis] = keep[:FRAME_MAX_POLES]
    return out


def frame_diff(old: dict, new: dict) -> list[dict]:
    """신규·수정 극만(diff-grounding 리뷰 대상 — 유지 극은 과거 검증분). 스펙 §5 표."""
    prev = {p["id"]: p["text"] for axis in AXES for p in (old.get(axis) or [])}
    return [p for axis in AXES for p in (new.get(axis) or [])
            if p["id"] not in prev or prev[p["id"]] != p["text"]]
```

- [ ] **Step 4: 통과 확인** — 3 passed
- [ ] **Step 5: 커밋** — `git commit -m "feat(#20): 프레임 결정론 검증(3축·상한·무효 극 드롭)과 diff(신규/수정만)"`

---

### Task 6: frames.py — 프롬프트·diff 리뷰·run_frame_pass

**Files:**
- Modify: `src/newsstore/enrich/frames.py`
- Test: `tests/test_frames.py`

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_frames.py`에 append:

```python
from datetime import datetime, timezone
from newsstore.enrich.frames import (build_frame_prompt, build_frame_review_prompt,
                                     run_frame_pass)

NOW = datetime(2026, 7, 4, 7, 0, tzinfo=timezone.utc)
STORIES = [{"id": "s1", "title": "엔비디아 실적 서프라이즈", "summary": "HBM 수요 급증"}]


class _LLM:
    def __init__(self, frame_resp, review_resp=None):
        self.frame_resp, self.review_resp = frame_resp, review_resp
        self.calls = []
    def generate_json(self, prompt, *, timeout=30.0):
        self.calls.append(prompt)
        if isinstance(self.frame_resp, Exception):
            raise self.frame_resp
        return self.review_resp if "심사" in prompt else self.frame_resp
        # 리뷰 프롬프트는 '심사' 단어 포함(아래 구현) — fake 분기용


class _Store:
    def __init__(self, frames=None):
        self.frames = dict(frames or {})
        self.saved = {}
    def get_frame(self, lens_id):
        return self.frames.get(lens_id, {})
    def save_frame(self, lens_id, frame, *, now):
        self.saved[lens_id] = frame
    def get_stories_for_report(self, lens_id, cutoff):
        return list(STORIES)


def test_frame_prompt_carries_yesterday_and_caps_input():
    old = {"risks": [{"id": "r1", "text": "관세 리스크"}], "premiums": [], "watchpoints": []}
    p = build_frame_prompt("kr_equity", old, [{"id": f"s{i}", "title": f"t{i}", "summary": "x"}
                                              for i in range(100)])
    assert "관세 리스크" in p and '"r1"' in p            # 이월: 어제 극이 프롬프트에(재심 대상)
    assert "t99" not in p                               # FRAME_MAX_INPUT_STORIES 캡


def test_run_frame_pass_saves_reviewed_frame():
    llm = _LLM(frame_resp={"risks": [{"id": "r1", "text": "새 극"}], "premiums": [],
                           "watchpoints": []},
               review_resp={"passed": True, "notes": ""})
    store = _Store()
    n = run_frame_pass(store, llm, lens_ids=["kr_equity"], now=NOW)
    assert n == 1 and "kr_equity" in store.saved


def test_run_frame_pass_keeps_yesterday_on_review_reject_and_llm_error():
    old = {"risks": [{"id": "r1", "text": "기존"}], "premiums": [], "watchpoints": []}
    rejected = _LLM(frame_resp={"risks": [{"id": "r9", "text": "무근거"}], "premiums": [],
                                "watchpoints": []},
                    review_resp={"passed": False, "notes": "근거 없음"})
    store = _Store({"fx": old})
    run_frame_pass(store, rejected, lens_ids=["fx"], now=NOW)
    assert "fx" not in store.saved                      # 기각 → 어제 판 유지(저장 안 함)
    boom = _LLM(frame_resp=__import__("newsstore.enrich.gemini", fromlist=["LLMError"]).LLMError("down"))
    store2 = _Store({"fx": old})
    run_frame_pass(store2, boom, lens_ids=["fx"], now=NOW)
    assert "fx" not in store2.saved                     # 콜 실패 → 폴백(전파 금지, fail-soft)


def test_run_frame_pass_no_diff_skips_review():
    same = {"risks": [{"id": "r1", "text": "동일"}], "premiums": [], "watchpoints": []}
    llm = _LLM(frame_resp=same, review_resp={"passed": False})   # 리뷰가 불려도 False지만
    store = _Store({"fx": same})
    run_frame_pass(store, llm, lens_ids=["fx"], now=NOW)
    assert "fx" in store.saved                          # diff 없음 → 리뷰 0콜 → 저장(updated_at 갱신)
    assert sum("심사" in c for c in llm.calls) == 0
```

- [ ] **Step 2: 실패 확인** — FAIL(`build_frame_prompt` 없음)

- [ ] **Step 3: 구현** — `frames.py`에 append:

```python
def build_frame_prompt(lens_id: str, old: dict, stories: list[dict]) -> str:
    """이월 재심 프롬프트 — 어제 극 전부 + 최근 스토리(캡). 유지 판단에도 근거 명시 요구(§3 재심 계약)."""
    lines = [f'{i}. [{s["id"]}] {s.get("title", "")} :: {(s.get("summary") or "")[:150]}'
             for i, s in enumerate(stories[:FRAME_MAX_INPUT_STORIES])]
    return (
        f"당신은 '{lens_id}' 자산군의 standing 프레임을 유지하는 애널리스트다.\n"
        "프레임 3축: risks(아킬레스건/실질 리스크), premiums(기대/컨센서스), "
        "watchpoints(극을 트리거할 수 있는 예정된 관찰 지점 — 판단/조언 금지).\n"
        f"어제의 프레임(재심 대상):\n{json.dumps(old or {a: [] for a in AXES}, ensure_ascii=False)}\n"
        "최근 스토리:\n" + "\n".join(lines) + "\n"
        "임무: 어제 극을 하나씩 재심하라 — 여전히 유효하면 id 유지(근거 스토리가 최근에 없어도 "
        "구조적으로 유효하면 유지 가능하되 그 이유를 스스로 검토), 낡았으면 탈락, 새 위험/기대/"
        f"관찰 지점은 추가(신규 id). 축당 최대 {FRAME_MAX_POLES}개.\n"
        '아래 JSON만 출력: {"risks":[{"id":"...","text":"..."}],"premiums":[...],"watchpoints":[...]}')


def build_frame_review_prompt(diff: list[dict], stories: list[dict]) -> str:
    """diff-grounding 심사(§5 표) — 신규/수정 극이 스토리에 근거하는지."""
    lines = [f'[{s["id"]}] {s.get("title", "")} :: {(s.get("summary") or "")[:150]}'
             for s in stories[:FRAME_MAX_INPUT_STORIES]]
    return (
        "당신은 grounding 심사자다. 아래 신규/수정 프레임 극이 제공된 스토리에서 "
        "합리적으로 도출 가능한지 심사하라(구조적 상식 수준의 일반 명제는 허용, "
        "스토리와 무관한 구체 단정은 기각).\n"
        f"극:\n{json.dumps(diff, ensure_ascii=False)}\n스토리:\n" + "\n".join(lines) + "\n"
        '아래 JSON만 출력: {"passed": true|false, "notes": "기각 사유 또는 빈 문자열"}')


```python
def run_frame_pass(store, client, *, lens_ids: list[str], now, window=None) -> int:
    """렌즈별 프레임 재심. 실패(콜·검증·리뷰 기각)는 어제 판 유지(fail-soft, §5(c)). 반환=갱신 수."""
    from datetime import timedelta
    cutoff = now - (window or timedelta(hours=72))
    n = 0
    for lens_id in lens_ids:
        old = store.get_frame(lens_id)
        stories = store.get_stories_for_report(lens_id, cutoff=cutoff)
        try:
            raw = client.generate_json(build_frame_prompt(lens_id, old, stories), timeout=60.0)
        except LLMError as e:
            log.warning("frame pass %s: LLM 실패 — 어제 판 유지: %s", lens_id, e)
            continue
        frame = validate_frame(raw)
        if frame is None:
            log.warning("frame pass %s: 결정론 검증 실패 — 어제 판 유지", lens_id)
            continue
        diff = frame_diff(old, frame)
        if diff:
            try:
                verdict = client.generate_json(
                    build_frame_review_prompt(diff, stories), timeout=60.0)
            except LLMError as e:
                log.warning("frame pass %s: 리뷰 콜 실패 — 어제 판 유지: %s", lens_id, e)
                continue
            if not (isinstance(verdict, dict) and verdict.get("passed") is True):
                log.warning("frame pass %s: diff-grounding 기각(%s) — 어제 판 유지",
                            lens_id, (verdict or {}).get("notes"))
                continue
        store.save_frame(lens_id, frame, now=now)
        n += 1
    log.info("frame pass: %d/%d updated", n, len(lens_ids))
    return n
```

(프롬프트에 "심사" 단어가 리뷰 프롬프트에만 들어가는 것이 fake LLM 분기 계약 — build_frame_review_prompt 첫 문장에 '심사'가 있다.)

- [ ] **Step 4: 통과 확인** — `pytest -q tests/test_frames.py` → 전부 PASS
- [ ] **Step 5: 커밋** — `git commit -m "feat(#20): 프레임 패스 — 이월 재심 프롬프트·diff-grounding 리뷰·어제 판 폴백"`

---

### Task 7: report.py — top-K 선정(storyRank·층화 cap)·급부상 선정 (순수함수)

**Files:**
- Create: `src/newsstore/enrich/report.py`
- Test: `tests/test_report.py` (신규)

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_report.py`:

```python
"""리포트 패스 순수 로직 — top-K(storyRank·섹터 층화 cap)·급부상 선정."""
from datetime import datetime, timezone, timedelta
from newsstore.enrich.report import (story_rank, select_top_k, select_rising,
                                     REPORT_MAX_STORIES, SECTOR_STRATIFY_CAP,
                                     REPORT_MIN_STORIES)

NOW = datetime(2026, 7, 4, 7, 0, tzinfo=timezone.utc)


def _s(sid, *, impact=2, hours_ago=1, lenses=("kr_equity",), sector=None, ndev=1):
    devs = [{"text": f"d{i}", "time": NOW - timedelta(hours=hours_ago),
             "delta_time": NOW - timedelta(hours=hours_ago)} for i in range(ndev)]
    ls = list(lenses) + ([sector] if sector else [])
    return {"id": sid, "title": sid, "summary": "x", "impact": impact,
            "lenses": ls, "count": 3, "developments": devs}


def test_story_rank_mirrors_ui_impact_times_freshness():
    fresh = story_rank(_s("a", impact=2, hours_ago=0), NOW)
    old = story_rank(_s("b", impact=2, hours_ago=48), NOW)
    unscored = story_rank({"id": "c", "impact": None, "developments": [],
                           "last_seen": NOW}, NOW)
    assert fresh > old and unscored > 0                 # 미채점 prior(IMPACT_PRIOR=1, 0 매몰 금지)


def test_select_top_k_caps_and_ranks():
    stories = [_s(f"s{i}", impact=(3 if i < 5 else 1)) for i in range(30)]
    top = select_top_k(stories, NOW, stratify=False)
    assert len(top) == REPORT_MAX_STORIES
    assert top[0]["impact"] == 3                        # 랭킹 상위 우선


def test_select_top_k_sector_stratify_cap():
    # 반도체(sector_tech) 20건이 전부 impact 3 — cap 없으면 top-15 독식
    tech = [_s(f"t{i}", impact=3, sector="sector_tech") for i in range(20)]
    fin = [_s(f"f{i}", impact=1, sector="sector_financials") for i in range(3)]
    top = select_top_k(tech + fin, NOW, stratify=True)
    n_tech = sum(1 for s in top if "sector_tech" in s["lenses"])
    assert n_tech == SECTOR_STRATIFY_CAP                # 같은 섹터 최대 N건(cap — fill 아님)
    assert any("sector_financials" in s["lenses"] for s in top)


def test_select_rising_density_and_exclusion():
    hot = _s("hot", ndev=5)                             # 24h 델타 5건 — 밀도 최고
    cold = _s("cold", ndev=1)
    in_topk = _s("taken", ndev=4)
    rising = select_rising([hot, cold, in_topk], top_k_ids={"taken"}, now=NOW)
    assert [s["id"] for s in rising][0] == "hot"
    assert all(s["id"] != "taken" for s in rising)      # 타 리포트 top-K 등장분 제외


def test_min_stories_constant():
    assert REPORT_MIN_STORIES >= 2                      # 사이트 표시 기준(count>=2)과 동일 발상
```

- [ ] **Step 2: 실패 확인** — FAIL(모듈 없음)

- [ ] **Step 3: 구현** — `src/newsstore/enrich/report.py`:

```python
"""리포트 패스(리포트 탭 v1) — 스토리-그라운디드 섹션 리포트 + 백드롭 + 급부상.

스펙 docs/superpowers/specs/2026-06-30-report-tab-design.md §4·§5. 프레임은 frames.py(입력으로만).
top-K 랭킹은 UI(web/index.html storyRank)와 같은 정의: impact × 신선도(delta_time 최신성)."""
from __future__ import annotations
import logging
from datetime import datetime, timedelta, timezone

from .gemini import LLMError

log = logging.getLogger("newsstore.enrich.report")

REPORT_MAX_STORIES = 15       # 입력 하드캡 K(§4 — 토큰 폭탄 차단)
REPORT_MIN_STORIES = 2        # 빈 리포트 가드(§4 — 미만이면 콜 스킵)
SECTOR_STRATIFY_CAP = 5       # 주식 렌즈 층화: 같은 sector_* 최대 N건(§4 — cap, fill 아님)
RISING_MAX = 10               # 급부상 입력 상한
IMPACT_PRIOR = 1              # 미채점 prior(UI IMPACT_PRIOR와 동일 의미)
FRESH_TAU_H = 12.0            # 신선도 감쇠(UI FRESH_TAU_H와 동일)
DELTA_WINDOW = timedelta(hours=24)   # 급부상 밀도 창


def _latest_delta(story: dict):
    best = None
    for d in (story.get("developments") or []):
        t = d.get("delta_time") or d.get("time")
        if t is not None and (best is None or t > best):
            best = t
    return best or story.get("last_seen")


def story_rank(story: dict, now) -> float:
    """UI storyRank와 같은 정의(impact × 1/(1+age/tau)) — 프론트·백 동일 랭킹(§4)."""
    impact = story.get("impact")
    impact = IMPACT_PRIOR if impact is None else float(impact)
    ms = _latest_delta(story)
    if ms is None:
        return 0.0
    age_h = max(0.0, (now - ms).total_seconds() / 3600.0)
    return impact * (1.0 / (1.0 + age_h / FRESH_TAU_H))


def select_top_k(stories: list[dict], now, *, stratify: bool) -> list[dict]:
    """랭킹 상위 K. stratify=True(주식 렌즈)면 같은 sector_* 라벨 최대 SECTOR_STRATIFY_CAP —
    한 테마 독식 방지(cap). sector 라벨 없는 스토리는 cap 미적용."""
    ranked = sorted(stories, key=lambda s: (-story_rank(s, now), s.get("id", "")))
    if not stratify:
        return ranked[:REPORT_MAX_STORIES]
    out, per_sector = [], {}
    for s in ranked:
        sectors = [l for l in (s.get("lenses") or []) if l.startswith("sector_")]
        if sectors and any(per_sector.get(x, 0) >= SECTOR_STRATIFY_CAP for x in sectors):
            continue
        for x in sectors:
            per_sector[x] = per_sector.get(x, 0) + 1
        out.append(s)
        if len(out) >= REPORT_MAX_STORIES:
            break
    return out


def delta_density_24h(story: dict, now) -> int:
    """최근 24h delta_time 수(velocity 근사 — §3.5. 한계: 신규성 아님)."""
    n = 0
    for d in (story.get("developments") or []):
        t = d.get("delta_time") or d.get("time")
        if t is not None and (now - t) <= DELTA_WINDOW:
            n += 1
    return n


def select_rising(stories: list[dict], *, top_k_ids: set[str], now) -> list[dict]:
    """급부상 결정론 선정: 밀도 상위 + 전 렌즈 top-K(입력 선정 집합) 미등장(§3.5)."""
    cands = [(delta_density_24h(s, now), s) for s in stories
             if s.get("id") not in top_k_ids]
    cands = [(d, s) for d, s in cands if d > 0]
    cands.sort(key=lambda t: (-t[0], t[1].get("id", "")))
    return [s for _, s in cands[:RISING_MAX]]
```

- [ ] **Step 4: 통과 확인** — 5 passed
- [ ] **Step 5: 커밋** — `git commit -m "feat(#20): top-K 선정(UI 동일 storyRank·섹터 층화 cap)과 급부상 결정론 선정"`

---

### Task 8: report.py — validate_report(story_ids·pole_id 실재) + 프롬프트

**Files:**
- Modify: `src/newsstore/enrich/report.py`
- Test: `tests/test_report.py`

- [ ] **Step 1: 실패 테스트 작성** — append:

```python
from newsstore.enrich.report import validate_report, build_section_prompt, build_backdrop_prompt

FRAME = {"risks": [{"id": "r1", "text": "빅테크 capex 감속"}],
         "premiums": [{"id": "p1", "text": "HBM 수요"}],
         "watchpoints": [{"id": "w1", "text": "메타 실적"}]}
GOOD = {"headline": "반도체, capex 우려 속 수요 견조", "lead": "핵심 요약.",
        "sections": [
            {"name": "risk_triggered", "items": [
                {"text": "MS가 capex 재검토 시사", "story_ids": ["s1"], "pole_id": "r1"}]},
            {"name": "premium_triggered", "items": []},
            {"name": "not_triggered", "items": [{"text": "HBM 수요", "story_ids": [], "pole_id": "p1"}]},
            {"name": "watchpoints", "items": [{"text": "메타 실적", "story_ids": [], "pole_id": "w1"}]}]}


def test_validate_report_accepts_good_and_drops_hallucinated():
    bad_items = {**GOOD, "sections": [
        {"name": "risk_triggered", "items": [
            {"text": "실재", "story_ids": ["s1"], "pole_id": "r1"},
            {"text": "환각 스토리", "story_ids": ["ghost"], "pole_id": "r1"},   # story 환각 → 드롭
            {"text": "환각 극", "story_ids": ["s1"], "pole_id": "r99"}]}]}      # 극 환각 → 드롭
    v = validate_report(bad_items, frame=FRAME, input_story_ids={"s1"})
    items = v["sections"][0]["items"]
    assert [i["text"] for i in items] == ["실재"]


def test_validate_report_trigger_requires_citation():
    # 트리거 주장은 story_ids 인용 필수(B) — 빈 인용의 *_triggered 항목은 드롭
    r = {**GOOD, "sections": [{"name": "risk_triggered",
                               "items": [{"text": "인용 없음", "story_ids": [], "pole_id": "r1"}]}]}
    v = validate_report(r, frame=FRAME, input_story_ids={"s1"})
    assert v["sections"][0]["items"] == []


def test_validate_report_rejects_missing_required():
    assert validate_report(None, frame=FRAME, input_story_ids=set()) is None
    assert validate_report({"headline": "", "lead": "x", "sections": []},
                           frame=FRAME, input_story_ids=set()) is None


def test_section_prompt_contains_frame_stories_backdrop():
    p = build_section_prompt("kr_equity", FRAME,
                             [{"id": "s1", "title": "제목", "summary": "요약"}], "백드롭 텍스트")
    assert "r1" in p and "빅테크 capex 감속" in p       # standing 프레임이 입력에
    assert "s1" in p and "백드롭 텍스트" in p
    assert "매수" in p                                  # 매수/매도 금지 지시 포함(§1)
```

- [ ] **Step 2: 실패 확인** — FAIL

- [ ] **Step 3: 구현** — append:

```python
MAX_HEADLINE = 100
MAX_LEAD = 300
MAX_ITEM_TEXT = 240
SECTION_NAMES = ("risk_triggered", "premium_triggered", "not_triggered", "watchpoints")
_TRIGGER_SECTIONS = ("risk_triggered", "premium_triggered")


def _frame_pole_ids(frame: dict) -> set[str]:
    return {p["id"] for axis in ("risks", "premiums", "watchpoints")
            for p in (frame.get(axis) or [])}


def validate_report(raw, *, frame: dict, input_story_ids: set[str]) -> dict | None:
    """결정론 검증(§5 표): 스키마·headline/lead 필수·인용 story_id 실재(환각 드롭)·
    pole_id가 standing frame에 실재·트리거 항목은 인용 필수(B). 실패 → None."""
    if not isinstance(raw, dict):
        return None
    headline = raw.get("headline")
    lead = raw.get("lead")
    if not (isinstance(headline, str) and headline.strip()
            and isinstance(lead, str) and lead.strip()):
        return None
    pole_ids = _frame_pole_ids(frame)
    sections_in = raw.get("sections")
    if not isinstance(sections_in, list):
        return None
    sections = []
    for sec in sections_in:
        if not (isinstance(sec, dict) and sec.get("name") in SECTION_NAMES):
            continue
        items = []
        for it in (sec.get("items") or []):
            if not (isinstance(it, dict) and isinstance(it.get("text"), str)
                    and it["text"].strip()):
                continue
            ids = [i for i in (it.get("story_ids") or [])
                   if isinstance(i, str) and i in input_story_ids]   # 환각 story 드롭
            pid = it.get("pole_id")
            if pid is not None and pid not in pole_ids:
                continue                                              # 환각 극 드롭
            if sec["name"] in _TRIGGER_SECTIONS and not ids:
                continue                                              # 트리거 = 인용 필수(B)
            items.append({"text": it["text"].strip()[:MAX_ITEM_TEXT],
                          "story_ids": ids, "pole_id": pid})
        sections.append({"name": sec["name"], "items": items})
    return {"headline": headline.strip()[:MAX_HEADLINE], "lead": lead.strip()[:MAX_LEAD],
            "sections": sections}


def build_backdrop_prompt(excerpts: list[str]) -> str:
    return (
        "당신은 매크로/교차자산 데스크 에디터다. 아래 오늘의 주요 스토리 발췌로 "
        "채권·순환매·원자재·매크로 백드롭을 4~6문장으로 합성하라. 예측·매수/매도 조언 금지, "
        "관측된 사실·내러티브만.\n" + "\n".join(excerpts[:40]) +
        '\n아래 JSON만 출력: {"text": "..."}')


def build_section_prompt(lens_id: str, frame: dict, stories: list[dict], backdrop: str) -> str:
    import json as _json
    lines = [f'[{s["id"]}] {s.get("title", "")} :: {(s.get("summary") or "")[:200]}'
             for s in stories]
    return (
        f"당신은 '{lens_id}' 자산군 데일리 리포트 에디터다. standing 프레임(주어진 것 — "
        "새 프레임을 만들지 마라)에 오늘 스토리를 대조하라.\n"
        f"프레임:\n{_json.dumps(frame, ensure_ascii=False)}\n"
        f"매크로 백드롭(참고): {backdrop or '(없음)'}\n"
        "스토리(각 줄 맨 앞 [id]가 story_id):\n" + "\n".join(lines) + "\n"
        "규칙: 매수·매도·비중 조언 금지(재료만). 트리거 판정은 반드시 해당 story_id 인용. "
        "미발생(not_triggered)은 프레임 극 중 72h 트리거 없는 것. watchpoints는 관찰 지점 재확인.\n"
        '아래 JSON만 출력: {"headline":"...","lead":"...","sections":['
        '{"name":"risk_triggered","items":[{"text":"...","story_ids":["..."],"pole_id":"..."}]},'
        '{"name":"premium_triggered","items":[...]},{"name":"not_triggered","items":[...]},'
        '{"name":"watchpoints","items":[...]}]}')
```

- [ ] **Step 4: 통과 확인** — 전부 PASS
- [ ] **Step 5: 커밋** — `git commit -m "feat(#20): 리포트 결정론 검증(인용·극 실재, 트리거 인용 필수)과 섹션·백드롭 프롬프트"`

---

### Task 9: report.py — 리뷰 콜·run_report_pass 오케스트레이션

**Files:**
- Modify: `src/newsstore/enrich/report.py`
- Test: `tests/test_report.py`

- [ ] **Step 1: 실패 테스트 작성** — append:

```python
from newsstore.enrich.report import run_report_pass


class _Store:
    def __init__(self, stories_by_lens, frames):
        self.stories, self.frames = stories_by_lens, frames
        self.reports = {}
    def get_frame(self, lens_id):
        return self.frames.get(lens_id, {})
    def get_stories_for_report(self, lens_id, cutoff):
        return list(self.stories.get(lens_id, []))
    def save_report(self, doc_id, report):
        self.reports[doc_id] = report


class _LLM:
    """프롬프트 역할 마커로 분기(각 마커는 해당 프롬프트에만 존재하는 리터럴 — 구현 프롬프트와
    짝: 리뷰='심사자', 백드롭='데스크 에디터', 섹션='데일리 리포트 에디터'.
    주의: '백드롭' 단어는 섹션 프롬프트 본문에도 나오므로 마커로 쓰면 오라우팅된다)."""
    def __init__(self, section, review, backdrop='{"text": "bd"}'):
        import json
        self.section, self.review = section, review
        self.backdrop = json.loads(backdrop)
        self.n_review = 0
    def generate_json(self, prompt, *, timeout=30.0):
        if "심사자" in prompt:
            self.n_review += 1
            return dict(self.review)
        if "데스크 에디터" in prompt:
            return dict(self.backdrop)
        assert "데일리 리포트 에디터" in prompt          # 오라우팅 fail-loud
        return dict(self.section)


def _stories(n=3):
    return [_s(f"s{i}") for i in range(n)]


SECTION_OK = {"headline": "h", "lead": "l", "sections": [
    {"name": "risk_triggered", "items": [{"text": "x", "story_ids": ["s0"], "pole_id": None}]}]}


def test_run_report_pass_saves_passed_report_and_backdrop():
    store = _Store({"kr_equity": _stories()}, {"kr_equity": FRAME})
    llm = _LLM(SECTION_OK, {"passed": True, "notes": ""})
    totals = run_report_pass(store, llm, lens_ids=["kr_equity"], now=NOW)
    assert totals["reported"] == 1
    saved = store.reports["kr_equity"]
    assert saved["review"]["passed"] is True
    assert saved["frame_updated_at"] == FRAME.get("updated_at")
    # 결정⑧ 역산 금지(§10): 프레임 3축이 리포트 출력에 새어들지 않는다
    assert not ({"risks", "premiums", "watchpoints"} & set(saved))
    assert "_backdrop" in store.reports                 # 백드롭 별도 문서(§6)
    assert llm.n_review >= 2                            # 섹션 리뷰 + 백드롭 grounding 리뷰(§5 표)


def test_run_report_pass_backdrop_review_reject_degrades():
    # 백드롭 리뷰 기각 → 서두 미저장 + 섹션 콜에 미주입(degrade — §5 표). 섹션은 계속 진행.
    class _RejBackdrop(_LLM):
        def generate_json(self, prompt, *, timeout=30.0):
            if "심사자" in prompt:
                self.n_review += 1
                # 첫 심사 콜 = 백드롭 grounding(파이프라인상 섹션보다 선행) → 기각, 이후 통과
                return ({"passed": False, "notes": "무근거"} if self.n_review == 1
                        else {"passed": True, "notes": ""})
            if "데스크 에디터" in prompt:
                return dict(self.backdrop)
            return dict(self.section)
    store = _Store({"kr_equity": _stories()}, {"kr_equity": FRAME})
    llm = _RejBackdrop(SECTION_OK, {"passed": True, "notes": ""})
    totals = run_report_pass(store, llm, lens_ids=["kr_equity"], now=NOW)
    assert "_backdrop" not in store.reports             # 기각 → 미저장(기존 유지)
    assert totals["reported"] == 1                      # 섹션은 백드롭 없이 진행(degrade)


def test_run_report_pass_review_reject_saves_with_badge():
    store = _Store({"kr_equity": _stories()}, {"kr_equity": FRAME})
    llm = _LLM(SECTION_OK, {"passed": False, "notes": "과인용"})
    run_report_pass(store, llm, lens_ids=["kr_equity"], now=NOW)
    r = store.reports["kr_equity"]
    assert r["review"]["passed"] is False and "과인용" in r["review"]["notes"]   # 결정③ 저장+배지


def test_run_report_pass_skips_below_min_stories():
    store = _Store({"kr_equity": _stories(1)}, {"kr_equity": FRAME})   # REPORT_MIN_STORIES 미만
    llm = _LLM(SECTION_OK, {"passed": True})
    totals = run_report_pass(store, llm, lens_ids=["kr_equity"], now=NOW)
    assert totals["skipped_empty"] == 1 and "kr_equity" not in store.reports


def test_run_report_pass_generation_failure_keeps_existing():
    store = _Store({"kr_equity": _stories()}, {"kr_equity": FRAME})
    store.reports["kr_equity"] = {"headline": "옛것"}
    class _Boom:
        def generate_json(self, prompt, *, timeout=30.0):
            if "심사자" in prompt:
                return {"passed": True, "notes": ""}
            if "데스크 에디터" in prompt:
                return {"text": "bd"}
            from newsstore.enrich.gemini import LLMError
            raise LLMError("down")                       # 섹션 생성 콜만 실패(§5(b) 경로 검증)
    run_report_pass(store, _Boom(), lens_ids=["kr_equity"], now=NOW)
    assert store.reports["kr_equity"]["headline"] == "옛것"    # §5(b) 기존 유지


def test_run_report_pass_generates_rising():
    hot = _s("hot", ndev=5, impact=1)
    store = _Store({"kr_equity": _stories() + [hot]}, {"kr_equity": FRAME})
    llm = _LLM(SECTION_OK, {"passed": True, "notes": ""})
    run_report_pass(store, llm, lens_ids=["kr_equity"], now=NOW)
    if "rising" in store.reports:                       # hot이 top-K에 들면 rising 없음도 합법
        assert store.reports["rising"]["criteria"]
```

- [ ] **Step 2: 실패 확인** — FAIL(`run_report_pass` 없음)

- [ ] **Step 3: 구현** — append:

```python
def build_review_prompt(report: dict, stories: list[dict]) -> str:
    import json as _json
    lines = [f'[{s["id"]}] {s.get("title", "")} :: {(s.get("summary") or "")[:150]}'
             for s in stories]
    return (
        "당신은 리포트 심사자다(grounding+fit). 기각 기준: (1) 항목 주장이 인용 story와 "
        "실제로 무관(과인용), (2) 매수/매도/비중 조언 포함, (3) 출처에 없는 수치 단정.\n"
        f"리포트:\n{_json.dumps(report, ensure_ascii=False)}\n스토리:\n" + "\n".join(lines) + "\n"
        '아래 JSON만 출력: {"passed": true|false, "notes": "기각 사유 또는 빈 문자열"}')


def _review(client, report: dict, stories: list[dict]) -> dict:
    """리뷰 콜 — 실패는 passed=false(통과 위장 금지, §5 표)."""
    try:
        v = client.generate_json(build_review_prompt(report, stories), timeout=60.0)
    except LLMError as e:
        return {"passed": False, "notes": f"리뷰 불가: {e}"}
    if not isinstance(v, dict) or not isinstance(v.get("passed"), bool):
        return {"passed": False, "notes": "리뷰 응답 형식 위반"}
    return {"passed": v["passed"], "notes": str(v.get("notes") or "")}


def run_report_pass(store, client, *, lens_ids: list[str], now, window=None) -> dict:
    """§4 파이프라인: 백드롭 → 섹션(렌즈별) → 급부상 → 저장. 프레임은 입력(frames.py 선행)."""
    cutoff = now - (window or timedelta(hours=72))
    totals = {"reported": 0, "skipped_empty": 0, "failed": 0}

    per_lens: dict[str, list[dict]] = {l: store.get_stories_for_report(l, cutoff=cutoff)
                                       for l in lens_ids}
    # 백드롭(생성 1콜 + grounding 리뷰 1콜 — §5 표: 16개 섹션 공통 입력이라 오염 전파 지점).
    # 생성·검증·리뷰 어느 것이든 실패 → 서두 생략 + 섹션 미주입(degrade), _backdrop 미저장(기존 유지).
    backdrop = ""
    all_top3 = [s for ss in per_lens.values() for s in ss[:3]]
    excerpts = [f'{s.get("title", "")}' for s in all_top3]
    if excerpts:
        try:
            raw = client.generate_json(build_backdrop_prompt(excerpts), timeout=60.0)
            text = (raw.get("text") or "").strip() if isinstance(raw, dict) else ""
            if text and len(text) <= 1200:               # 결정론: 비어있지 않음·길이 상한
                verdict = _review(client, {"text": text}, all_top3)
                if verdict["passed"]:
                    backdrop = text
                    store.save_report("_backdrop", {"text": backdrop, "generated_at": now,
                                                    "review": verdict})
                else:
                    log.warning("backdrop 리뷰 기각(%s) — 서두 생략", verdict["notes"])
        except LLMError as e:
            log.warning("backdrop 실패 — 서두 생략: %s", e)

    top_k_ids: set[str] = set()
    selected: dict[str, list[dict]] = {}
    for lens_id in lens_ids:
        stories = per_lens[lens_id]
        if len(stories) < REPORT_MIN_STORIES:
            totals["skipped_empty"] += 1
            continue
        top = select_top_k(stories, now, stratify=lens_id.endswith("_equity"))
        selected[lens_id] = top
        top_k_ids |= {s["id"] for s in top}

    def _one(doc_id, lens_id, frame, top, criteria=None):
        try:
            raw = client.generate_json(build_section_prompt(lens_id, frame, top, backdrop),
                                       timeout=90.0)
        except LLMError as e:
            log.warning("report %s: 생성 실패 — 기존 유지(§5b): %s", doc_id, e)
            totals["failed"] += 1
            return
        v = validate_report(raw, frame=frame, input_story_ids={s["id"] for s in top})
        if v is None:
            log.warning("report %s: 결정론 검증 실패 — 기존 유지", doc_id)
            totals["failed"] += 1
            return
        review = _review(client, v, top)                # 기각이어도 저장+배지(결정③)
        doc = {**v, "topic": lens_id, "generated_at": now,
               "frame_updated_at": frame.get("updated_at"), "review": review}
        if criteria:
            doc["criteria"] = criteria
        store.save_report(doc_id, doc)
        totals["reported"] += 1

    for lens_id, top in selected.items():
        _one(lens_id, lens_id, store.get_frame(lens_id), top)

    # 급부상 — 전 렌즈 top-K 확정 후(§3.5 순서 의존)
    all_stories = {s["id"]: s for ss in per_lens.values() for s in ss}
    rising = select_rising(list(all_stories.values()), top_k_ids=top_k_ids, now=now)
    if len(rising) >= REPORT_MIN_STORIES:
        _one("rising", "rising", {}, rising,
             criteria="최근 24h 델타 밀도 상위 + 타 리포트 top-K 미등장(결정론)")
    log.info("report pass: %s", totals)
    return totals
```

- [ ] **Step 4: 통과 확인** — `pytest -q tests/test_report.py tests/test_frames.py` → 전부 PASS
- [ ] **Step 5: 커밋** — `git commit -m "feat(#20): 리포트 패스 오케스트레이션 — 백드롭·섹션(리뷰 1콜)·급부상, 결정③⑤(b) 실패 거동"`

---

### Task 10: run_enrich --mode report 배선

**Files:**
- Modify: `src/newsstore/entrypoints/run_enrich.py` (`--mode` choices에 `report` 추가 + 분기)
- Test: `tests/test_run.py`

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_run.py`에 append (기존 스타일 확인 후 동일 픽스처 사용; 핵심 단언):

```python
def test_run_enrich_mode_report_wires_frame_then_report(monkeypatch, store):
    # --mode report가 (1) 프레임 패스 → (2) 리포트 패스 순서로 호출하는지 배선만 검증
    import newsstore.entrypoints.run_enrich as re_mod
    calls = []
    monkeypatch.setattr("newsstore.enrich.frames.run_frame_pass",
                        lambda *a, **k: calls.append("frames") or 0)
    monkeypatch.setattr("newsstore.enrich.report.run_report_pass",
                        lambda *a, **k: calls.append("report") or {"reported": 0})
    monkeypatch.setattr(re_mod, "make_store", lambda: store)
    monkeypatch.setattr(re_mod, "GeminiClient", lambda *a, **k: object())
    monkeypatch.setenv("GEMINI_API_KEY", "dummy")
    assert re_mod.main(["--mode", "report"]) == 0
    assert calls == ["frames", "report"]                # 프레임 선행(§4)
```

(주의: store 픽스처는 context manager 프로토콜(`__enter__/__exit__`)을 이미 구현 — FirestoreStore 그대로 사용.)

- [ ] **Step 2: 실패 확인** — FAIL(choices에 report 없음 → SystemExit 2)

- [ ] **Step 3: 구현** — `run_enrich.py`:
  - `--mode` choices에 `"report"` 추가, help에 `/ report=프레임+데일리 리포트(스펙 2026-06-30)` 추가.
  - main 분기 추가:

```python
            elif args.mode == "report":
                from ..enrich import frames as _frames, report as _report, topics as _topics
                now = datetime.now(timezone.utc)
                lens_ids = _topics.report_lens_ids(_topics.load_topics())
                _frames.run_frame_pass(store, client, lens_ids=lens_ids, now=now)   # 선행(§4)
                totals = _report.run_report_pass(store, client, lens_ids=lens_ids, now=now)
```

  (monkeypatch가 모듈 함수를 갈아끼우므로 분기 내부에서 `_frames.run_frame_pass` 형태가 아니라 **함수를 임포트한 모듈 경유로 호출**해야 한다 — 위 코드가 그 형태다.)

- [ ] **Step 4: 통과 확인** — PASS
- [ ] **Step 5: 커밋** — `git commit -m "feat(#20): run_enrich --mode report — 프레임 패스 선행 후 리포트 패스"`

---

### Task 11: firestore.rules — frames/reports public read

**Files:**
- Modify: `firestore.rules`
- Test: (규칙은 배포 검증 — 파일 diff 확인)

- [ ] **Step 1: 현행 규칙 확인** — `firestore.rules`를 읽고 items/stories/meta match 블록과 같은 스타일로 추가:

```
    match /reports/{doc} {
      allow read: if true;          // 리포트 탭(공개 read — 스펙 §6)
      allow write: if false;
    }
    match /frames/{doc} {
      allow read: if true;          // 섹션 머리 프레임 표시(§7)
      allow write: if false;
    }
```

(frames_history는 UI가 읽지 않으므로 기본 거부 유지 — 규칙 추가 안 함.)

- [ ] **Step 2: 커밋** — `git commit -m "feat(#20): firestore.rules — frames/reports 공개 read(백엔드 전용 write)"`

---

### Task 12: web UI — 리포트 순수 로직(node 테스트)

**Files:**
- Modify: `web/index.html` (`REPORT-LOGIC-START/END` 마커 블록 신설 — STORIES-LOGIC 마커와 동일 관례)
- Test: `tests/web/report_logic.test.mjs` (신규 — stories_logic.test.mjs와 동일 슬라이스 방식)

- [ ] **Step 1: 실패 테스트 작성** — `tests/web/report_logic.test.mjs`:

```javascript
// 리포트 탭 순수 로직 — index.html REPORT-LOGIC 마커 슬라이스(node 단독).
import { readFileSync } from "node:fs";
import assert from "node:assert/strict";

const html = readFileSync(new URL("../../web/index.html", import.meta.url), "utf8");
const START = "// === REPORT-LOGIC-START", END = "// === REPORT-LOGIC-END";
const i = html.indexOf(START), j = html.indexOf(END);
assert.ok(i !== -1 && j !== -1 && j > i, "REPORT-LOGIC 마커 필요(드리프트 가드)");
const { assembleReportDoc, reportStatus, crossLinks, dedupCards } =
  new Function(html.slice(i, j) +
    "\nreturn { assembleReportDoc, reportStatus, crossLinks, dedupCards };")();

let pass = 0, fail = 0;
const test = (n, f) => { try { f(); pass++; } catch (e) { fail++; console.error("FAIL:", n, "\n ", e.message); } };
const NOW = Date.UTC(2026, 6, 4, 12, 0, 0);
const rep = (topic, over = {}) => ({ topic, headline: "h", lead: "l",
  sections: [{ name: "risk_triggered", items: [{ text: "x", story_ids: ["s1"], pole_id: "r1" }] }],
  generated_at: new Date(NOW - 3600e3), review: { passed: true }, ...over });

test("assembleReportDoc: 그룹 순서 + 백드롭 서두 + rising 말미", () => {
  const groups = { "주식": ["kr_equity", "us_equity"], "코인": ["crypto"] };
  const reports = { kr_equity: rep("kr_equity"), crypto: rep("crypto"),
                    rising: rep("rising"), _backdrop: { text: "bd" } };
  const doc = assembleReportDoc(groups, reports);
  assert.equal(doc.backdrop, "bd");
  assert.deepEqual(doc.sections.map(s => s.lensId), ["kr_equity", "crypto", "rising"]);
  assert.equal(doc.sections[0].group, "주식");          // us_equity 리포트 없음 → 생략(fail-soft)
});

test("reportStatus: 정상/생성전/갱신지연 3구분", () => {
  assert.equal(reportStatus(rep("x"), NOW), "ok");
  assert.equal(reportStatus(null, NOW), "not_generated");                    // §4 빈 스킵
  assert.equal(reportStatus(rep("x", { generated_at: new Date(NOW - 26 * 3600e3) }), NOW),
               "stale");                                                     // §5(b) 1일 초과
});

test("crossLinks: 같은 스토리 다중 섹션 인용 → 상호 링크", () => {
  const secs = [{ lensId: "kr_equity", report: rep("kr_equity") },
                { lensId: "us_policy", report: rep("us_policy") }];
  const links = crossLinks(secs);                       // s1이 두 섹션에 인용됨
  assert.deepEqual(links["s1"].sort(), ["kr_equity", "us_policy"]);
});

test("dedupCards: 문서 전체에서 카드 1회, 재인용은 참조 배지", () => {
  const order = ["s1", "s2", "s1"];
  const d = dedupCards(order);
  assert.deepEqual(d, [{ id: "s1", first: true }, { id: "s2", first: true },
                       { id: "s1", first: false }]);
});

console.log(`\nreport_logic: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
```

- [ ] **Step 2: 실패 확인** — `node tests/web/report_logic.test.mjs` → FAIL(마커 없음)

- [ ] **Step 3: 구현** — `web/index.html`의 STORIES-LOGIC-END 뒤에 마커 블록 추가(순수함수만, DOM 금지):

```javascript
    // === REPORT-LOGIC-START (node test가 슬라이스; 순수함수만, DOM/외부스코프 금지) ===
    const REPORT_STALE_MS = 24 * 3600 * 1000;           // §5(b) 기대 주기 1일
    function assembleReportDoc(groups, reports) {
      // 단일 데일리 문서 결정론 조립(§4): 백드롭 서두 → report_group 순 섹션 → rising 말미.
      // 리포트 없는 렌즈는 생략(fail-soft — 상태는 reportStatus가 별도 판정).
      const sections = [];
      for (const [group, lensIds] of Object.entries(groups || {}))
        for (const lid of lensIds)
          if (reports && reports[lid]) sections.push({ lensId: lid, group, report: reports[lid] });
      if (reports && reports.rising)
        sections.push({ lensId: "rising", group: "급부상", report: reports.rising });
      return { backdrop: (reports && reports._backdrop && reports._backdrop.text) || "",
               sections };
    }
    function reportStatus(report, now) {
      if (!report) return "not_generated";              // 스토리 부족 스킵(§4) — "아직 생성 전"
      const g = report.generated_at;
      const ms = g && typeof g.toDate === "function" ? g.toDate().getTime()
        : (g instanceof Date ? g.getTime() : new Date(g).getTime());
      if (!Number.isFinite(ms) || (now - ms) > REPORT_STALE_MS) return "stale";   // §5(b)
      return "ok";
    }
    function crossLinks(sections) {
      // 같은 story_id가 여러 섹션에 인용 → {storyId: [lensId...]} (다중 인용 결정론 — §7)
      const byStory = {};
      for (const { lensId, report } of (sections || []))
        for (const sec of ((report && report.sections) || []))
          for (const it of (sec.items || []))
            for (const sid of (it.story_ids || [])) {
              if (!byStory[sid]) byStory[sid] = new Set();
              byStory[sid].add(lensId);
            }
      const out = {};
      for (const [sid, set] of Object.entries(byStory))
        if (set.size > 1) out[sid] = [...set];
      return out;
    }
    function dedupCards(storyIdOrder) {
      // 문서 전체 등장 순서에서 첫 인용만 카드(first:true), 재인용은 참조 배지(§7 dedup)
      const seen = new Set();
      return (storyIdOrder || []).map(id => {
        const first = !seen.has(id);
        seen.add(id);
        return { id, first };
      });
    }
    // === REPORT-LOGIC-END ===
```

- [ ] **Step 4: 통과 확인** — `node tests/web/report_logic.test.mjs` → 4 passed (+기존 stories/feed node 테스트 재실행 무회귀)
- [ ] **Step 5: 커밋** — `git commit -m "feat(#20): 리포트 UI 순수 로직 — 단일 문서 조립·상태 3구분·교차링크·카드 dedup"`

---

### Task 13: web UI — 리포트 탭 렌더·배선

**Files:**
- Modify: `web/index.html` (탭 버튼·뷰·렌더 함수·로드)

- [ ] **Step 1: 탭 추가** — 헤더 `.tabs`에 `<button class="tab" id="tabReport">리포트</button>`, main에 `<div id="reportView" hidden><div id="reportDoc"></div></div>`. `showTab`을 3-탭으로 확장(`which === "report"` 분기, hash `#report`, 최초 진입 시 `loadReport()` 1회).

- [ ] **Step 2: 로드·렌더 구현** — 스토리 뷰 코드 뒤에(모듈 스코프):

```javascript
    // ============================ 리포트 뷰 ============================
    const reportView = document.getElementById("reportView");
    const reportDocEl = document.getElementById("reportDoc");
    const tabReport = document.getElementById("tabReport");
    let reportLoaded = false, REPORT_GROUPS = {};        // meta/report_groups(SSOT 발행) 폴백 없음 → frames 도출

    async function loadReport() {
      reportDocEl.innerHTML = `<div class="sempty">불러오는 중…</div>`;
      await ensureLensLabels();
      try {
        const [repSnap, frameSnap] = await Promise.all([
          getDocs(collection(db, "reports")), getDocs(collection(db, "frames"))]);
        const reports = {}; repSnap.docs.forEach(d => reports[d.id] = d.data());
        const frames = {}; frameSnap.docs.forEach(d => frames[d.id] = d.data());
        const groupsSnap = await getDoc(doc(db, "meta", "report_groups"));
        REPORT_GROUPS = groupsSnap.exists() ? (groupsSnap.data() || {}) : {};
        const docm = assembleReportDoc(REPORT_GROUPS, reports);
        const now = Date.now();
        const links = crossLinks(docm.sections);
        if (!docm.sections.length) {
          reportDocEl.innerHTML = `<div class="sempty">아직 생성된 리포트가 없어요.</div>`;
          return;
        }
        // 인용 스토리 카드용 스토리 문서 일괄 로드(in ≤30 청크)
        const citedIds = [...new Set(docm.sections.flatMap(({ report }) =>
          (report.sections || []).flatMap(s => (s.items || []).flatMap(i => i.story_ids || []))))];
        const cited = new Map();
        for (let k = 0; k < citedIds.length; k += 30) {
          const chunk = citedIds.slice(k, k + 30);
          const qs = await getDocs(query(collection(db, "stories"),
                                         where(documentId(), "in", chunk)));
          qs.docs.forEach(d => cited.set(d.id, { id: d.id, ...d.data() }));
        }
        renderReportDoc(docm, frames, links, cited, now);
      } catch (e) {
        reportDocEl.innerHTML = `<div class="sempty">불러오기 실패: <code>${esc(e.message)}</code></div>`;
      }
    }

    const SEC_LABEL = { risk_triggered: "아킬레스건 트리거", premium_triggered: "기대 트리거",
                        not_triggered: "미발생", watchpoints: "주시 포인트" };
    function frameChipsHtml(f) {
      if (!f) return "";
      const ax = (label, arr, cls) => (arr || []).map(p =>
        `<span class="lchip" title="${esc(p.id)}" style="color:var(--${cls})">${txt(p.text)}</span>`).join("");
      return `<div class="lchips">${ax("risk", f.risks, "risk")}${ax("premium", f.premiums, "imp")}${ax("watch", f.watchpoints, "green")}</div>`;
    }
    function renderReportDoc(docm, frames, links, cited, now) {
      const seenCards = new Set();
      const anchors = docm.sections.map(({ lensId, group }) =>
        `<a href="#rep-${esc(lensId)}" class="pill">${txt(group)} · ${txt(LENS_LABELS[lensId] || lensId)}</a>`).join(" ");
      const body = docm.sections.map(({ lensId, group, report }) => {
        const st = reportStatus(report, now);
        const badge = report.review && report.review.passed === false
          ? `<span class="newb" style="background:var(--risk)">검증 실패</span>` : "";
        const stale = st === "stale" ? `<span class="newb" style="background:var(--mut)">갱신 지연</span>` : "";
        // §5(c)·§7: 프레임 자체가 낡았거나(updated_at 1일+), 본문이 참조한 판(frame_updated_at)과
        // 현행 프레임 판이 다르면 표기 — reportStatus와 같은 toMs 규칙 사용
        const f = frames[lensId];
        const fMs = f && f.updated_at && f.updated_at.toDate ? f.updated_at.toDate().getTime() : null;
        const frameStale = fMs != null && (now - fMs) > REPORT_STALE_MS
          ? `<span class="newb" style="background:var(--mut)">프레임 갱신 지연</span>` : "";
        const refMs = report.frame_updated_at && report.frame_updated_at.toDate
          ? report.frame_updated_at.toDate().getTime() : null;
        const skew = (fMs != null && refMs != null && fMs !== refMs)
          ? `<span class="pill">본문은 이전 프레임 기준</span>` : "";
        const secs = (report.sections || []).map(sec => {
          const items = (sec.items || []).map(it => {
            const cards = (it.story_ids || []).map(sid => {
              const s = cited.get(sid);
              if (!s) return "";
              if (seenCards.has(sid)) {                  // dedup: 재인용은 참조 배지
                const rel = (links[sid] || []).filter(l => l !== lensId)
                  .map(l => LENS_LABELS[l] || l).join(", ");
                return `<span class="pill">↩ 위 카드 참조${rel ? ` · 관련: ${txt(rel)}` : ""}</span>`;
              }
              seenCards.add(sid);
              return storyCardHtml(s);                   // 기존 스토리 카드 재사용(§7)
            }).join("");
            return `<li>${txt(it.text)}<div class="darts">${cards}</div></li>`;
          }).join("");
          return items ? `<h4>${SEC_LABEL[sec.name] || esc(sec.name)}</h4><ul class="abul">${items}</ul>` : "";
        }).join("");
        return `<section class="sdetail" id="rep-${esc(lensId)}">
          <div class="seclbl">${txt(group)}</div>
          <div class="dt">${txt(report.headline) || "(제목 없음)"} ${badge}${stale}${frameStale}${skew}</div>
          ${frameChipsHtml(frames[lensId])}
          <div class="dlead">${txt(report.lead)}</div>${secs}
          <div class="dmeta">${relTime(report.generated_at && report.generated_at.toDate ? report.generated_at.toDate() : null)} · 가격 미반영(이슈 중심)</div>
        </section>`;
      }).join("");
      reportDocEl.innerHTML =
        (docm.backdrop ? `<div class="sdetail"><div class="dlead">${txt(docm.backdrop)}</div></div>` : "") +
        `<div class="lchips">${anchors}</div>` + body;
    }
```

  (import에 `documentId`를 firebase-firestore 모듈에서 추가. `meta/report_groups`는 Task 14에서 백엔드가 발행 — UI는 SSOT 소비만.)

- [ ] **Step 3: 스토리 카드 클릭 배선** — reportDocEl에 위임 리스너: `.scard` 클릭 시 `location.hash = "#stories"` 후 `openStory(id)` (스토리 탭 디테일 재사용). 코드:

```javascript
    reportDocEl.addEventListener("click", e => {
      const card = e.target.closest(".scard");
      if (!card) return;
      location.hash = "#stories";
      setTimeout(() => openStory(card.dataset.id), 0);   // 탭 전환 후 디테일 오픈
    });
```

- [ ] **Step 4: 수동 검증** — `node tests/web/*.mjs` 3파일 전부 PASS + 브라우저 스모크는 배포 후(§8).
- [ ] **Step 5: 커밋** — `git commit -m "feat(#20): 리포트 탭 렌더 — 단일 문서·프레임 머리·카드 embed·배지·앵커"`

---

### Task 14: meta/report_groups 발행(백엔드 → UI SSOT 전달)

**Files:**
- Modify: `src/newsstore/entrypoints/run_enrich.py` (report 분기에서 `set_meta`)
- Test: `tests/test_run.py`

- [ ] **Step 1: 실패 테스트** — Task 10 테스트에 단언 추가:

```python
    # report 모드는 UI 앵커용 그룹 매핑을 발행한다(topics.yaml SSOT → meta/report_groups)
    groups = store.db.collection("meta").document("report_groups").get().to_dict() or {}
    assert groups.get("주식") == ["kr_equity", "us_equity"]
```

- [ ] **Step 2: 실패 확인** — FAIL
- [ ] **Step 3: 구현** — report 분기에서 run_frame_pass 전에:

```python
                store.set_meta("report_groups", _topics.report_groups(_topics.load_topics()))
```

- [ ] **Step 4: 통과 확인** — PASS
- [ ] **Step 5: 커밋** — `git commit -m "feat(#20): meta/report_groups 발행 — UI 앵커가 topics.yaml에서 도출(SSOT)"`

---

### Task 15: 전체 회귀 + 마무리

- [ ] **Step 1: 전체 테스트** — `MSYS_NO_PATHCONV=1 docker compose run --rm test` → **FAIL=0** + `node tests/web/report_logic.test.mjs && node tests/web/stories_logic.test.mjs && node tests/web/feed_logic.test.mjs` 전부 PASS.
- [ ] **Step 2: 계약 문서 최종 대조** — firestore-contract.md의 frames/reports 서술이 구현과 일치하는지 diff 검토(드리프트 0).
- [ ] **Step 3: 푸시** — `git push origin main`. (배포는 사용자가 집에서 — Job 이미지 재빌드 + Hosting 재배포 + Scheduler에 report 모드 1×/일 추가는 docs/operations.md 절차.)

<!-- spec-review: passed -->
