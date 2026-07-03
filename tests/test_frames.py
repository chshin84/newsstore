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
        # 리뷰 프롬프트는 '심사' 단어 포함(구현 계약) — fake 분기용


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
    from newsstore.enrich.gemini import LLMError
    old = {"risks": [{"id": "r1", "text": "기존"}], "premiums": [], "watchpoints": []}
    rejected = _LLM(frame_resp={"risks": [{"id": "r9", "text": "무근거"}], "premiums": [],
                                "watchpoints": []},
                    review_resp={"passed": False, "notes": "근거 없음"})
    store = _Store({"fx": old})
    run_frame_pass(store, rejected, lens_ids=["fx"], now=NOW)
    assert "fx" not in store.saved                      # 기각 → 어제 판 유지(저장 안 함)
    boom = _LLM(frame_resp=LLMError("down"))
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
