from newsstore.enrich import topics
from newsstore.enrich.lens_classify import classify_stage1

T = topics.load_topics()


def _c(**kw):
    base = dict(asset_hints=[], tickers=[], entities=[], topics=[], language="en", keyword_text="")
    base.update(kw)
    return classify_stage1(T, **base)


def test_asset_hint_is_primary_signal():
    # 태그 비어도 asset_hint만으로 분류(신뢰 prior)
    assert "kr_rates" in _c(asset_hints=["kr_bond"])
    assert "crypto" in _c(asset_hints=["crypto"])


def test_watch_ticker_exact_match():
    assert "watch_samsung" in _c(tickers=["005930"], asset_hints=["kr_market"])
    assert "watch_nvidia" in _c(keyword_text="엔비디아 신제품")


def test_region_disambiguation_equities():
    # equities topic이지만 한국 신호 → kr_equity만(둘 다 X)
    out = _c(topics=["equities"], asset_hints=["kr_market"], language="ko")
    assert "kr_equity" in out and "us_equity" not in out
    out2 = _c(topics=["equities"], asset_hints=["equity"], language="en")
    assert "us_equity" in out2 and "kr_equity" not in out2


def test_max_lenses_cap():
    # 많은 신호 → 상한(MAX_LENSES=4) 준수
    out = _c(asset_hints=["kr_bond", "kr_macro", "crypto", "energy", "commodity", "kr_realestate"])
    assert len(out) <= 4


def test_empty_signals_no_assignment():
    assert _c() == []          # fail-safe: 신호 없음 → 미배정(emergent)


class _FakeLLM:
    def __init__(self, lenses, boom=False):
        self.lenses, self.boom = lenses, boom

    def generate_json(self, prompt, *, timeout=30.0):
        if self.boom:
            from newsstore.enrich.gemini import LLMError
            raise LLMError("down")          # LLM 장애만 prior 폴백
        return {"lenses": self.lenses}


def test_stage2_validates_and_caps():
    from newsstore.enrich.lens_classify import classify_stage2
    # 환각 id·중복·>MAX_LENSES → validator가 정제
    llm = _FakeLLM(["kr_rates", "INVALID_ID", "crypto", "fx", "risk", "kr_rates"])
    out = classify_stage2(T, llm, story_text="x", candidates=[])
    assert "INVALID_ID" not in out
    assert out.count("kr_rates") <= 1 and len(out) <= 4 and "kr_rates" in out


def test_stage2_failsoft_to_candidates():
    from newsstore.enrich.lens_classify import classify_stage2
    llm = _FakeLLM([], boom=True)        # LLM 장애 → prior 폴백
    assert classify_stage2(T, llm, story_text="x", candidates=["kr_rates"]) == ["kr_rates"]


def test_stage2_propagates_non_llm_bug():
    import pytest
    from newsstore.enrich.lens_classify import classify_stage2

    class _Bug:                          # 코드 버그(비-LLMError)는 폴백으로 위장 말고 전파(FAIL-LOUD)
        def generate_json(self, prompt, *, timeout=30.0):
            raise ValueError("programming bug")
    with pytest.raises(ValueError):
        classify_stage2(T, _Bug(), story_text="x", candidates=["kr_rates"])
