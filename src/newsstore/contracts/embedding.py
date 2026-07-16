"""임베딩 계약 상수 — 단일 출처(SSOT).

모델명·차원은 다운스트림과의 계약이다(쿼리도 같은 모델·차원으로 임베딩해야 유사도
검색이 성립). embed 모듈(입력 조립·API 호출)과 store(문서 필드 주입)가 모두 여기서
도출한다 — 독립 리터럴 이중 정의 금지.
"""
EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 768          # gemini-embedding-001 기본 3072차원 → output_dimensionality로 축소
