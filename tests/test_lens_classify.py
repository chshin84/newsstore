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


def test_stage2_null_lenses_falls_back_to_prior():
    # {"lenses": null}: .get(key, [])는 null을 그대로 주므로 순회 시 TypeError로
    # 렌즈 패스 전체가 죽던 회귀 — 형태 위반은 prior 폴백(fail-soft)
    from newsstore.enrich.lens_classify import classify_stage2
    llm = _FakeLLM(None)
    assert classify_stage2(T, llm, story_text="x", candidates=["kr_rates"]) == ["kr_rates"]


def test_stage2_non_dict_response_falls_back_to_prior():
    from newsstore.enrich.lens_classify import classify_stage2

    class _Arr:                              # top-level JSON 배열(형태 위반)
        def generate_json(self, prompt, *, timeout=30.0):
            return ["kr_rates"]
    assert classify_stage2(T, _Arr(), story_text="x", candidates=["crypto"]) == ["crypto"]


def test_stage2_valid_empty_is_respected():
    # LLM의 정상 무선택 판정("아무 렌즈도 안 맞음")은 prior로 덮지 않는다(오탐 제거 목적)
    from newsstore.enrich.lens_classify import classify_stage2
    llm = _FakeLLM([])
    assert classify_stage2(T, llm, story_text="x", candidates=["kr_rates"]) == []


def test_region_us_stock_hint_beats_ko_language():
    # us_stock은 topics.yaml us_equity의 asset_hint — 손복제 _US_HINT에서 빠졌던 회귀.
    # 한국어 기사여도 asset_hint가 미국이면 us_equity가 남아야 한다(infomax_overseas 사례).
    out = _c(topics=["equities"], asset_hints=["us_stock"], language="ko")
    assert "us_equity" in out and "kr_equity" not in out


def test_region_kr_stock_hint_recognized():
    # kr_stock도 topics.yaml kr_equity asset_hint — 손복제 _KR_HINT에서 빠졌던 회귀
    out = _c(topics=["equities"], asset_hints=["kr_stock"], language="en")
    assert "kr_equity" in out and "us_equity" not in out


def test_keyword_match_is_case_insensitive():
    # topics.yaml 키워드는 소문자(gold 등) — 제목 첫머리 대문자 표기를 놓치면 안 된다
    out = _c(keyword_text="Gold Hits Record High")
    assert "precious_metals" in out


def test_stage2_propagates_non_llm_bug():
    import pytest
    from newsstore.enrich.lens_classify import classify_stage2

    class _Bug:                          # 코드 버그(비-LLMError)는 폴백으로 위장 말고 전파(FAIL-LOUD)
        def generate_json(self, prompt, *, timeout=30.0):
            raise ValueError("programming bug")
    with pytest.raises(ValueError):
        classify_stage2(T, _Bug(), story_text="x", candidates=["kr_rates"])
