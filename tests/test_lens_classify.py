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
