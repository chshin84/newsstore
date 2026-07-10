"""config/watchlist.yaml — 종목·지수·환율의 단일 출처(SSOT) 로더.
검증은 로드 시 즉시 터뜨린다(FAIL-LOUD): id 중복·ticker 결측·station인데 aliases 없음."""
from __future__ import annotations

import yaml

REQUIRED = ("id", "label", "ticker", "role", "station", "aliases")
ROLES = ("stock", "index", "fx")


def load_watchlist(path: str = "config/watchlist.yaml") -> list[dict]:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    entries = raw.get("entries") or []
    seen: set[str] = set()
    for e in entries:
        missing = [k for k in REQUIRED if k not in e]
        if missing:
            raise ValueError(f"watchlist 항목 {e.get('id')!r}: 필수 필드 결측 {missing} (ticker 포함)")
        if not e["ticker"]:
            raise ValueError(f"watchlist 항목 {e['id']!r}: ticker 결측")
        if e["id"] in seen:
            raise ValueError(f"watchlist id 중복: {e['id']!r}")
        seen.add(e["id"])
        if e["role"] not in ROLES:
            raise ValueError(f"watchlist 항목 {e['id']!r}: role {e['role']!r}은 {ROLES} 중 하나여야 한다")
        if e["station"] and not e["aliases"]:
            raise ValueError(f"watchlist 항목 {e['id']!r}: station=true면 aliases가 비어 있을 수 없다")
    return entries


def station_entries(entries: list[dict]) -> list[dict]:
    return [e for e in entries if e["station"]]
