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


def build_frame_prompt(lens_id: str, old: dict, stories: list[dict]) -> str:
    """이월 재심 프롬프트 — 어제 극 전부 + 최근 스토리(캡). 유지 판단에도 근거 검토 요구(§3 재심 계약)."""
    lines = [f'{i}. [{s["id"]}] {s.get("title", "")} :: {(s.get("summary") or "")[:150]}'
             for i, s in enumerate(stories[:FRAME_MAX_INPUT_STORIES])]
    return (
        f"당신은 '{lens_id}' 자산군의 standing 프레임을 유지하는 애널리스트다.\n"
        "프레임 3축: risks(아킬레스건/실질 리스크), premiums(기대/컨센서스), "
        "watchpoints(극을 트리거할 수 있는 예정된 관찰 지점 — 판단/조언 금지).\n"
        f"어제의 프레임(재검토 대상):\n{json.dumps(old or {a: [] for a in AXES}, ensure_ascii=False)}\n"
        "최근 스토리:\n" + "\n".join(lines) + "\n"
        "임무: 어제 극을 하나씩 재검토하라 — 여전히 유효하면 id 유지(근거 스토리가 최근에 없어도 "
        "구조적으로 유효하면 유지 가능하되 그 이유를 스스로 검토), 낡았으면 탈락, 새 위험/기대/"
        f"관찰 지점은 추가(신규 id). 축당 최대 {FRAME_MAX_POLES}개.\n"
        '아래 JSON만 출력: {"risks":[{"id":"...","text":"..."}],"premiums":[...],"watchpoints":[...]}')


def build_frame_review_prompt(diff: list[dict], stories: list[dict]) -> str:
    """diff-grounding 심사(§5 표) — 신규/수정 극이 스토리에 근거하는지."""
    lines = [f'[{s["id"]}] {s.get("title", "")} :: {(s.get("summary") or "")[:150]}'
             for s in stories[:FRAME_MAX_INPUT_STORIES]]
    return (
        "당신은 grounding 심사자다. 아래 신규/수정 프레임 극이 제공된 스토리에서 "
        "합리적으로 도출 가능한지 심사하라(구조적 상식 수준의 일반 명제는 허용, "
        "스토리와 무관한 구체 단정은 기각).\n"
        f"극:\n{json.dumps(diff, ensure_ascii=False)}\n스토리:\n" + "\n".join(lines) + "\n"
        '아래 JSON만 출력: {"passed": true|false, "notes": "기각 사유 또는 빈 문자열"}')


def run_frame_pass(store, client, *, lens_ids: list[str], now, window=None) -> int:
    """렌즈별 프레임 재심. 실패(콜·검증·리뷰 기각)는 어제 판 유지(fail-soft, §5(c)). 반환=갱신 수."""
    from datetime import timedelta
    cutoff = now - (window or timedelta(hours=72))
    n = 0
    for lens_id in lens_ids:
        old = store.get_frame(lens_id)
        stories = store.get_stories_for_report(lens_id, cutoff=cutoff)
        try:
            raw = client.generate_json(build_frame_prompt(lens_id, old, stories), timeout=60.0)
        except LLMError as e:
            log.warning("frame pass %s: LLM 실패 — 어제 판 유지: %s", lens_id, e)
            continue
        frame = validate_frame(raw)
        if frame is None:
            log.warning("frame pass %s: 결정론 검증 실패 — 어제 판 유지", lens_id)
            continue
        diff = frame_diff(old, frame)
        if diff:
            try:
                verdict = client.generate_json(
                    build_frame_review_prompt(diff, stories), timeout=60.0)
            except LLMError as e:
                log.warning("frame pass %s: 리뷰 콜 실패 — 어제 판 유지: %s", lens_id, e)
                continue
            if not (isinstance(verdict, dict) and verdict.get("passed") is True):
                log.warning("frame pass %s: diff-grounding 기각(%s) — 어제 판 유지",
                            lens_id, (verdict or {}).get("notes"))
                continue
        store.save_frame(lens_id, frame, now=now)
        n += 1
    log.info("frame pass: %d/%d updated", n, len(lens_ids))
    return n
