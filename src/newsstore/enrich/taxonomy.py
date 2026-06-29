from __future__ import annotations
from pathlib import Path
import yaml


def load_taxonomy(path="config/taxonomy.yaml") -> dict:
    """통제 어휘 로드 → {'entities': [...], 'topics': [...]}. (tickers는 LLM 추출)"""
    d = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    ents, topics = list(d.get("entities", [])), list(d.get("topics", []))
    if not ents and not topics:          # 빈/오타 설정을 조용히 통과시키지 않는다(FAIL-LOUD)
        raise ValueError(f"taxonomy at {path}: entities·topics 둘 다 비어 있음 — 설정 오류")
    return {"entities": ents, "topics": topics}
