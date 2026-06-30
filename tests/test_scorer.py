from newsstore.enrich import topics
from newsstore.enrich.scorer import (validate_score, should_score, score_story,
                                     SCORE_MIN, SCORE_MAX, MATERIALITY_MIN_MEMBERS)

T = topics.load_topics()


# ── validator (결정론, 범위·필수키) ──
def test_validate_in_range_keeps_scores():
    v = validate_score({"risk": 2, "impact": 3, "risk_reason": "war", "impact_reason": "oil"})
    assert v == {"risk": 2, "impact": 3, "risk_reason": "war", "impact_reason": "oil"}


def test_validate_out_of_range_drops():
    assert validate_score({"risk": SCORE_MAX + 1, "impact": 1}) is None
    assert validate_score({"risk": SCORE_MIN - 1, "impact": 1}) is None
    assert validate_score({"risk": 1}) is None                    # impact 결측
    assert validate_score({"risk": "high", "impact": 1}) is None  # 비정수
    assert validate_score({"risk": True, "impact": 1}) is None    # bool 거부(정수 아님)
    assert validate_score(None) is None


def test_validate_reason_advisory_optional():
    v = validate_score({"risk": 0, "impact": 0})        # reason 결측 → 빈문자열, 점수 보존
    assert v["risk"] == SCORE_MIN and v["impact"] == SCORE_MIN
    assert v["risk_reason"] == "" and v["impact_reason"] == ""


def test_validate_reason_truncated():
    v = validate_score({"risk": 1, "impact": 1, "risk_reason": "x" * 9999})
    assert len(v["risk_reason"]) <= 200


# ── type-aware 게이트 ──
def test_gate_standing_watch_always():
    assert should_score(["kr_rates"], T, count=1) is True         # standing 멤버 1
    assert should_score(["watch_samsung"], T, count=1) is True    # watch 멤버 1


def test_gate_nonfinancial_needs_min_members():
    assert should_score(["kr_econ"], T, count=1) is False         # development 1 → 차단
    assert should_score(["kr_econ"], T, count=MATERIALITY_MIN_MEMBERS) is True
    assert should_score(["risk"], T, count=1) is False
    assert should_score(["sector_tech"], T, count=1) is False     # sector = 게이트
    assert should_score([], T, count=1) is False                  # emergent 무렌즈
    assert should_score([], T, count=MATERIALITY_MIN_MEMBERS) is True


def test_gate_mixed_financial_wins():
    assert should_score(["kr_econ", "watch_samsung"], T, count=1) is True
    assert should_score(["sector_tech", "kr_equity"], T, count=1) is True


def test_gate_unknown_id_demoted_to_emergent():
    assert should_score(["NOT_A_LENS"], T, count=1) is False      # KeyError 안 남, 보수 차단
    assert should_score(["NOT_A_LENS"], T, count=MATERIALITY_MIN_MEMBERS) is True


# ── score_story (입력 구성 + fail-soft) ──
class _FakeLLM:
    def __init__(self, resp):
        self.resp, self.seen = resp, None

    def generate_json(self, prompt, *, timeout=30.0):
        self.seen = prompt
        return self.resp


def test_score_story_uses_summary():
    llm = _FakeLLM({"risk": 2, "impact": 1, "risk_reason": "r", "impact_reason": "i"})
    out = score_story({"title": "Hormuz", "summary": "tanker strike", "developments": []},
                      members=None, client=llm)
    assert out["risk"] == 2 and out["impact"] == 1
    assert "tanker strike" in llm.seen


def test_score_story_member_fallback():
    llm = _FakeLLM({"risk": 0, "impact": 0})
    out = score_story({"title": "t", "summary": "", "developments": []},
                      members=[{"title": "Fed hikes"}], client=llm)
    assert out["risk"] == 0 and "Fed hikes" in llm.seen


def test_score_story_empty_input_returns_none():
    llm = _FakeLLM({"risk": 1, "impact": 1})
    assert score_story({"title": "", "summary": "", "developments": []},
                       members=[], client=llm) is None     # 빈 입력 → 스킵(크래시 금지)


def test_score_story_failsoft_on_llm_error():
    from newsstore.enrich.gemini import LLMError

    class _Boom:
        def generate_json(self, prompt, *, timeout=30.0):
            raise LLMError("down")          # LLM 장애만 fail-soft
    out = score_story({"title": "x", "summary": "s", "developments": []},
                      members=None, client=_Boom())
    assert out is None


def test_score_story_drops_invalid_llm_output():
    llm = _FakeLLM({"risk": 99, "impact": 1})              # 범위 밖 → validator None
    assert score_story({"title": "x", "summary": "s", "developments": []},
                       members=None, client=llm) is None
