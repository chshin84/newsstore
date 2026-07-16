"""임베딩 입력 조립 + 병렬 실행 — ca8840a enrich/embedder.py 개조.

개조점(스펙 2026-07-16): 기사 단위 실패를 예외로 전파하지 않고 항목별 3분류
(성공/영구/재시도)로 돌려 embed_pass가 플래그 처분을 결정론적으로 가른다.
예외: 401/403(인증)·차원 불일치는 항목 문제가 아니라 설정 드리프트 — 그대로 전파해
패스 전체 실패(exit 1)로 승격한다(항목별 영구 처분하면 플래그가 부당하게 걷혀 조용히 고착).
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from ..contracts.embedding import EMBED_DIM
from .gemini import PermanentEmbedError

BODY_CAP = 500
EMBED_CONCURRENCY = 50      # 병렬 임베딩 동시 호출 수 (ca8840a와 동일)

# 400=입력 문제(항목 귀속) → 항목별 영구 처분. 그 외 비일시 코드(401/403/404 등)와
# code=None(비-code 판별로 만들어진 PermanentEmbedError)은 설정 드리프트로 보고
# 패스 전체 실패로 승격한다 — 안전한 쪽(fail-loud) 폴백.
_PER_ITEM_PERMANENT_CODES = {400}


@dataclass
class EmbedResult:
    item_id: str
    outcome: str                     # "ok" | "permanent" | "retryable"
    vector: list[float] | None = None
    reason: str = ""


def embed_text(item: dict) -> str:
    """임베딩 입력 = title + 본문(≤500자). 기사당 1회(계약 — firestore-contract.md)."""
    return f"{item['title']} {(item['body'] or '')[:BODY_CAP]}".strip()


def embed_items(items: list[dict], client,
                concurrency: int = EMBED_CONCURRENCY) -> list[EmbedResult]:
    """기사당 1회 임베딩, 병렬(순서 보존). 항목별 3분류 — 차원 불일치는 패스 승격(fail-loud)."""
    if not items:
        return []

    def _one(it: dict) -> EmbedResult:
        text = embed_text(it)
        if not text:
            return EmbedResult(it["item_id"], "permanent", reason="empty input")
        try:
            vec = client.embed(text, timeout=30.0)
        except PermanentEmbedError as e:
            if e.code in _PER_ITEM_PERMANENT_CODES:
                return EmbedResult(it["item_id"], "permanent", reason=str(e))
            raise                     # 인증/모델명 드리프트 — 패스 전체 실패로 승격
        except Exception as e:        # LLMError(재시도 소진)·네트워크 등
            return EmbedResult(it["item_id"], "retryable", reason=str(e))
        if len(vec) != EMBED_DIM:
            # 차원 불일치는 항목 문제가 아니라 설정 드리프트(EMBED_DIM ↔ API 응답) —
            # 항목별 처분하면 백로그 전체 플래그가 조용히 걷힌다. 401과 같이 승격.
            raise PermanentEmbedError(
                f"dim {len(vec)} != {EMBED_DIM} (config drift)", code=None)
        return EmbedResult(it["item_id"], "ok", vector=vec)

    workers = max(1, min(concurrency, len(items)))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(_one, items))   # map은 순서 보존
