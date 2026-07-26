"""임베딩 계약 상수 — 단일 출처(SSOT).

모델명·차원은 다운스트림과의 계약이다(쿼리도 같은 모델·차원으로 임베딩해야 유사도
검색이 성립). embed 모듈(입력 조립·API 호출)과 store(문서 필드 주입)가 모두 여기서
도출한다 — 독립 리터럴 이중 정의 금지.
"""
EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 768          # gemini-embedding-001 기본 3072차원 → output_dimensionality로 축소

# 임베딩 용도. 같은 문장도 task_type에 따라 다른 벡터가 나오므로 모델·차원과 동급의
# 계약이다 — 다운스트림은 질의를 RETRIEVAL_QUERY로 임베딩해야 이 벡터와 짝이 맞는다.
#
# RETRIEVAL_DOCUMENT를 고른 근거는 취향이 아니라 실측이다(2026-07-26, 실 저장 기사 표본).
# 다운스트림 용도는 중복 기사 접기 + 유사 기사 군집이라 이름만 보면 SEMANTIC_SIMILARITY나
# CLUSTERING이 맞아 보이는데, 재보니 반대였다. 중복 쌍과 무관 쌍을 가르는 AUC가
# RETRIEVAL_DOCUMENT 1.000(마진 0.256) · SEMANTIC_SIMILARITY 1.000(0.180) · CLUSTERING
# 0.967(0.176)로, CLUSTERING은 완벽 분리에 실패했다. 뒤 둘은 유사도 값을 잘 맞추도록
# 훈련돼 공간이 압축되는데(무관 쌍조차 0.77로 뜬다), 임계값으로 접고 가르는 용도에는
# 넓게 퍼진 공간이 유리하다. 과병합이 이 도메인의 알려진 실패 모드라 마진이 곧 안전 여유다.
# 바꾸면 전량 재임베딩이 필요한 단방향 문이다.
EMBED_TASK_TYPE = "RETRIEVAL_DOCUMENT"
