"""Phase 2 델타 — delta_time 배정(순수·결정론). LLM·store 의존 없음.

delta_time = 그 전개가 우리 스토어에 새 정보로 처음 편입된 시각. milestone 게이트:
새 전개(is_new=True)는 자기 발행시각(time), recap(is_new!=True이고 프런티어 존재)은
프런티어(max prior delta_time)에 귀속해 새 델타로 앞서지 않게 한다(analysis-design §6).
"""
from __future__ import annotations

MILESTONE_PRIOR_MAX = 12          # prior를 milestone 프롬프트에 먹이는 상한(토큰 통제)


def _frontier(prior_developments: list[dict]):
    """prior delta_time 중 max(없거나 모두 None이면 None — 비교 불가=첫 요약/legacy)."""
    times = [p.get("delta_time") for p in (prior_developments or [])
             if p.get("delta_time") is not None]
    return max(times) if times else None


def assign_delta_times(developments: list[dict], *, prior_developments: list[dict]) -> list[dict]:
    """각 development에 delta_time을 배정한 새 리스트 반환. is_new는 내부 신호라 제거.

    is_new is True 또는 프런티어 None → delta_time=time(새 전개/첫요약/legacy).
    그 외(recap이고 프런티어 존재) → delta_time=프런티어(새 델타 비생성, 보수적).
    """
    frontier = _frontier(prior_developments)
    out = []
    for d in developments:
        is_new = d.get("is_new") is True            # 정확히 True만 새 전개(누락/null/비bool=recap)
        dt = d["time"] if (is_new or frontier is None) else frontier
        out.append({"text": d["text"], "time": d["time"],
                    "source_count": d["source_count"], "delta_time": dt,
                    "event_time": d.get("event_time")})
    return out


def prior_texts(prior_developments: list[dict]) -> list[str]:
    """milestone 프롬프트용 prior 텍스트(time desc 최신순, MILESTONE_PRIOR_MAX 상한)."""
    ordered = sorted((p for p in (prior_developments or []) if p.get("time") is not None),
                     key=lambda p: p["time"], reverse=True)
    return [p["text"] for p in ordered[:MILESTONE_PRIOR_MAX]]
