from __future__ import annotations
import math

def cosine(a: list[float], b: list[float]) -> float:
    """코사인 유사도. 영벡터면 0.0 (0division 회피)."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0
