from __future__ import annotations
from pathlib import Path
import yaml


def load_taxonomy(path="config/taxonomy.yaml") -> dict:
    """통제 어휘 로드 → {'entities': [...], 'topics': [...]}. (tickers는 LLM 추출)"""
    d = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return {"entities": list(d.get("entities", [])), "topics": list(d.get("topics", []))}
