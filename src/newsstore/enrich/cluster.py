from __future__ import annotations
import math

def cosine(a: list[float], b: list[float]) -> float:
    """코사인 유사도. 영벡터면 0.0 (0division 회피)."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0

DEFAULT_THRESHOLD = 0.83

def centroid(centroid_sum: list[float], count: int) -> list[float]:
    """중심 = 누적합 / 개수."""
    return [x / count for x in centroid_sum]

def assign(vec: list[float], open_stories: list[dict],
           threshold: float = DEFAULT_THRESHOLD) -> str | None:
    """가장 유사한 '열린 스토리' id를 반환(코사인 ≥ threshold). 없으면 None(=새 스토리).
    open_stories: [{'id': str, 'centroid': list[float]}]. centroid 기준이라 전이 연쇄 없음."""
    best_id, best_sim = None, -1.0
    for st in open_stories:
        s = cosine(vec, st["centroid"])
        if s > best_sim:
            best_sim, best_id = s, st["id"]
    return best_id if best_sim >= threshold else None
