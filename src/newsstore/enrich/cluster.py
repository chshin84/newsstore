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

# 최근접 스토리 검색은 enrich.vector_index.InMemoryVectorIndex(포트 구현)가 담당.
# (과거 best_match/assign은 그 포트로 흡수됨)
