"""클러스터링 평가 메트릭(eval 헬퍼 — 제품 코드 아님). news-analytics @249aa3d에서 이식.

B-cubed: 이벤트/상호참조 클러스터링의 표준 외재적 메트릭(Amigó 2009 형식제약 충족).
- precision: 기사별 '내 클러스터 안 같은 정답 라벨 비율' 평균 → 과병합 벌점.
- recall:    기사별 '같은 정답 라벨 중 내 클러스터에 들어온 비율' 평균 → 과분할 벌점.
pred/gold 교집합 id만 평가한다.
"""
from __future__ import annotations

from collections import defaultdict


def bcubed(pred: dict, gold: dict) -> tuple[float, float, float]:
    """(precision, recall, f1)를 반환. pred: id→cluster_id, gold: id→true_label."""
    items = [i for i in pred if i in gold]
    if not items:
        return 0.0, 0.0, 0.0

    pred_groups: dict[object, set] = defaultdict(set)
    gold_groups: dict[object, set] = defaultdict(set)
    for i in items:
        pred_groups[pred[i]].add(i)
        gold_groups[gold[i]].add(i)

    precision = recall = 0.0
    for i in items:
        pc = pred_groups[pred[i]]
        gc = gold_groups[gold[i]]
        inter = len(pc & gc)
        precision += inter / len(pc)
        recall += inter / len(gc)

    n = len(items)
    precision /= n
    recall /= n
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1
