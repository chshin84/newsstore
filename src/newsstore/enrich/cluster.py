from __future__ import annotations
import math

def cosine(a: list[float], b: list[float]) -> float:
    """코사인 유사도. 영벡터면 0.0 (0division 회피).
    차원이 다르면 ValueError (zip 무음 절단 방지 — fail-loud, 원칙3)."""
    if len(a) != len(b):
        raise ValueError(f"cosine dim mismatch: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0

# 클러스터 합류 코사인 임계값. 0.83은 스파이크의 Vertex 임베딩 기준(폐기). 프로덕션
# 모델 gemini-embedding-001(768)을 실 Firestore 기사 120건으로 캘리브레이션:
#   교차소스 같은 사건 0.71~0.86(이란 MOU·코스피·크립토법안), 노이즈 천장 p99≈0.66.
#   → 0.72(0.65는 토픽만 비슷한 별개 글 오병합). env NEWSSTORE_CLUSTER_THRESHOLD로 튜닝.
DEFAULT_THRESHOLD = 0.72

def centroid(centroid_sum: list[float], count: int) -> list[float]:
    """중심 = 누적합 / 개수. count는 ≥1 (스토리는 최소 1 멤버)."""
    if count <= 0:
        raise ValueError(f"count must be >= 1, got {count}")
    return [x / count for x in centroid_sum]

def best_match(vec: list[float], candidates: list[dict],
               threshold: float = DEFAULT_THRESHOLD) -> int:
    """가장 유사한 candidate의 인덱스(코사인 ≥ threshold) 또는 -1(=새 스토리).
    candidates: [{'centroid': list[float], ...}]. in-memory 캐시 클러스터링용(Firestore 재조회 회피)."""
    best_i, best_s = -1, -1.0
    for i, c in enumerate(candidates):
        s = cosine(vec, c["centroid"])
        if s > best_s:
            best_s, best_i = s, i
    return best_i if best_s >= threshold else -1


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
