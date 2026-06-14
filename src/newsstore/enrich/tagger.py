from __future__ import annotations
import logging
import re

from ..contracts.ports import LLMClient
from .llm import LLMError

log = logging.getLogger("newsstore.enrich.tagger")

MAX_TICKERS = 5
_TICKER_RE = re.compile(r"^[A-Z0-9]{1,6}(\.[A-Z]{1,3})?$")   # NVDA, 000660.KS


def validate_tags(raw: dict, taxonomy: dict) -> dict:
    """결정론 적합성 검증(advisor-fit): 어휘 밖·형식위반·과다 티커 제거.

    비파괴: 저장 전 필터링일 뿐 원본 raw 응답은 호출자가 로깅. 결정론으로 잡히는 것은
    LLM 리뷰 콜 없이 코드로(비용↓). 환각 grounding 등 결정론 불가한 건만 추후 LLM 리뷰.
    """
    raw = raw or {}
    ent_vocab = set(taxonomy["entities"])
    top_vocab = set(taxonomy["topics"])
    entities = [e for e in raw.get("entities", []) if e in ent_vocab]
    topics = [t for t in raw.get("topics", []) if t in top_vocab]
    tickers = [t for t in raw.get("tickers", [])
               if isinstance(t, str) and _TICKER_RE.match(t)]
    return {"tickers": tickers[:MAX_TICKERS], "entities": entities, "topics": topics}


def build_prompt(items: list, taxonomy: dict) -> str:
    """통제어휘를 프롬프트에 SSOT로 주입. 사건명은 태그가 아니라 스토리(클러스터)."""
    ents = ", ".join(taxonomy["entities"])
    tops = ", ".join(taxonomy["topics"])
    lines = [f'{i}. {it.title} :: {(it.body or "")[:200]}' for i, it in enumerate(items)]
    return (
        "You tag financial news. For each item return tickers (extract symbols), "
        f"entities (ONLY from this list: {ents}), topics (ONLY from this list: {tops}). "
        'Events (e.g. a war) are NOT tags. Return JSON '
        '{"results":[{"tickers":[],"entities":[],"topics":[]}]} in the same item order.\n'
        + "\n".join(lines)
    )


def tag_items(items: list, client: LLMClient, taxonomy: dict, *, batch: int = 10) -> list[dict]:
    """≤batch건씩 태깅 → 결정론 검증. 결과 수 불일치 시 빈 태그로 정렬 보존(fail-soft).

    batch 상한(비용/토큰 상한 — advisor-nonfunctional)으로 한 콜의 입력 크기를 묶는다.
    """
    out: list[dict] = []
    for s in range(0, len(items), batch):
        chunk = items[s:s + batch]
        try:
            resp = client.generate_json(build_prompt(chunk, taxonomy), timeout=30.0)
        except LLMError as e:        # 한 배치 실패가 전체를 죽이지 않게 fail-soft(빈 태그)
            log.warning("tagging batch failed, continuing with empty tags: %s", e)
            resp = {}
        results = (resp or {}).get("results", [])
        for j in range(len(chunk)):
            raw = results[j] if j < len(results) else {}
            out.append(validate_tags(raw, taxonomy))
    return out
