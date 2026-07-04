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


from newsstore.enrich.report import (validate_report, build_section_prompt, build_backdrop_prompt,
                                     build_review_prompt)

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
    # #1: 과인용(스토리에 없는 사실을 트리거 근거로 지어냄) 방지 — grounding 리뷰 기각의 주 원인
    assert "과인용" in p and "watchpoints" in p


def test_section_prompt_includes_developments():
    # #1 근본수정: 구체 사실은 스토리 developments(타임라인)에 있다 — 요약만 보면 근거를 못 본다.
    story = {"id": "s1", "title": "비트코인", "summary": "정부 매각",
             "developments": [{"text": "아일랜드 당국 누적 1,500 BTC 압수", "delta_time": NOW}]}
    p = build_section_prompt("crypto", FRAME, [story], "")
    assert "아일랜드 당국 누적 1,500 BTC 압수" in p   # 전개가 생성기 입력에 실림


def test_review_prompt_includes_frame_and_developments():
    # #1 근본수정: 리뷰어가 프레임(극 출처)과 스토리 전개를 받아야, 프레임 극을 restate한 항목을
    # '출처 없는 날조'로 오판하지 않는다(아일랜드 1,500 BTC = 프레임 watchpoint 극, 실제 사실).
    story = {"id": "s1", "title": "비트코인", "summary": "정부 매각",
             "developments": [{"text": "아일랜드 당국 누적 1,500 BTC 압수", "delta_time": NOW}]}
    rep = {"headline": "h", "lead": "l", "sections": []}
    p = build_review_prompt(rep, [story], frame=FRAME)
    assert "빅테크 capex 감속" in p                   # 프레임 극이 리뷰어 입력(출처로 인정)
    assert "HBM 수요" in p
    assert "아일랜드 당국 누적 1,500 BTC 압수" in p    # 스토리 전개가 리뷰어 입력
    assert "프레임" in p                              # 프레임을 출처로 인정하라는 지시


def test_review_prompt_backward_compat_no_frame():
    # 프레임 없이(백드롭 리뷰 등) 호출해도 동작(하위호환).
    p = build_review_prompt({"headline": "h", "lead": "l", "sections": []},
                            [{"id": "s1", "title": "t", "summary": "x"}])
    assert "심사자" in p


def test_section_prompt_survives_real_frame_with_datetime():
    # C1 회귀: 실 프레임은 save_frame이 심는 updated_at(datetime)을 포함한다 —
    # dict 통째 json.dumps면 TypeError로 잡 전체 사망. 3축만 추려 직렬화해야 한다.
    frame = {**FRAME, "updated_at": datetime(2026, 7, 4, 7, 0, tzinfo=timezone.utc)}
    p = build_section_prompt("kr_equity", frame,
                             [{"id": "s1", "title": "제목", "summary": "요약"}], "")
    assert isinstance(p, str)
    assert "빅테크 capex 감속" in p and "HBM 수요" in p and "메타 실적" in p   # 3축 전부 포함


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
    주의: '백드롭' 단어는 마커로 쓰지 않는다 — 백드롭 인자값이 섹션 프롬프트에 삽입될 수 있음)."""
    def __init__(self, section, review, backdrop='{"text": "bd"}'):
        import json
        self.section, self.review = section, review
        self.backdrop = json.loads(backdrop)
        self.n_review = 0
    def generate_json(self, prompt, *, timeout=30.0, model=None):
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


def test_run_report_pass_folds_context_stories_into_backdrop_only():
    # #2 fold-in: 비자산(us_policy) 스토리는 백드롭 입력엔 들어가되(자산 리포트로 녹음),
    # 리포트 문서는 자산(kr_equity)만 저장 — 정치·정책 리포트는 안 생긴다(#5/#6).
    store = _Store({"kr_equity": _stories(),
                    "us_policy": [_s("트럼프관세", lenses=("us_policy",)),
                                  _s("연준긴축", lenses=("us_policy",))]},
                   {"kr_equity": FRAME})
    seen = {}

    class _Cap(_LLM):
        def generate_json(self, prompt, *, timeout=30.0, model=None):
            if "데스크 에디터" in prompt:
                seen["backdrop"] = prompt
            return super().generate_json(prompt, timeout=timeout, model=model)

    run_report_pass(store, _Cap(SECTION_OK, {"passed": True, "notes": ""}),
                    lens_ids=["kr_equity"], now=NOW,
                    context_lens_ids=["kr_equity", "us_policy"])
    assert "트럼프관세" in seen["backdrop"]         # 정치 스토리가 백드롭(자산 리포트 입력)에 녹음
    assert "kr_equity" in store.reports              # 자산 리포트 저장
    assert "us_policy" not in store.reports          # 정치·정책 리포트는 안 생김


def test_run_report_pass_backdrop_review_reject_degrades():
    # 백드롭 리뷰 기각 → 서두 미저장 + 섹션 콜에 미주입(degrade — §5 표). 섹션은 계속 진행.
    class _RejBackdrop(_LLM):
        def generate_json(self, prompt, *, timeout=30.0, model=None):
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
    # M5: 스킵 신호 발행 — UI가 "아직 생성 전" vs "갱신 지연"을 구분(§4)
    assert store.reports["_skips"]["lenses"] == ["kr_equity"]


def test_run_report_pass_generation_failure_keeps_existing():
    store = _Store({"kr_equity": _stories()}, {"kr_equity": FRAME})
    store.reports["kr_equity"] = {"headline": "옛것"}
    class _Boom:
        def generate_json(self, prompt, *, timeout=30.0, model=None):
            if "심사자" in prompt:
                return {"passed": True, "notes": ""}
            if "데스크 에디터" in prompt:
                return {"text": "bd"}
            from newsstore.enrich.gemini import LLMError
            raise LLMError("down")                       # 섹션 생성 콜만 실패(§5(b) 경로 검증)
    run_report_pass(store, _Boom(), lens_ids=["kr_equity"], now=NOW)
    assert store.reports["kr_equity"]["headline"] == "옛것"    # §5(b) 기존 유지


def test_section_prompt_includes_reject_notes():
    # 재시도: 직전 리뷰 실패 사유(reject_notes)를 섹션 프롬프트에 실어 재작성하게 한다.
    p = build_section_prompt("kr_equity", FRAME,
                             [{"id": "s1", "title": "t", "summary": "s"}], "bd",
                             reject_notes="조언 포함")
    assert "조언 포함" in p
    p0 = build_section_prompt("kr_equity", FRAME,
                              [{"id": "s1", "title": "t", "summary": "s"}], "bd")  # 기본값 None
    assert "조언 포함" not in p0


# 재시도 fake — 리뷰 순서: 백드롭 grounding(1) → 섹션 리뷰1 → 섹션 리뷰2.
# 재생성 섹션은 기각 사유(NOTES)를 담은 프롬프트로 호출되므로 그걸로 분기.
_RETRY_NOTES = "과인용-ABC"
SECTION_IMPROVED = {"headline": "개선h", "lead": "개선l", "sections": [
    {"name": "risk_triggered", "items": [{"text": "보강", "story_ids": ["s0"], "pole_id": None}]}]}


def test_run_report_pass_retries_once_and_saves_improved():
    class _RetryLLM:
        def __init__(self):
            self.n_review, self.n_section = 0, 0
        def generate_json(self, prompt, *, timeout=30.0, model=None):
            if "심사자" in prompt:
                self.n_review += 1
                # 백드롭 리뷰(1) 통과 · 섹션 리뷰1(2) 기각 · 섹션 리뷰2(3) 통과
                return ({"passed": False, "notes": _RETRY_NOTES} if self.n_review == 2
                        else {"passed": True, "notes": ""})
            if "데스크 에디터" in prompt:
                return {"text": "bd"}
            self.n_section += 1
            return SECTION_IMPROVED if _RETRY_NOTES in prompt else SECTION_OK

    store = _Store({"kr_equity": _stories()}, {"kr_equity": FRAME})
    llm = _RetryLLM()
    run_report_pass(store, llm, lens_ids=["kr_equity"], now=NOW)
    r = store.reports["kr_equity"]
    assert r["headline"] == "개선h" and r["review"]["passed"] is True   # 재생성분으로 교체
    assert llm.n_section == 2                            # 상한=1: 생성+재생성, 3번째 없음


def test_run_report_pass_retry_still_rejected_keeps_first_with_badge():
    SECTION_REGEN = {"headline": "regen-h", "lead": "l", "sections": [
        {"name": "risk_triggered", "items": [{"text": "x", "story_ids": ["s0"], "pole_id": None}]}]}

    class _AlwaysRejectSection:
        def __init__(self):
            self.n_review, self.n_section = 0, 0
        def generate_json(self, prompt, *, timeout=30.0, model=None):
            if "심사자" in prompt:
                self.n_review += 1
                return ({"passed": True, "notes": ""} if self.n_review == 1     # 백드롭만 통과
                        else {"passed": False, "notes": "과인용"})
            if "데스크 에디터" in prompt:
                return {"text": "bd"}
            self.n_section += 1
            return SECTION_OK if self.n_section == 1 else SECTION_REGEN

    store = _Store({"kr_equity": _stories()}, {"kr_equity": FRAME})
    llm = _AlwaysRejectSection()
    run_report_pass(store, llm, lens_ids=["kr_equity"], now=NOW)
    r = store.reports["kr_equity"]
    assert r["review"]["passed"] is False and "과인용" in r["review"]["notes"]  # 배지 계약 유지
    assert r["headline"] == SECTION_OK["headline"]      # 기존(1차) v 저장 — 재생성분 아님
    assert llm.n_section == 2                            # 상한=1: 3번째 생성 없음


def test_run_report_pass_retry_llm_error_keeps_first():
    from newsstore.enrich.gemini import LLMError

    class _RetryBoom:
        def __init__(self):
            self.n_review, self.n_section = 0, 0
        def generate_json(self, prompt, *, timeout=30.0, model=None):
            if "심사자" in prompt:
                self.n_review += 1
                return {"passed": True, "notes": ""} if self.n_review == 1 else {"passed": False, "notes": "기각"}
            if "데스크 에디터" in prompt:
                return {"text": "bd"}
            self.n_section += 1
            if self.n_section == 1:
                return SECTION_OK
            raise LLMError("regen down")                # 재생성 콜 실패 → 폴백(기존 v 유지)

    store = _Store({"kr_equity": _stories()}, {"kr_equity": FRAME})
    llm = _RetryBoom()
    run_report_pass(store, llm, lens_ids=["kr_equity"], now=NOW)   # 예외 전파 없이 완료
    r = store.reports["kr_equity"]
    assert r["review"]["passed"] is False and r["headline"] == SECTION_OK["headline"]  # 기존 유지
    assert llm.n_section == 2                            # 재시도 1회 시도(3번째 없음)


def test_run_report_pass_generates_rising():
    # m8: 결정적 구성 — impact=3 fresh 15개가 top-K(=REPORT_MAX_STORIES)를 점유하고,
    # hot1·hot2(impact=1, 24h 델타 5건)는 top-K 밖 + 밀도 상위 → rising 무조건 생성.
    # SECTION_OK의 s0 인용은 rising 입력에 없어 validate가 드롭하지만 headline/lead만으로
    # 유효(트리거 항목 드롭 ≠ None) — 저장 자체를 무조건 단언한다.
    fillers = [_s(f"s{i}", impact=3, hours_ago=0) for i in range(15)]
    hots = [_s("hot1", ndev=5, impact=1), _s("hot2", ndev=5, impact=1)]
    store = _Store({"kr_equity": fillers + hots}, {"kr_equity": FRAME})
    llm = _LLM(SECTION_OK, {"passed": True, "notes": ""})
    run_report_pass(store, llm, lens_ids=["kr_equity"], now=NOW)
    assert "rising" in store.reports and store.reports["rising"]["criteria"]
