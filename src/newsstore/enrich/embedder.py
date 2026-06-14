from __future__ import annotations

from .llm import LLMClient

EMBED_DIM = 768
BODY_CAP = 500


def embed_text(item) -> str:
    """임베딩 입력 = title + 본문(≤500자). spec §5.4 (기사당 1회)."""
    return f"{item.title} {(item.body or '')[:BODY_CAP]}".strip()


def embed_items(items: list, client: LLMClient) -> list[list[float]]:
    """기사당 1회 임베딩. 차원 불일치는 fail-loud(원칙3 — cluster.cosine/add_vectors와 정합)."""
    out: list[list[float]] = []
    for it in items:
        vec = client.embed(embed_text(it), timeout=30.0)
        if len(vec) != EMBED_DIM:
            raise ValueError(f"embedding dim {len(vec)} != {EMBED_DIM}")
        out.append(vec)
    return out
