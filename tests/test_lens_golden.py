"""렌즈 분류 골든 불변식 — 자명해(전부 미배정·한 렌즈) 격파. 매직넘버 없음."""
from newsstore.enrich import topics
from newsstore.enrich.lens_classify import classify_stage1

T = topics.load_topics()

# 합성 골든: (신호, 정답 렌즈)
GOLDEN = [
    (dict(asset_hints=["kr_bond"], keyword_text="한은 금리"), {"kr_rates"}),
    (dict(asset_hints=["crypto"], keyword_text="비트코인"), {"crypto"}),
    (dict(asset_hints=["energy"], keyword_text="유가"), {"oil_energy"}),
    (dict(asset_hints=["equity"], keyword_text="엔비디아 실적", language="en"),
     {"watch_nvidia", "us_equity"}),                  # 멀티라벨
    (dict(asset_hints=["kr_realestate"], keyword_text="집값"), {"kr_realestate"}),
    (dict(asset_hints=[], keyword_text="잡담"), set()),  # 미배정
]


def _pred(sig):
    base = dict(asset_hints=[], tickers=[], entities=[], topics=[], language="ko", keyword_text="")
    base.update(sig)
    return set(classify_stage1(T, **base))


def _micro(preds, golds):
    tp = sum(len(p & g) for p, g in zip(preds, golds))
    fp = sum(len(p - g) for p, g in zip(preds, golds))
    fn = sum(len(g - p) for p, g in zip(preds, golds))
    prec = tp / (tp + fp) if (tp + fp) else 1.0
    rec = tp / (tp + fn) if (tp + fn) else 1.0
    return prec, rec


def test_golden_beats_trivial_baselines():
    golds = [g for _, g in GOLDEN]
    preds = [_pred(s) for s, _ in GOLDEN]
    p, r = _micro(preds, golds)
    _, r_empty = _micro([set()] * len(golds), golds)          # 자명해1: 전부 미배정
    p_one, _ = _micro([{"crypto"}] * len(golds), golds)       # 자명해2: 한 렌즈만
    assert r > r_empty                                        # 미배정보다 recall 높음
    assert p > p_one                                          # 한 렌즈 박기보다 precision 높음


def test_same_signal_same_lens():
    assert _pred(dict(asset_hints=["kr_bond"])) == _pred(dict(asset_hints=["kr_bond"]))


def test_orthogonal_signals_differ():
    assert _pred(dict(asset_hints=["crypto"])) != _pred(dict(asset_hints=["energy"]))
