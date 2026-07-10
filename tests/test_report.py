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


def test_saga_aware_ranking_lifts_split_fragment():
    # 과소병합 만회: 같은 사가 조각(개체 다수 공유+시간 근접)의 impact를 그룹 최대로 lift해
    # 갈린 사가가 조각이라 top-K에서 밀리지 않게. LLM 0·결정론·표시 무변경.
    from newsstore.enrich.report import saga_impact, _same_saga, select_top_k
    A = {"id": "a", "impact": 1, "entities": ["FOMC", "연준", "금리"],
         "developments": [{"delta_time": NOW}], "lenses": ["us_rates"]}
    B = {"id": "b", "impact": 5, "entities": ["FOMC", "연준", "의사록"],
         "developments": [{"delta_time": NOW}], "lenses": ["us_rates"]}
    U = {"id": "u", "impact": 2, "entities": ["엔비디아", "실적"],
         "developments": [{"delta_time": NOW}], "lenses": ["us_rates"]}
    assert _same_saga(A, B)                             # FOMC·연준 공유(Jaccard 2/4=0.5)+동시간 → 사가
    assert not _same_saga(A, U)                         # 개체 무공유 → 아님
    eff = saga_impact([A, B, U], NOW)
    assert eff["a"] == 5.0 and eff["b"] == 5.0          # 조각 A가 그룹 최대(5)로 lift
    assert eff["u"] == 2.0                              # 무관은 자기 impact
    top_ids = [s["id"] for s in select_top_k([A, B, U], NOW, stratify=False)]
    assert "a" in top_ids and "b" in top_ids           # 갈린 사가 둘 다 top-K


def test_same_saga_conservative_no_generic_overlink():
    # 제네릭 단일 개체 공유(예 '미국')로는 안 묶여야 한다(과연결 방지 — Jaccard 임계).
    from newsstore.enrich.report import _same_saga
    C = {"id": "c", "impact": 9, "entities": ["미국", "호르무즈", "이란", "유가"],
         "developments": [{"delta_time": NOW}]}
    D = {"id": "d", "impact": 1, "entities": ["미국", "반도체", "삼성"],
         "developments": [{"delta_time": NOW}]}
    assert not _same_saga(C, D)                         # '미국'만 공유 Jaccard 1/6 < 0.5 → 안 묶임


from newsstore.enrich.report import (validate_report, build_section_prompt, build_backdrop_prompt,
                                     build_review_prompt, price_context)

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


def test_price_context_format_and_empty():
    p = {"label": "원/달러", "close": 1520.0, "percent_change": -0.78, "symbol": "KRW=X",
         "series": [{"t": "d1", "c": 1555}, {"t": "d2", "c": 1540}, {"t": "d3", "c": 1530},
                    {"t": "d4", "c": 1525}, {"t": "d5", "c": 1520}]}
    ctx = price_context(p)
    assert "원/달러" in ctx and "1520" in ctx and "-0.78%" in ctx and "하락" in ctx   # 추세 방향
    assert price_context(None) == "" and price_context({}) == "" and price_context({"close": None}) == ""


def test_section_prompt_price_crosscheck_rule():
    # 뉴스 지연 보정: 가격 주입 시 교차검증 규칙 명시(뉴스 vs 가격 어긋나면 가격 우선).
    story = [{"id": "s1", "title": "t", "summary": "x"}]
    p = build_section_prompt("fx", FRAME, story, "", price_ctx="원/달러 1520 (전일 -0.78%)")
    assert "원/달러 1520" in p and "가격 교차검증" in p
    assert "지연" in p and "우선 근거" in p
    assert "가격 교차검증" not in build_section_prompt("fx", FRAME, story, "")   # 가격 없으면 규칙 없음


def test_review_prompt_accepts_price_as_source():
    # 리뷰어도 가격을 출처③으로 인정 — 가격 기반 현재상태 서술을 날조로 오탐하지 않게.
    p = build_review_prompt({"headline": "h", "lead": "l", "sections": []},
                            [{"id": "s1", "title": "t", "summary": "x"}], frame=FRAME,
                            price_ctx="원/달러 1520 (전일 -0.78%)")
    assert "원/달러 1520" in p and "출처③" in p


def test_run_report_pass_injects_price_ctx_into_section():
    store = _Store({"fx": _stories()}, {"fx": FRAME})
    seen = {}

    class _Cap(_LLM):
        def generate_json(self, prompt, *, timeout=30.0, model=None):
            if "데일리 리포트 에디터" in prompt:
                seen["section"] = prompt
            return super().generate_json(prompt, timeout=timeout, model=model)

    run_report_pass(store, _Cap(SECTION_OK, {"passed": True, "notes": ""}),
                    lens_ids=["fx"], now=NOW, price_ctx_by_lens={"fx": "원/달러 1520 (전일 -0.78%)"})
    assert "원/달러 1520" in seen["section"] and "가격 교차검증" in seen["section"]


def test_section_prompt_narrative_weighting_not_chronological():
    # 서사 구조: 전개는 시간순 arc(근거)로 보여주되, 출력은 현재상태 가중·시간순 나열 금지.
    from datetime import timedelta
    t0 = NOW - timedelta(days=2)
    story = {"id": "s1", "title": "원달러", "summary": "환율",
             "developments": [{"text": "1550원 급등", "delta_time": t0},
                              {"text": "1239원으로 진정", "delta_time": t0 + timedelta(days=1)}]}
    p = build_section_prompt("fx", FRAME, [story], "")
    assert p.index("1550원 급등") < p.index("1239원으로 진정")     # 입력 arc는 오래된→최신
    assert "서사 구조" in p and "나열" in p                        # 시간순 나열 금지
    assert ("negate" in p or "무효화" in p) and "가중치" in p      # 무효화 강등 + 현재 가중


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


def test_run_report_pass_attributes_silent_stale_failure_to_lens():
    # IB3: LLM 생성 실패(silent-stale)를 lens_id와 함께 _failures에 귀속 발행(_skips 옆).
    store = _Store({"kr_equity": _stories()}, {"kr_equity": FRAME})
    store.reports["kr_equity"] = {"headline": "옛것"}
    class _Boom:
        def generate_json(self, prompt, *, timeout=30.0, model=None):
            if "심사자" in prompt:
                return {"passed": True, "notes": ""}
            if "데스크 에디터" in prompt:
                return {"text": "bd"}
            from newsstore.enrich.gemini import LLMError
            raise LLMError("down")                        # 섹션 생성 콜만 실패
    run_report_pass(store, _Boom(), lens_ids=["kr_equity"], now=NOW)
    fails = store.reports["_failures"]["lenses"]
    assert [f["lens_id"] for f in fails] == ["kr_equity"]
    assert fails[0]["reason"] == "failed_llm"
    assert store.reports["kr_equity"]["headline"] == "옛것"   # 기존 유지(silent-stale)


def test_run_report_pass_validation_failure_attributed():
    # 결정론 검증 실패도 silent-stale로 귀속(reason=failed_validation).
    store = _Store({"kr_equity": _stories()}, {"kr_equity": FRAME})
    class _BadSection(_LLM):
        def generate_json(self, prompt, *, timeout=30.0, model=None):
            if "심사자" in prompt:
                return {"passed": True, "notes": ""}
            if "데스크 에디터" in prompt:
                return {"text": "bd"}
            return {"headline": "", "lead": "x", "sections": []}   # validate_report → None
    run_report_pass(store, _BadSection(SECTION_OK, {"passed": True}), lens_ids=["kr_equity"], now=NOW)
    fails = store.reports["_failures"]["lenses"]
    assert [f["lens_id"] for f in fails] == ["kr_equity"] and fails[0]["reason"] == "failed_validation"


def test_run_report_pass_review_reject_not_in_failures():
    # 리뷰 기각은 fresh doc+배지로 저장되므로 silent-stale 아님 → _failures에 없다(귀속 제외).
    store = _Store({"kr_equity": _stories()}, {"kr_equity": FRAME})
    llm = _LLM(SECTION_OK, {"passed": False, "notes": "과인용"})
    run_report_pass(store, llm, lens_ids=["kr_equity"], now=NOW)
    assert store.reports["_failures"]["lenses"] == []         # 기각은 실패 귀속 아님
    assert store.reports["kr_equity"]["review"]["passed"] is False   # 배지로 표면화됨


def test_run_report_pass_success_publishes_empty_failures():
    store = _Store({"kr_equity": _stories()}, {"kr_equity": FRAME})
    llm = _LLM(SECTION_OK, {"passed": True, "notes": ""})
    run_report_pass(store, llm, lens_ids=["kr_equity"], now=NOW)
    assert store.reports["_failures"]["lenses"] == []         # 멱등 빈 발행


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


# ── divergence 배지(A1) ──
from newsstore.enrich.report import (frame_lean, divergence, conviction,
                                     _triggered_signals, DIVERGENCE_DEADBAND_DEFAULT)


def _price(pts, pct=None):
    d = {"series": [{"t": f"d{i}", "c": c} for i, c in enumerate(pts)]}
    if pct is not None:
        d["percent_change"] = pct
    return d


def test_frame_lean_is_premium_minus_risk_count():
    assert frame_lean({"premiums": [1, 2], "risks": [1]}) == 1
    assert frame_lean({"premiums": [], "risks": [1, 2]}) == -2
    assert frame_lean({}) == 0                       # 빈 프레임 → 0(중립)


def test_divergence_over_fear_when_fear_but_price_not_falling():
    # lean<0(공포 우세) + 최근 추세 상승/무반응(≥ −ε) → over_fear(뉴스 공포인데 가격 미반영)
    frame = {"risks": [{"id": "r1"}, {"id": "r2"}], "premiums": []}
    d = divergence(frame, _price([100, 101, 102]), "usdkrw", deadband=0.3)
    assert d["kind"] == "over_fear" and d["price_key"] == "usdkrw"
    assert "단정 아님" in d["note"]                  # 재료 어투(판정 금지)


def test_divergence_aligned_when_fear_and_price_falls():
    frame = {"risks": [{"id": "r1"}, {"id": "r2"}], "premiums": []}
    d = divergence(frame, _price([102, 100, 98]), "usdkrw", deadband=0.3)
    assert d["kind"] == "aligned"


def test_divergence_over_hope_when_hope_but_price_not_rising():
    frame = {"premiums": [{"id": "p1"}, {"id": "p2"}], "risks": []}
    d = divergence(frame, _price([100, 99, 100]), "sp500", deadband=0.3)
    assert d["kind"] == "over_hope"


def test_divergence_deadband_boundary_is_inclusive():
    # direction=(last-first)/|first|*100. 정확히 −ε는 over_fear(경계 포함), ε 밖 하락은 aligned.
    frame = {"risks": [{"id": "r1"}], "premiums": []}
    assert divergence(frame, _price([100, 99.7]), "x", deadband=0.3)["kind"] == "over_fear"  # −0.3 ≥ −0.3
    assert divergence(frame, _price([100, 99.6]), "x", deadband=0.3)["kind"] == "aligned"    # −0.4 < −0.3


def test_divergence_none_when_lean_zero_or_no_price():
    lean0 = {"risks": [{"id": "r1"}], "premiums": [{"id": "p1"}]}
    assert divergence(lean0, _price([100, 101]), "x", deadband=0.3) is None
    fear = {"risks": [{"id": "r1"}], "premiums": []}
    assert divergence(fear, None, "x", deadband=0.3) is None                # 가격 없음
    assert divergence(fear, _price([100, 101]), None, deadband=0.3) is None  # 가격키 없음


def test_divergence_series_trend_preferred_over_percent_change():
    # series 추세(상승)가 단일일 percent_change(하락)보다 우선 — 누적 센티먼트 시점 스케일 정합.
    fear = {"risks": [{"id": "r1"}], "premiums": []}
    d = divergence(fear, _price([100, 101, 103], pct=-0.5), "x", deadband=0.3)
    assert d["kind"] == "over_fear"                  # 추세 상승 → 안 빠짐


def test_divergence_percent_change_fallback_when_no_series():
    fear = {"risks": [{"id": "r1"}], "premiums": []}
    d = divergence(fear, {"percent_change": 0.5}, "x", deadband=0.3)   # series 없음 → pct 폴백
    assert d["kind"] == "over_fear" and d["price_pct"] == 0.5


def test_divergence_note_has_no_trend_contradiction_within_deadband():
    # 리뷰 지적: over_fear인데 추세가 살짝 하락(deadband 안)이면 '안 빠짐(하락)' 모순이 났다.
    # deadband 상대 3분(보합)으로 over_fear는 '하락'을, over_hope는 '상승'을 안 만든다.
    fear = {"risks": [{"id": "r1"}], "premiums": []}
    d = divergence(fear, _price([100, 99.7]), "x", deadband=0.3)   # 추세 −0.3%(경계=보합)
    assert d["kind"] == "over_fear" and "하락" not in d["note"] and "보합" in d["note"]
    hope = {"premiums": [{"id": "p1"}], "risks": []}
    d2 = divergence(hope, _price([100, 100.2]), "x", deadband=0.3)  # 추세 +0.2%(보합)
    assert d2["kind"] == "over_hope" and "상승" not in d2["note"] and "보합" in d2["note"]


def test_divergence_note_discloses_when_price_pct_is_trend_not_prior_day():
    # pct 없어 price_pct가 '추세 %'로 대체되면 note가 그 출처를 노출(전일 등락으로 오해 금지).
    fear = {"risks": [{"id": "r1"}], "premiums": []}
    d = divergence(fear, _price([100, 101, 102]), "x", deadband=0.3)   # series만, pct 없음
    assert "전일 등락 데이터 없" in d["note"] and d["price_pct"] == 2.0


def test_divergence_price_pct_is_prior_day_change_per_schema():
    fear = {"risks": [{"id": "r1"}], "premiums": []}
    d = divergence(fear, _price([100, 102], pct=-0.78), "usdkrw", deadband=0.3)
    assert d["price_pct"] == -0.78                    # 스키마: price_pct = 전일 등락%
    assert "전일 등락" in d["note"]                   # 추세로 분류하되 전일 등락도 노출(투명성)


# ── conviction 등급(A2) ──
def test_triggered_signals_count_unique_citations_and_poles():
    report = {"sections": [
        {"name": "risk_triggered", "items": [
            {"text": "a", "story_ids": ["s1", "s2"], "pole_id": "r1"},
            {"text": "b", "story_ids": ["s1"], "pole_id": None}]},
        {"name": "premium_triggered", "items": [
            {"text": "c", "story_ids": ["s3"], "pole_id": "p1"}]},
        {"name": "not_triggered", "items": [
            {"text": "d", "story_ids": ["s9"], "pole_id": "w1"}]}]}
    c, p = _triggered_signals(report)
    assert c == 3                                    # s1,s2,s3 (not_triggered s9 제외)
    assert p == 2                                    # r1, p1 (pole None 제외)


def test_conviction_c_zero_forces_low():
    assert conviction(0, 5, 2)["level"] == "low"     # 인용 없으면 강제 low


def test_conviction_high_needs_first_pass_pole_and_two_citations():
    assert conviction(2, 1, 2)["level"] == "high"
    assert conviction(1, 1, 2)["level"] == "medium"  # c<2
    assert conviction(2, 0, 2)["level"] == "medium"  # p<1
    assert conviction(2, 1, 1)["level"] == "medium"  # 재작업 통과(r<2)


def test_conviction_is_monotonic_in_each_signal():
    # 계약=단조성: c/p/r 어느 것이 늘어도 등급이 낮아지지 않는다(정확한 컷 아님).
    order = {"low": 0, "medium": 1, "high": 2}
    for c in range(4):
        for p in range(4):
            for r in range(3):
                base = order[conviction(c, p, r)["level"]]
                assert order[conviction(c + 1, p, r)["level"]] >= base
                assert order[conviction(c, p + 1, r)["level"]] >= base
                if r < 2:
                    assert order[conviction(c, p, r + 1)["level"]] >= base


def test_conviction_basis_flags_coarse_signal():
    b = conviction(2, 1, 1)["basis"]
    assert "재작업" in b and ("거친" in b or "단조" in b)   # 프록시임을 basis에 노출


def test_run_report_pass_attaches_conviction():
    store = _Store({"kr_equity": _stories()}, {"kr_equity": FRAME})
    llm = _LLM(SECTION_OK, {"passed": True, "notes": ""})
    run_report_pass(store, llm, lens_ids=["kr_equity"], now=NOW)
    conv = store.reports["kr_equity"]["conviction"]
    assert conv["level"] in ("high", "medium", "low") and conv["basis"]


def test_run_report_pass_attaches_divergence_when_price_maps():
    fear = {"risks": [{"id": "r1"}, {"id": "r2"}], "premiums": []}   # lean<0
    store = _Store({"fx": _stories()}, {"fx": fear})
    llm = _LLM(SECTION_OK, {"passed": True, "notes": ""})
    run_report_pass(store, llm, lens_ids=["fx"], now=NOW,
                    price_by_lens={"fx": {"key": "usdkrw",
                                          "doc": {"series": [{"c": 100}, {"c": 102}]}}})
    d = store.reports["fx"]["divergence"]
    assert d["kind"] == "over_fear" and d["price_key"] == "usdkrw"


def test_run_report_pass_omits_divergence_without_price():
    store = _Store({"kr_equity": _stories()}, {"kr_equity": FRAME})   # price_by_lens 미전달
    llm = _LLM(SECTION_OK, {"passed": True, "notes": ""})
    run_report_pass(store, llm, lens_ids=["kr_equity"], now=NOW)
    assert "divergence" not in store.reports["kr_equity"]


# ── WB1: 문장 경계 컷(산문 항목 text·lead 중간 절단 제거) ──
from newsstore.enrich.report import _sentence_cut, MAX_ITEM_TEXT, MAX_LEAD, MAX_LEAD_BULLETS


def test_sentence_cut_preserves_complete_short_text():
    s = "단기 FX 스와프가 확대됐다."
    assert _sentence_cut(s, MAX_ITEM_TEXT) == s          # cap 이하 완결문은 그대로 보존


def test_sentence_cut_never_exceeds_cap_and_cuts_at_sentence_boundary():
    a = "코스피가 상승했다. " * 40                        # cap 초과 산문
    out = _sentence_cut(a, 50)
    assert len(out) <= 50                                # cap 상한 유지(토큰폭탄 방어)
    assert out.endswith(".")                             # 문장 종결부호에서 컷(중간 절단 아님)
    assert "코스피가 상승했다." in out


def test_sentence_cut_middot_is_not_a_boundary():
    # 가운뎃점 ·은 병렬 구분자 — 경계로 쓰면 "반도체·"처럼 절단된다. 경계 아님.
    s = "반도체·전력·자동차 업종이 동반 강세를 보이며 지수를 끌어올렸다는 평가가 나온다"
    out = _sentence_cut(s, 12)
    assert out and out[-1] != "·"                        # 구분자로 끝나지 않음


def test_sentence_cut_falls_back_to_word_boundary_not_mid_token():
    # 문장 경계가 cap 안에 없으면 마지막 공백(단어 경계)에서 — 조사·단어 중간 절단 금지.
    s = "최근 5일간 코스피 지수가 큰 폭으로 하락하면서 투자심리가 급격히 위축되었다"
    out = _sentence_cut(s, 15)
    assert " " in s and not out.endswith(" ")            # 열린 채로 끝나지 않음
    assert out == out.strip() and out
    assert s.startswith(out)                             # 원문의 접두(마지막 어절 온전)


def test_sentence_cut_does_not_end_with_open_bracket_or_separator():
    s = "지수는 강세를 보였고 (특히 반도체 " * 5
    out = _sentence_cut(s, 20)
    assert out[-1] not in "([{（·,;:"                    # 열린 괄호·구분자로 끝나지 않음


def test_sentence_cut_decimal_point_is_not_a_boundary():
    # ASCII 마침표가 숫자 사이(소수점·버전)면 경계 아님 — '3.5%'가 '3.'로 손상되면 안 된다.
    s = "매출은 3.5% 늘었지만 비용도 크게 증가하여 수익성은 오히려 악화되었다는 분석이다"
    out = _sentence_cut(s, 9)
    assert "3.5" in out and not out.endswith("3.")        # 소수점에서 자르지 않음
    assert out and out[-1] != "."                         # 숫자 소수점을 종결로 오인하지 않음


def test_sentence_cut_newline_boundary_does_not_expose_trailing_separator():
    # 종결 경계가 줄바꿈이라도 결과가 구분자·열린 괄호로 끝나지 않는다(폴백 트림을 모든 경로에).
    assert _sentence_cut("가·\n나 다 라 마 바 사", 5)[-1] != "·"
    assert _sentence_cut("(\n반도체 전력 자동차 산업", 4)[-1] not in "([{（"


def test_sentence_cut_hardcut_when_no_boundary_no_space():
    # 무경계·무공백 초장문 → cap 하드컷(예외 경로). 여전히 구분자로 끝나지 않고 cap 이내.
    s = "가나다라마바사아자차카타파하" * 5                 # 공백·종결부호 없음
    out = _sentence_cut(s, 7)
    assert len(out) <= 7 and out and out[-1] != "·"


def test_sentence_cut_empty_and_nonstring_defensive():
    assert _sentence_cut("", MAX_ITEM_TEXT) == ""
    assert _sentence_cut(None, MAX_ITEM_TEXT) == ""      # 실 SDK None 방어


def test_headline_is_not_boundary_cut_but_hard_sliced():
    # WB1 스코프: headline(명사구 제목)은 경계 컷 제외 — 종결부호 없어 경계룰이 오히려 잘못 자른다.
    # 긴 명사구 제목은 하드 슬라이스(MAX_HEADLINE)로 유지된다(경계 컷으로 빈/절단 제목 방지).
    from newsstore.enrich.report import MAX_HEADLINE
    long_head = "삼성·SK·마이크론 반도체 훈풍 " * 20            # 종결부호 없는 긴 명사구
    v = validate_report({**GOOD, "headline": long_head}, frame=FRAME, input_story_ids={"s1"})
    assert v["headline"] == long_head.strip()[:MAX_HEADLINE]   # 하드 슬라이스(경계 컷 아님)


def test_validate_report_item_text_gets_sentence_cut():
    long_text = "MS가 capex 재검토를 시사했다. " * 40    # cap 초과 산문 항목
    raw = {**GOOD, "sections": [
        {"name": "risk_triggered", "items": [
            {"text": long_text, "story_ids": ["s1"], "pole_id": "r1"}]}]}
    v = validate_report(raw, frame=FRAME, input_story_ids={"s1"})
    txt = v["sections"][0]["items"][0]["text"]
    assert len(txt) <= MAX_ITEM_TEXT and txt.endswith(".")   # 경계 컷(중간 절단 아님)


# ── WB2: 리드 = 핵심 합성 불릿 문자열 배열(≤3) ──
def test_validate_report_lead_is_bounded_string_array():
    raw = {**GOOD, "lead": ["현재 원화 약세가 이어진다.", "다만 당국 개입 경계가 반전 요인이다.",
                            "3분기 수급이 관건이다.", "넷째 불릿은 상한 초과."]}
    v = validate_report(raw, frame=FRAME, input_story_ids={"s1"})
    assert isinstance(v["lead"], list)
    assert 1 <= len(v["lead"]) <= MAX_LEAD_BULLETS       # 상한 불변식(매직넘버 아님)
    assert all(isinstance(x, str) and x.strip() for x in v["lead"])


def test_validate_report_lead_string_backward_compat_coerced_to_array():
    # 구형(문자열) 리드도 graceful 코어스 — 배포 순서 무관.
    v = validate_report({**GOOD, "lead": "핵심 요약 문장이다."}, frame=FRAME, input_story_ids={"s1"})
    assert v["lead"] == ["핵심 요약 문장이다."]


def test_validate_report_rejects_empty_lead_array():
    assert validate_report({**GOOD, "lead": []}, frame=FRAME, input_story_ids={"s1"}) is None
    assert validate_report({**GOOD, "lead": ["", "  "]}, frame=FRAME, input_story_ids={"s1"}) is None
    assert validate_report({**GOOD, "lead": None}, frame=FRAME, input_story_ids={"s1"}) is None


def test_validate_report_lead_list_skips_non_string_elements():
    # 리드 배열에 비문자열(None·숫자·dict)이 섞여도 안전하게 드롭하고 문자열만 남긴다.
    raw = {**GOOD, "lead": [None, 123, {"x": 1}, "유효한 불릿이다."]}
    v = validate_report(raw, frame=FRAME, input_story_ids={"s1"})
    assert v["lead"] == ["유효한 불릿이다."]


def test_validate_report_lead_bullets_get_sentence_cut():
    long_bullet = "코스피가 상승했다. " * 40
    v = validate_report({**GOOD, "lead": [long_bullet]}, frame=FRAME, input_story_ids={"s1"})
    assert len(v["lead"][0]) <= MAX_LEAD and v["lead"][0].endswith(".")   # 문장 경계 컷


def test_section_prompt_asks_lead_as_synthesis_bullets():
    p = build_section_prompt("kr_equity", FRAME,
                             [{"id": "s1", "title": "t", "summary": "s"}], "bd")
    assert "재요약" in p                                 # 섹션 항목 재요약 금지 지시
    assert "완결된 문장" in p                            # WB1 예산 내 완결 문장 지시
    assert '"lead":[' in p                               # JSON 템플릿이 배열


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
