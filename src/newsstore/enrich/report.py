"""리포트 패스(리포트 탭 v1) — 스토리-그라운디드 섹션 리포트 + 백드롭 + 급부상.

스펙 docs/superpowers/specs/2026-06-30-report-tab-design.md §4·§5. 프레임은 frames.py(입력으로만).
top-K 랭킹은 UI(web/index.html storyRank)와 같은 정의: impact × 신선도(delta_time 최신성)."""
from __future__ import annotations
import logging
from datetime import datetime, timedelta, timezone

from .gemini import LLMError

log = logging.getLogger("newsstore.enrich.report")

REPORT_MAX_STORIES = 15       # 입력 하드캡 K(§4 — 토큰 폭탄 차단)
REPORT_MIN_STORIES = 2        # 빈 리포트 가드(§4 — 미만이면 콜 스킵)
SECTOR_STRATIFY_CAP = 5       # 주식 렌즈 층화: 같은 sector_* 최대 N건(§4 — cap, fill 아님)
RISING_MAX = 10               # 급부상 입력 상한
IMPACT_PRIOR = 1              # 미채점 prior(UI IMPACT_PRIOR와 동일 의미)
FRESH_TAU_H = 12.0            # 신선도 감쇠(UI FRESH_TAU_H와 동일)
DELTA_WINDOW = timedelta(hours=24)   # 급부상 밀도 창


def _latest_delta(story: dict):
    best = None
    for d in (story.get("developments") or []):
        t = d.get("delta_time") or d.get("time")
        if t is not None and (best is None or t > best):
            best = t
    return best or story.get("last_seen")


def story_rank(story: dict, now) -> float:
    """UI storyRank와 같은 정의(impact × 1/(1+age/tau)) — 프론트·백 동일 랭킹(§4)."""
    impact = story.get("impact")
    impact = IMPACT_PRIOR if impact is None else float(impact)
    ms = _latest_delta(story)
    if ms is None:
        return 0.0
    age_h = max(0.0, (now - ms).total_seconds() / 3600.0)
    return impact * (1.0 / (1.0 + age_h / FRESH_TAU_H))


def select_top_k(stories: list[dict], now, *, stratify: bool) -> list[dict]:
    """랭킹 상위 K. stratify=True(주식 렌즈)면 같은 sector_* 라벨 최대 SECTOR_STRATIFY_CAP —
    한 테마 독식 방지(cap). sector 라벨 없는 스토리는 cap 미적용."""
    ranked = sorted(stories, key=lambda s: (-story_rank(s, now), s.get("id", "")))
    if not stratify:
        return ranked[:REPORT_MAX_STORIES]
    out, per_sector = [], {}
    for s in ranked:
        sectors = [l for l in (s.get("lenses") or []) if l.startswith("sector_")]
        if sectors and any(per_sector.get(x, 0) >= SECTOR_STRATIFY_CAP for x in sectors):
            continue
        for x in sectors:
            per_sector[x] = per_sector.get(x, 0) + 1
        out.append(s)
        if len(out) >= REPORT_MAX_STORIES:
            break
    return out


def delta_density_24h(story: dict, now) -> int:
    """최근 24h delta_time 수(velocity 근사 — §3.5. 한계: 신규성 아님)."""
    n = 0
    for d in (story.get("developments") or []):
        t = d.get("delta_time") or d.get("time")
        if t is not None and (now - t) <= DELTA_WINDOW:
            n += 1
    return n


def select_rising(stories: list[dict], *, top_k_ids: set[str], now) -> list[dict]:
    """급부상 결정론 선정: 밀도 상위 + 전 렌즈 top-K(입력 선정 집합) 미등장(§3.5)."""
    cands = [(delta_density_24h(s, now), s) for s in stories
             if s.get("id") not in top_k_ids]
    cands = [(d, s) for d, s in cands if d > 0]
    cands.sort(key=lambda t: (-t[0], t[1].get("id", "")))
    return [s for _, s in cands[:RISING_MAX]]
