from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor

from ..contracts.ports import LLMClient

EMBED_DIM = 768
BODY_CAP = 500
EMBED_CONCURRENCY = 50      # 병렬 임베딩 동시 호출 수 (백필 가속)


def embed_text(item) -> str:
    """임베딩 입력 = title + 본문(≤500자). spec §5.4 (기사당 1회)."""
    return f"{item.title} {(item.body or '')[:BODY_CAP]}".strip()


def embed_items(items: list, client: LLMClient,
                concurrency: int = EMBED_CONCURRENCY) -> list[list[float]]:
    """기사당 1회 임베딩, 병렬(순서 보존). 차원 불일치는 fail-loud(원칙3)."""
    if not items:
        return []

    def _one(it):
        vec = client.embed(embed_text(it), timeout=30.0)
        if len(vec) != EMBED_DIM:
            raise ValueError(f"embedding dim {len(vec)} != {EMBED_DIM}")
        return vec

    workers = max(1, min(concurrency, len(items)))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(_one, items))   # map은 순서 보존
