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


def test_validate_frame_preserves_achilles_and_evidence():
    # v1 구조화: achilles_kind(words_deeds|structural만) + evidence_dev_ids 보존.
    raw = {"risks": [
        {"id": "r1", "text": "메타 capex 감축 실토", "achilles_kind": "words_deeds",
         "evidence_dev_ids": ["s1", "ghost"]},          # ghost는 입력에 없음 → 드롭
        {"id": "r2", "text": "구조적 이월", "achilles_kind": "structural",
         "evidence_dev_ids": []},                        # 이월 구조극은 공란 허용
        {"id": "r3", "text": "미분류", "achilles_kind": "bogus"}],  # 잘못된 enum → null
        "premiums": [], "watchpoints": []}
    v = validate_frame(raw, input_story_ids={"s1"})
    r = {p["id"]: p for p in v["risks"]}
    assert r["r1"]["achilles_kind"] == "words_deeds"
    assert r["r1"]["evidence_dev_ids"] == ["s1"]         # 환각 dev_id 드롭
    assert r["r2"]["achilles_kind"] == "structural" and r["r2"]["evidence_dev_ids"] == []
    assert r["r3"]["achilles_kind"] is None              # 잘못된 enum → null


def test_validate_frame_backward_compat_text_only():
    # 기존 {id,text}만 있는 극도 그대로 통과(하위호환) — 신규 필드는 기본값.
    v = validate_frame({"risks": [{"id": "r1", "text": "옛 극"}], "premiums": [], "watchpoints": []})
    p = v["risks"][0]
    assert p["id"] == "r1" and p["text"] == "옛 극"
    assert p["achilles_kind"] is None and p["evidence_dev_ids"] == []


def test_frame_diff_new_and_changed_only():
    new = {"risks": [{"id": "r1", "text": "빅테크 capex 감속(수정)"},   # 텍스트 변경
                     {"id": "r9", "text": "관세 재점화"}],              # 신규
           "premiums": [{"id": "p1", "text": "HBM 수요"}],             # 동일 유지
           "watchpoints": []}
    d = frame_diff(OLD, new)
    assert {p["id"] for p in d} == {"r1", "r9"}          # 유지 극(p1)은 diff 아님 → 리뷰 0대상


from datetime import datetime, timezone, timedelta
from newsstore.enrich.frames import (build_frame_prompt, build_frame_review_prompt,
                                     run_frame_pass)

NOW = datetime(2026, 7, 4, 7, 0, tzinfo=timezone.utc)
STORIES = [{"id": "s1", "title": "엔비디아 실적 서프라이즈", "summary": "HBM 수요 급증"}]


class _LLM:
    def __init__(self, frame_resp, review_resp=None):
        self.frame_resp, self.review_resp = frame_resp, review_resp
        self.calls = []
    def generate_json(self, prompt, *, timeout=30.0, model=None):
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


def test_frame_prompt_survives_real_frame_with_datetime():
    # C1 회귀: 실 프레임(get_frame)은 updated_at(datetime)을 포함 — dict 통째 json.dumps면
    # TypeError. 3축(AXES)만 추려 직렬화해야 한다.
    old = {**OLD, "updated_at": datetime(2026, 7, 4, 7, 0, tzinfo=timezone.utc)}
    p = build_frame_prompt("kr_equity", old, STORIES)
    assert isinstance(p, str)
    assert "빅테크 capex 감속" in p and "HBM 수요" in p   # 3축 극이 프롬프트에 실림


def test_frame_prompt_has_ras_and_structured_output():
    # v1: RAS(말-행동 괴리) 준거 + 구조화 출력 형식이 프롬프트에 명시되고, 스토리 id가 실려
    # LLM이 evidence를 인용할 수 있어야 한다.
    p = build_frame_prompt("sector_tech", OLD, STORIES)
    assert "행동" in p and ("achilles_kind" in p and "evidence_dev_ids" in p)
    assert "words_deeds" in p
    assert "s1" in p                                     # 스토리 id 노출(evidence 인용 근거)


def test_frame_prompt_temporal_arc_and_causal_rule():
    # 시간적 인과: 전개를 시간순 arc(오래된→최신)로 보여주고, 되돌림/현재상태 규칙을 명시.
    from datetime import timedelta
    t0 = NOW - timedelta(days=3)
    story = {"id": "war1", "title": "트럼프 전쟁", "summary": "긴장 고조",
             "developments": [
                 {"text": "낙관: 협상 타결 임박", "delta_time": t0},
                 {"text": "비관: 추가 관세 전격 발표", "delta_time": t0 + timedelta(days=2)}]}
    p = build_frame_prompt("us_policy", OLD, [story])
    assert "협상 타결 임박" in p and "추가 관세 전격 발표" in p       # 전개 arc 전체 노출
    assert p.index("협상 타결 임박") < p.index("추가 관세 전격 발표")  # 오래된→최신 순서
    assert "시간순" in p and ("되돌림" in p or "현재" in p)          # 인과·되돌림 규칙 명시


def test_dev_arc_orders_oldest_to_newest():
    from datetime import timedelta
    from newsstore.enrich.frames import dev_arc
    t0 = NOW - timedelta(days=5)
    story = {"developments": [
        {"text": "C 최신", "delta_time": t0 + timedelta(days=4)},
        {"text": "A 최초", "delta_time": t0},
        {"text": "B 중간", "delta_time": t0 + timedelta(days=2)}]}
    arc = dev_arc(story)
    assert arc.index("A 최초") < arc.index("B 중간") < arc.index("C 최신")   # 시간순 정렬
    assert "→" in arc                                                       # arc 구분자


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


def test_run_frame_pass_attributes_silent_stale_failures(monkeypatch):
    # IB3: 실패(콜·검증·기각)로 어제 판을 조용히 유지한 렌즈를 _failures에 lens_id+사유로 귀속.
    monkeypatch.delenv("NEWSSTORE_FRAME_MIN_AGE_HOURS", raising=False)
    old = {"risks": [{"id": "r1", "text": "기존"}], "premiums": [], "watchpoints": []}
    rejected = _LLM(frame_resp={"risks": [{"id": "r9", "text": "무근거"}], "premiums": [],
                                "watchpoints": []},
                    review_resp={"passed": False, "notes": "근거 없음"})
    store = _Store({"fx": old})
    run_frame_pass(store, rejected, lens_ids=["fx"], now=NOW)
    fails = store.saved["_failures"]["lenses"]
    assert [f["lens_id"] for f in fails] == ["fx"]      # 기각된 렌즈 귀속
    assert fails[0]["reason"] == "retry_rejected"       # 재시도도 기각 사유


def test_run_frame_pass_attributes_llm_error_failure(monkeypatch):
    from newsstore.enrich.gemini import LLMError
    monkeypatch.delenv("NEWSSTORE_FRAME_MIN_AGE_HOURS", raising=False)
    old = {"risks": [{"id": "r1", "text": "기존"}], "premiums": [], "watchpoints": []}
    boom = _LLM(frame_resp=LLMError("down"))
    store = _Store({"fx": old})
    run_frame_pass(store, boom, lens_ids=["fx"], now=NOW)
    fails = store.saved["_failures"]["lenses"]
    assert [f["lens_id"] for f in fails] == ["fx"] and fails[0]["reason"] == "attempt_failed"


def test_run_frame_pass_attributes_retry_failed(monkeypatch):
    # IB3: 1차 기각 → 재생성 콜이 LLMError로 실패(silent-stale) → reason=retry_failed 귀속.
    from newsstore.enrich.gemini import LLMError
    from newsstore.enrich.frames import MARKET_ID
    monkeypatch.delenv("NEWSSTORE_FRAME_MIN_AGE_HOURS", raising=False)

    class _RetryBoom:
        def __init__(self): self.gen_calls, self.review_calls = 0, 0
        def generate_json(self, prompt, *, timeout=30.0, model=None):
            if "심사" in prompt:
                self.review_calls += 1
                return {"passed": False, "notes": "기각"}       # 1차 기각 → 재생성 유도
            self.gen_calls += 1
            if self.gen_calls == 1:
                return {"risks": [{"id": "r9", "text": "1차"}], "premiums": [], "watchpoints": []}
            raise LLMError("regen down")                        # 재생성 콜 실패 → retry_failed
    old = {"risks": [{"id": "r1", "text": "어제"}], "premiums": [], "watchpoints": []}
    store = _Store({"fx": old, MARKET_ID: _FRESH_MARKET})
    run_frame_pass(store, _RetryBoom(), lens_ids=["fx"], now=NOW)
    fails = store.saved["_failures"]["lenses"]
    assert [f["lens_id"] for f in fails] == ["fx"] and fails[0]["reason"] == "retry_failed"


def test_run_frame_pass_no_failures_publishes_empty(monkeypatch):
    # 성공한 렌즈는 _failures에 없다(멱등 빈 발행 — 전 런의 stale 귀속을 지운다).
    monkeypatch.delenv("NEWSSTORE_FRAME_MIN_AGE_HOURS", raising=False)
    llm = _LLM(frame_resp={"risks": [{"id": "r1", "text": "새 극"}], "premiums": [],
                           "watchpoints": []},
               review_resp={"passed": True, "notes": ""})
    store = _Store()
    run_frame_pass(store, llm, lens_ids=["kr_equity"], now=NOW)
    assert store.saved["_failures"]["lenses"] == []     # 실패 없음 → 빈 배열


def test_build_market_prompt_and_injection():
    from newsstore.enrich.frames import build_market_prompt, MARKET_ID
    # 시장 프레임 프롬프트: 전 렌즈 스토리로 '시장 전체가 가장 두려워할 것'을 RAS로.
    mp = build_market_prompt([{"id": "s1", "title": "메타 capex 감축", "summary": "반도체 투매"}])
    assert MARKET_ID == "_market"
    assert "시장" in mp and "s1" in mp and ("행동" in mp or "RAS" in mp)
    # 렌즈 프롬프트에 시장 프레임 주입 시 그 내용이 실린다(interconnectivity 입구)
    market = {"risks": [{"id": "m1", "text": "하이퍼스케일러 capex 철회"}], "premiums": [], "watchpoints": []}
    p = build_frame_prompt("kr_equity", OLD, STORIES, market=market)
    assert "하이퍼스케일러 capex 철회" in p            # 시장 공포가 렌즈 프롬프트에 컨텍스트로


def test_run_frame_pass_generates_market_frame(monkeypatch):
    from newsstore.enrich.frames import MARKET_ID
    monkeypatch.delenv("NEWSSTORE_FRAME_MIN_AGE_HOURS", raising=False)
    # _market 프레임이 렌즈 프레임보다 먼저 생성·저장된다(전 렌즈 스토리 기반, 1콜).
    llm = _LLM(frame_resp={"risks": [{"id": "m1", "text": "시장 공포"}], "premiums": [], "watchpoints": []},
               review_resp={"passed": True})
    store = _Store()
    run_frame_pass(store, llm, lens_ids=["kr_equity"], now=NOW)
    assert MARKET_ID in store.saved                    # 시장 프레임 저장됨
    assert store.saved[MARKET_ID]["risks"][0]["text"] == "시장 공포"


def test_run_frame_pass_market_folds_context_stories(monkeypatch):
    # #2 fold-in: 비자산(us_policy) 스토리가 시장 프레임 생성 입력에 녹되(자산 프레임으로 흐름),
    # 개별 프레임은 자산(kr_equity)만 생성. 정치·정책 렌즈 개별 프레임은 안 만든다.
    from newsstore.enrich.frames import MARKET_ID
    monkeypatch.delenv("NEWSSTORE_FRAME_MIN_AGE_HOURS", raising=False)

    class _PerLens:
        def __init__(self): self.saved = {}
        def get_frame(self, lens_id): return {}
        def save_frame(self, lens_id, frame, *, now): self.saved[lens_id] = frame
        def get_stories_for_report(self, lens_id, cutoff):
            return {"kr_equity": [{"id": "eq1", "title": "삼성", "summary": "x"}],
                    "us_policy": [{"id": "pol1", "title": "트럼프 관세", "summary": "x"}]}.get(lens_id, [])

    llm = _LLM(frame_resp={"risks": [{"id": "m1", "text": "공포"}], "premiums": [], "watchpoints": []},
               review_resp={"passed": True})
    store = _PerLens()
    run_frame_pass(store, llm, lens_ids=["kr_equity"], now=NOW,
                   context_lens_ids=["kr_equity", "us_policy"])
    assert any("pol1" in c for c in llm.calls)         # 정치 스토리가 시장 프레임 입력에 녹음
    assert MARKET_ID in store.saved and "kr_equity" in store.saved
    assert "us_policy" not in store.saved              # 정치 렌즈 개별 프레임은 안 만듦


def test_run_frame_pass_age_gate_skips_fresh(monkeypatch):
    # 6a age-gate: updated_at이 신선하면(min_age 이내) generate_json 0콜로 스킵 — #45 완화.
    monkeypatch.setenv("NEWSSTORE_FRAME_MIN_AGE_HOURS", "20")
    from newsstore.enrich.frames import MARKET_ID
    fresh = {"risks": [{"id": "r1", "text": "신선"}], "premiums": [], "watchpoints": [],
             "updated_at": NOW - __import__("datetime").timedelta(hours=1)}
    llm = _LLM(frame_resp={"risks": [], "premiums": [], "watchpoints": []},
               review_resp={"passed": True})
    store = _Store({"fx": fresh, MARKET_ID: fresh})   # 렌즈·시장 프레임 모두 신선
    n = run_frame_pass(store, llm, lens_ids=["fx"], now=NOW)
    assert n == 0 and len(llm.calls) == 0            # 전부 신선 → 콜 0(불변식, 매직넘버 없음)
    assert "fx" not in store.saved
    # 낡은(updated_at 없음) 프레임은 정상 재심
    llm2 = _LLM(frame_resp={"risks": [{"id": "r1", "text": "새"}], "premiums": [], "watchpoints": []},
                review_resp={"passed": True})
    store2 = _Store({"fx": {"risks": [], "premiums": [], "watchpoints": []}})
    assert run_frame_pass(store2, llm2, lens_ids=["fx"], now=NOW) == 1 and len(llm2.calls) >= 1


def test_run_frame_pass_no_diff_skips_review():
    same = {"risks": [{"id": "r1", "text": "동일"}], "premiums": [], "watchpoints": []}
    llm = _LLM(frame_resp=same, review_resp={"passed": False})   # 리뷰가 불려도 False지만
    store = _Store({"fx": same})
    run_frame_pass(store, llm, lens_ids=["fx"], now=NOW)
    assert "fx" in store.saved                          # diff 없음 → 리뷰 0콜 → 저장(updated_at 갱신)
    assert sum("심사" in c for c in llm.calls) == 0


def test_frame_prompt_includes_reject_notes():
    # 재시도: 직전 기각 사유(reject_notes)를 프롬프트에 실어 워커가 재작성하게 한다.
    p = build_frame_prompt("kr_equity", OLD, STORIES, reject_notes="근거 부족")
    assert "근거 부족" in p
    p0 = build_frame_prompt("kr_equity", OLD, STORIES)   # 기본값 None → 재작성 지시 없음
    assert "근거 부족" not in p0


# 재시도 fake — 프롬프트 마커로 분기: 리뷰='심사', 재생성 프롬프트는 기각 사유(NOTES)를 담는다.
_FRESH_MARKET = {"risks": [], "premiums": [], "watchpoints": [],
                 "updated_at": NOW - timedelta(hours=1)}   # age-gate로 시장 프레임 재생성 스킵


def test_run_frame_pass_retries_once_on_review_reject_then_saves():
    from newsstore.enrich.frames import MARKET_ID
    NOTES = "무근거단정-XYZ"
    gen1 = {"risks": [{"id": "r9", "text": "1차 무근거"}], "premiums": [], "watchpoints": []}
    gen2 = {"risks": [{"id": "r9", "text": "2차 근거보강"}], "premiums": [], "watchpoints": []}

    class _RetryLLM:
        def __init__(self):
            self.gen_calls, self.review_calls = [], []
        def generate_json(self, prompt, *, timeout=30.0, model=None):
            if "심사" in prompt:
                self.review_calls.append(prompt)
                return ({"passed": False, "notes": NOTES} if len(self.review_calls) == 1
                        else {"passed": True, "notes": ""})
            self.gen_calls.append(prompt)
            return gen2 if NOTES in prompt else gen1   # 재생성 프롬프트=기각 사유 포함

    llm = _RetryLLM()
    old = {"risks": [{"id": "r1", "text": "어제"}], "premiums": [], "watchpoints": []}
    store = _Store({"fx": old, MARKET_ID: _FRESH_MARKET})
    n = run_frame_pass(store, llm, lens_ids=["fx"], now=NOW)
    # 재시도 성공 → 재생성분(gen2)이 저장(어제 판 아님, 1차 무근거 아님)
    assert n == 1 and store.saved["fx"]["risks"][0]["text"] == "2차 근거보강"
    # 불변식: 생성 2회(gen+regen)·리뷰 2회. 상한=1 → 3번째 생성 없음.
    assert len(llm.gen_calls) == 2 and len(llm.review_calls) == 2
    assert NOTES in llm.gen_calls[1]                     # 재생성 프롬프트에 기각 사유 실림


def test_run_frame_pass_retry_still_rejected_keeps_yesterday_no_third_gen():
    from newsstore.enrich.frames import MARKET_ID

    class _AlwaysReject:
        def __init__(self):
            self.gen_calls, self.review_calls = [], []
        def generate_json(self, prompt, *, timeout=30.0, model=None):
            if "심사" in prompt:
                self.review_calls.append(prompt)
                return {"passed": False, "notes": "여전히 무근거"}
            self.gen_calls.append(prompt)
            return {"risks": [{"id": "r9", "text": "무근거"}], "premiums": [], "watchpoints": []}

    llm = _AlwaysReject()
    old = {"risks": [{"id": "r1", "text": "어제"}], "premiums": [], "watchpoints": []}
    store = _Store({"fx": old, MARKET_ID: _FRESH_MARKET})
    n = run_frame_pass(store, llm, lens_ids=["fx"], now=NOW)
    assert n == 0 and "fx" not in store.saved           # 재시도도 기각 → 어제 판 유지
    # 상한=1: 생성 2회(gen+regen)에서 멈춤(3번째 없음), 리뷰 2회
    assert len(llm.gen_calls) == 2 and len(llm.review_calls) == 2


def test_run_frame_pass_retry_llm_error_falls_back():
    from newsstore.enrich.frames import MARKET_ID, LLMError
    gen1 = {"risks": [{"id": "r9", "text": "1차"}], "premiums": [], "watchpoints": []}

    class _RetryBoom:
        def __init__(self):
            self.gen_calls, self.review_calls = [], []
        def generate_json(self, prompt, *, timeout=30.0, model=None):
            if "심사" in prompt:
                self.review_calls.append(prompt)
                return {"passed": False, "notes": "기각"}
            self.gen_calls.append(prompt)
            if len(self.gen_calls) == 1:
                return gen1
            raise LLMError("regen down")                # 재생성 콜 실패 → 폴백(전파 금지)

    llm = _RetryBoom()
    old = {"risks": [{"id": "r1", "text": "어제"}], "premiums": [], "watchpoints": []}
    store = _Store({"fx": old, MARKET_ID: _FRESH_MARKET})
    n = run_frame_pass(store, llm, lens_ids=["fx"], now=NOW)   # 예외 전파 없이 완료
    assert n == 0 and "fx" not in store.saved           # 재시도 콜 실패 → 어제 판 유지(fail-soft)
    assert len(llm.gen_calls) == 2                       # 재시도 1회 시도(3번째 없음)
