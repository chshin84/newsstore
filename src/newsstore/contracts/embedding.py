"""임베딩 계약 상수 — 단일 출처(SSOT).

모델명·차원은 다운스트림과의 계약이다(쿼리도 같은 모델·차원으로 임베딩해야 유사도
검색이 성립). embed 모듈(입력 조립·API 호출)과 store(문서 필드 주입)가 모두 여기서
도출한다 — 독립 리터럴 이중 정의 금지.
"""
EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 768          # gemini-embedding-001 기본 3072차원 → output_dimensionality로 축소

# 임베딩 용도. 같은 문장도 task_type에 따라 다른 벡터가 나오므로 모델·차원과 동급의
# 계약이다 — 다운스트림은 질의를 RETRIEVAL_QUERY로 임베딩해야 이 벡터와 짝이 맞는다.
# RETRIEVAL_DOCUMENT를 고른 이유: 저장 문서용 범용 타입이라 질의 검색과 문서 간 유사도·
# 군집 양쪽에 쓸 수 있다. SEMANTIC_SIMILARITY·CLUSTERING은 문서 간 비교에 더 특화되지만
# 질의 검색 쪽을 닫는다. 바꾸면 전량 재임베딩이 필요한 단방향 문이다.
EMBED_TASK_TYPE = "RETRIEVAL_DOCUMENT"
