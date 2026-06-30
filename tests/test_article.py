from datetime import datetime, timezone, timedelta

from newsstore.enrich.article import (validate_article, compute_ref, article_story,
                                      build_article_input, MAX_BULLETS, MAX_HEADLINE,
                                      MAX_LEAD, MAX_BULLET_LEN, REF_WINDOW)

NOW = datetime(2026, 6, 29, 12, tzinfo=timezone.utc)


# ── validate_article ──
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


# ── compute_ref ──
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


# ── build_article_input ──
def test_build_input_prefers_summary_then_members():
    assert "tanker" in build_article_input({"summary": "tanker strike", "developments": []}, None)
    out = build_article_input({"summary": "", "developments": []}, [{"title": "Fed hikes"}])
    assert "Fed hikes" in out
    assert build_article_input({"summary": "", "developments": []}, []) == ""


# ── article_story (fail-soft + ref) ──
class _FakeLLM:
    def __init__(self, resp):
        self.resp, self.seen = resp, None

    def generate_json(self, prompt, *, timeout=30.0):
        self.seen = prompt
        return self.resp


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
    from newsstore.enrich.gemini import LLMError

    class _Boom:
        def generate_json(self, prompt, *, timeout=30.0):
            raise LLMError("down")          # LLM 장애만 fail-soft
    assert article_story({"title": "x", "summary": "s", "developments": []},
                         members=None, client=_Boom(), now=NOW) is None


def test_article_story_propagates_non_llm_bug():
    import pytest

    class _Bug:                             # 코드 버그(비-LLMError)는 삼키지 말고 전파(FAIL-LOUD)
        def generate_json(self, prompt, *, timeout=30.0):
            raise ValueError("programming bug")
    with pytest.raises(ValueError):
        article_story({"title": "x", "summary": "s", "developments": []},
                      members=None, client=_Bug(), now=NOW)


def test_article_story_drops_invalid_output():
    llm = _FakeLLM({"headline": "", "lead": "L", "article": ["b"]})   # 빈 headline → validator None
    assert article_story({"title": "x", "summary": "s", "developments": []},
                         members=None, client=llm, now=NOW) is None
