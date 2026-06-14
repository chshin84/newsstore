from __future__ import annotations


def add_vectors(a: list[float], b: list[float]) -> list[float]:
    """원소별 합 a+b. 차원이 다르면 ValueError (centroid_sum 누적의 무음 절단 방지 — 원칙3).

    store(centroid_sum 누적)와 enrich(클러스터) 양쪽이 쓰는 공유 벡터 원시연산이라
    contracts에 둔다 — store가 enrich를 import하지 않게(모듈 경계).
    """
    if len(a) != len(b):
        raise ValueError(f"vector dim mismatch: {len(a)} vs {len(b)}")
    return [x + y for x, y in zip(a, b)]
