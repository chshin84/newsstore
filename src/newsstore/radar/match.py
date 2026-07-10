"""단어경계 어휘 매칭 — 부분문자열 오탐(IREN→사이렌 류) 차단.

규칙(스펙 §5 '토큰 경계'의 스크립트별 구체화):
- 선행 경계: alias 바로 앞이 [가-힣A-Za-z0-9]면 불일치(공통).
- 후행 경계: 라틴/숫자 alias는 뒤가 [A-Za-z0-9]면 불일치. 한글 alias는 뒤에 한글이 와도
  일치(조사 결합 '하이닉스가' 허용 — 한국어는 공백 없이 조사가 붙는다).
"""
from __future__ import annotations

import re

import yaml

_WORD = "0-9A-Za-z가-힣"


def _pattern(alias: str) -> re.Pattern:
    esc = re.escape(alias)
    lead = f"(?<![{_WORD}])"
    tail = "" if re.search(r"[가-힣]$", alias) else "(?![0-9A-Za-z])"
    return re.compile(lead + esc + tail)


def find_alias(alias: str, text: str) -> tuple[str, int] | None:
    m = _pattern(alias).search(text or "")
    return (alias, m.start()) if m else None


def find_any(aliases: list[str], text: str) -> tuple[str, int] | None:
    for a in aliases:
        hit = find_alias(a, text)
        if hit:
            return hit
    return None


def load_vocab(path: str = "config/radar_vocab.yaml") -> list[str]:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    vocab: list[str] = []
    if raw.get("derived_from_taxonomy"):
        with open("config/taxonomy.yaml", encoding="utf-8") as tf:
            tax = yaml.safe_load(tf)
        vocab.extend(tax["entities"])
    vocab.extend(raw.get("manual") or [])
    if len(vocab) != len(set(vocab)):
        raise ValueError("radar_vocab: 중복 어휘")
    return vocab
