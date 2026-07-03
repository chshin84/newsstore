"""프레임 패스(리포트 탭 v1) — standing 프레임(risk/premium/watchpoints) 이월·재심.

스펙 docs/superpowers/specs/2026-06-30-report-tab-design.md §3: 전용 패스가 어제 프레임을
입력으로 전체 극을 재심(유지/수정/탈락 — 나이 기반 밀어내기 없음), diff(신규/수정)만
grounding 리뷰. 실패 시 어제 프레임 유지(이월 폴백)."""
from __future__ import annotations
import json
import logging

from .gemini import LLMError

log = logging.getLogger("newsstore.enrich.frames")

FRAME_MAX_POLES = 5           # 축당 극 상한(결정⑧ — 무상한이면 리포트 입력 폭탄)
FRAME_MAX_INPUT_STORIES = 30  # 프레임 패스 입력 캡(§3 — 프레임 패스가 새 토큰 폭탄 금지)
MAX_POLE_TEXT = 120
AXES = ("risks", "premiums", "watchpoints")


def validate_frame(raw) -> dict | None:
    """결정론 검증: 3축 스키마·축당 상한·극 id/text 필수(무효 극은 드롭). 실패 → None."""
    if not isinstance(raw, dict):
        return None
    out: dict = {}
    for axis in AXES:
        poles = raw.get(axis)
        if poles is None:
            out[axis] = []
            continue
        if not isinstance(poles, list):
            return None                       # 축 타입 위반은 프레임 전체 무효(fail-loud)
        keep = []
        for p in poles:
            if (isinstance(p, dict) and isinstance(p.get("id"), str) and p["id"].strip()
                    and isinstance(p.get("text"), str) and p["text"].strip()):
                keep.append({"id": p["id"].strip(), "text": p["text"].strip()[:MAX_POLE_TEXT]})
        out[axis] = keep[:FRAME_MAX_POLES]
    return out


def frame_diff(old: dict, new: dict) -> list[dict]:
    """신규·수정 극만(diff-grounding 리뷰 대상 — 유지 극은 과거 검증분). 스펙 §5 표."""
    prev = {p["id"]: p["text"] for axis in AXES for p in (old.get(axis) or [])}
    return [p for axis in AXES for p in (new.get(axis) or [])
            if p["id"] not in prev or prev[p["id"]] != p["text"]]
