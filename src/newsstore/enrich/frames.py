"""프레임 패스(리포트 탭 v1) — standing 프레임(risk/premium/watchpoints) 이월·재심.

스펙 docs/superpowers/specs/2026-06-30-report-tab-design.md §3: 전용 패스가 어제 프레임을
입력으로 전체 극을 재심(유지/수정/탈락 — 나이 기반 밀어내기 없음), diff(신규/수정)만
grounding 리뷰. 실패 시 어제 프레임 유지(이월 폴백)."""
from __future__ import annotations
import json
import logging

from .gemini import LLMError
from .model_config import model_for

log = logging.getLogger("newsstore.enrich.frames")

FRAME_MAX_POLES = 5           # 축당 극 상한(결정⑧ — 무상한이면 리포트 입력 폭탄)
FRAME_MAX_INPUT_STORIES = 30  # 프레임 패스 입력 캡(§3 — 프레임 패스가 새 토큰 폭탄 금지)
MAX_POLE_TEXT = 120
AXES = ("risks", "premiums", "watchpoints")
ACHILLES_KINDS = ("words_deeds", "structural")   # v1 enum(나머지 kind는 v2). 그 외는 null.


def validate_frame(raw, *, input_story_ids: set | None = None) -> dict | None:
    """결정론 검증: 3축 스키마·축당 상한·극 id/text 필수(무효 극은 드롭). 실패 → None.

    v1 구조화(스펙 §3·§5): achilles_kind(ACHILLES_KINDS만, 그 외 None)·evidence_dev_ids 보존.
    input_story_ids 주어지면 evidence_dev_ids를 실재 id로 필터(환각 드롭); 없으면 문자열만 유지.
    이월 구조극은 evidence 공란 허용(극 자체는 드롭하지 않음 — 근거 없어도 구조적 유지 계약)."""
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
                kind = p.get("achilles_kind")
                kind = kind if kind in ACHILLES_KINDS else None
                ev = [i for i in (p.get("evidence_dev_ids") or []) if isinstance(i, str)
                      and (input_story_ids is None or i in input_story_ids)]
                keep.append({"id": p["id"].strip(), "text": p["text"].strip()[:MAX_POLE_TEXT],
                             "achilles_kind": kind, "evidence_dev_ids": ev})
        out[axis] = keep[:FRAME_MAX_POLES]
    return out


def frame_diff(old: dict, new: dict) -> list[dict]:
    """신규·수정 극만(diff-grounding 리뷰 대상 — 유지 극은 과거 검증분). 스펙 §5 표."""
    prev = {p["id"]: p["text"] for axis in AXES for p in (old.get(axis) or [])}
    return [p for axis in AXES for p in (new.get(axis) or [])
            if p["id"] not in prev or prev[p["id"]] != p["text"]]


def build_frame_prompt(lens_id: str, old: dict, stories: list[dict]) -> str:
    """이월 재심 프롬프트 — 어제 극 전부 + 최근 스토리(캡). 유지 판단에도 근거 검토 요구(§3 재심 계약)."""
    # 실 프레임은 updated_at(datetime) 등 비직렬화 필드를 포함 — 3축(AXES)만 추려 직렬화(C1)
    axes_only = {a: (old or {}).get(a) or [] for a in AXES}
    lines = [f'{i}. [{s["id"]}] {s.get("title", "")} :: {(s.get("summary") or "")[:150]}'
             for i, s in enumerate(stories[:FRAME_MAX_INPUT_STORIES])]
    return (
        f"당신은 '{lens_id}' 자산군의 standing 프레임을 유지하는 시니어 애널리스트다.\n"
        "센티먼트 근사 준거 — 말이 아니라 '비용을 치른 행동(RAS)'을 본다: 브로커 목표가 상향·"
        "낙관 논평(말)이 아니라, 스토리 전개(developments)에 담긴 비가역 행동 — capex 감축·"
        "잉여자원 매도·감원·정점 증자·비중 축소 — 을 근거로 삼아라. 서술 톤과 행동의 부호가 "
        "어긋나는 곳(톤↑·행동↓ 또는 그 반대)이 숨은 공포의 시그니처다.\n"
        "프레임 3축:\n"
        "- risks(아킬레스건): '지금 터진다면 시장이 가장 두려워할' 소수·고강도 시나리오만. "
        "구조적 급소를 과감·깊게 — 지배적 투자 사이클의 철회, 핵심 수요처의 이탈처럼 내러티브 "
        "전체를 뒤집는 급. 사소한 것은 버려라.\n"
        "- premiums(기대/컨센서스): 현재 가격·내러티브를 지탱하는 핵심 믿음 — 꺾이면 상방 논리가 "
        "무너지는 것.\n"
        "- watchpoints: 위 극을 트리거할 예정된 관찰 지점(판단/조언 금지).\n"
        f"어제의 프레임(재검토 대상):\n{json.dumps(axes_only, ensure_ascii=False)}\n"
        "최근 스토리(각 줄 맨 앞 [id]가 story_id — evidence 인용에 사용):\n" + "\n".join(lines) + "\n"
        "임무: 어제 극을 하나씩 재검토 — 유효하면 id 유지(근거 스토리 없어도 구조적 유효 시 유지 "
        "가능, 이유 자가검토), 낡으면 탈락, 새 위험/기대/관찰은 추가(신규 id). "
        f"축당 최대 {FRAME_MAX_POLES}개 — 수 채우지 말고 강도로 골라라.\n"
        "각 극에 achilles_kind와 evidence_dev_ids를 붙여라: achilles_kind는 말-행동 괴리(RAS)로 "
        "잡은 극이면 'words_deeds', 근거 이벤트 없이 구조적으로 유지하는 이월 극이면 'structural'. "
        "evidence_dev_ids는 그 극의 근거가 된 story_id 배열(위 목록에 실재하는 것만; 구조극은 [] 허용).\n"
        '아래 JSON만 출력: {"risks":[{"id":"...","text":"...","achilles_kind":"words_deeds|structural",'
        '"evidence_dev_ids":["..."]}],"premiums":[...],"watchpoints":[...]}')


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
            raw = client.generate_json(build_frame_prompt(lens_id, old, stories), timeout=60.0,
                                       model=model_for("frame_gen"))
        except LLMError as e:
            log.warning("frame pass %s: LLM 실패 — 어제 판 유지: %s", lens_id, e)
            continue
        frame = validate_frame(raw, input_story_ids={s["id"] for s in stories if s.get("id")})
        if frame is None:
            log.warning("frame pass %s: 결정론 검증 실패 — 어제 판 유지", lens_id)
            continue
        diff = frame_diff(old, frame)
        if diff:
            try:
                verdict = client.generate_json(
                    build_frame_review_prompt(diff, stories), timeout=60.0,
                    model=model_for("frame_review"))
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
