"""클러스터링 골든 — B-cubed 메트릭 자기검증 + 결정론 수렴 불변식(키 불요).

실 Gemini eval(F1=0.821, 이란+코스피 골든셋)은 GEMINI_API_KEY·실데이터 fixture에 의존하므로
news-analytics origin(eval 하네스)에 잔류하고 오프라인 측정한다. 여기선 합성 코퍼스로
'자명해(전부병합·전부분리)를 모두 이긴다'는 불변식만 결정론으로 검증한다(매직넘버 없음).
"""
from __future__ import annotations

import math

from clustering_metrics import bcubed
from newsstore.enrich.clustering import cluster_articles
from newsstore.enrich.clustering_types import Article


def _approx(a, b, tol=1e-9):
    return math.isclose(a, b, abs_tol=tol)


# ── B-cubed 메트릭 자기검증 (news-analytics test_metrics.py 이식) ──────────────

def test_metric_perfect_match_is_one():
    gold = {"a": "x", "b": "x", "c": "y"}
    assert bcubed({"a": 0, "b": 0, "c": 1}, gold) == (1.0, 1.0, 1.0)


def test_metric_all_one_cluster_recall_one_precision_drops():
    gold = {"a": "x", "b": "x", "c": "y"}
    p, r, _ = bcubed({"a": 0, "b": 0, "c": 0}, gold)
    assert _approx(p, 5 / 9) and _approx(r, 1.0)


def test_metric_all_singletons_precision_one_recall_drops():
    gold = {"a": "x", "b": "x", "c": "y"}
    p, r, _ = bcubed({"a": 0, "b": 1, "c": 2}, gold)
    assert _approx(p, 1.0) and _approx(r, 2 / 3)


# ── 수렴 불변식: cluster_articles가 두 자명해를 모두 이긴다 ────────────────────

def _art(i, vec):
    return Article(id=i, title=f"t{i}", body="b", source="S", published_at="2026-06-29",
                   embedding=tuple(vec))


def test_cluster_articles_beats_trivial_solutions():
    # 3개 사건 × 각 2건. 같은 사건=같은 직교 단위벡터(cos=1.0), 다른 사건=직교(cos=0.0).
    events = {"e1": (1.0, 0.0, 0.0), "e2": (0.0, 1.0, 0.0), "e3": (0.0, 0.0, 1.0)}
    articles, gold = [], {}
    for ev, vec in events.items():
        for k in range(2):
            aid = f"{ev}_{k}"
            articles.append(_art(aid, vec))
            gold[aid] = ev
    pred = cluster_articles(articles, embed=lambda t: [[0.0, 0.0, 0.0]] * len(t), llm=None)

    p, r, f1 = bcubed(pred, gold)
    assert (p, r, f1) == (1.0, 1.0, 1.0)                       # 완전 수렴+분리

    all_one = {a.id: 0 for a in articles}                     # 자명해 1: 전부 한 덩어리
    singletons = {a.id: i for i, a in enumerate(articles)}    # 자명해 2: 전부 싱글톤
    assert f1 > bcubed(all_one, gold)[2]
    assert f1 > bcubed(singletons, gold)[2]
