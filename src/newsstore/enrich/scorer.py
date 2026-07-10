"""Dual score 패스(Phase 3) — 스토리에 risk/impact(0~3)를 LLM 1콜로 매겨 비파괴 저장.

설계: docs/analysis-design.md §7
- type-aware 게이트: standing/watch(금융자산) 상시 채점 / 그 외·emergent·unknown은 멤버수≥MIN.
- 결정론 validator 먼저(범위 0~3·필수키 risk/impact). reason은 advisory(결측→빈문자열).
- incremental(count>scored_count)은 store.get_stories_for_scoring가 필터, fail-soft(스토리 단위).
"""
from __future__ import annotations
import logging
import os

from . import topics
from .gemini import LLMError
from .model_config import model_for

log = logging.getLogger("newsstore.enrich.scorer")


def env_int(name: str, default: int) -> int:
    """캘리브레이션 정수 임계를 env로 오버라이드(기본=현 값). #7 — 재빌드 없이 튜닝.
    잘못된 값은 ValueError로 즉시 터뜨린다(FAIL-LOUD)."""
    return int(os.environ.get(name, default))


SCORE_MIN, SCORE_MAX = 0, 3              # risk/impact 범위(불변식 — 매직넘버 금지)
# 게이트 임계(#7). env로 튜닝 — 값은 라이브 점수/게이트 분포 보고 결정.
MATERIALITY_MIN_MEMBERS = env_int("NEWSSTORE_SCORE_MIN_MEMBERS", 2)   # 비금융자산/emergent 소스확증 게이트
ALWAYS_SCORE_TYPES = {"standing", "watch"}   # 금융자산 렌즈 = 게이트 면제(상시 채점)
MAX_REASON = 200                        # advisory reason 길이 상한
MEMBER_FALLBACK_N = 30                  # 요약 없을 때 입력으로 쓸 멤버 제목 수


def _is_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def should_score(lenses: list, t: dict, count: int, *,
                 min_members: int = MATERIALITY_MIN_MEMBERS) -> bool:
    """채점 자격(type-aware 게이트). standing/watch 렌즈가 하나라도 있으면 상시 통과,
    아니면(development/risk/sector/emergent/unknown-id) 멤버수>=min_members.

    unknown lens id(topics.yaml에 없음)는 KeyError로 안 터뜨리고 emergent로 강등(보수)."""
    for lid in (lenses or []):
        try:
            if topics.lens_type(t, lid) in ALWAYS_SCORE_TYPES:
                return True
        except KeyError:                # 드리프트: 모르는 id → 금융자산 승격 안 함(보수)
            continue
    return count >= min_members


def validate_score(raw: dict | None) -> dict | None:
    """결정론 검증(advisor-fit). risk/impact가 [SCORE_MIN,SCORE_MAX] 정수 아니면 None(드롭).
    reason은 advisory — 결측·비-str이면 빈문자열로 강등(점수는 보존)."""
    raw = raw or {}
    risk, impact = raw.get("risk"), raw.get("impact")
    if not (_is_int(risk) and SCORE_MIN <= risk <= SCORE_MAX):
        return None
    if not (_is_int(impact) and SCORE_MIN <= impact <= SCORE_MAX):
        return None
    rr, ir = raw.get("risk_reason"), raw.get("impact_reason")
    rr = rr.strip()[:MAX_REASON] if isinstance(rr, str) else ""
    ir = ir.strip()[:MAX_REASON] if isinstance(ir, str) else ""
    return {"risk": risk, "impact": impact, "risk_reason": rr, "impact_reason": ir}


def build_score_input(story: dict, members: list | None) -> str:
    """채점 입력 텍스트. 요약 패스 산출(summary·developments) 1차 → 없으면 멤버 제목 폴백.
    둘 다 비면 빈 문자열(호출자가 None 스킵)."""
    parts: list[str] = []
    if story.get("summary"):
        parts.append(str(story["summary"]))
    for d in (story.get("developments") or []):
        if isinstance(d, dict) and d.get("text"):
            parts.append(str(d["text"]))
    if not parts and members:
        for m in members[:MEMBER_FALLBACK_N]:
            if m.get("title"):
                parts.append(str(m["title"]))
    return "\n".join(parts)


def build_score_prompt(title: str, body: str) -> str:
    """dual-score 프롬프트. risk/impact 0~3 루브릭(spec §3, provisional). JSON만 출력."""
    return (
        "당신은 금융 뉴스 스토리의 위험도(risk)와 시장 영향(impact)을 채점하는 애널리스트다.\n"
        "두 차원은 다르다 — risk=악재·불확실성(하방·꼬리 리스크)의 강도, "
        "impact=시장이 움직일 크기(방향 무관).\n"
        "각각 0~3 정수로 채점:\n"
        "- risk: 0=리스크 무관, 1=경미(국지적 불확실성), 2=주목할 악재·불확실성(하방 가능), "
        "3=심각(시스템·지정학·꼬리 리스크).\n"
        "- impact: 0=시장영향 없음, 1=특정 종목/섹터 국지, 2=시장 일부 유의미 이동, "
        "3=광범위 큰 이동.\n"
        "출처(아래 스토리) 밖 추측 금지. 아래 JSON만 출력:\n"
        '{"risk":0,"impact":0,"risk_reason":"한 줄 근거","impact_reason":"한 줄 근거"}\n\n'
        f"제목: {title}\n내용:\n{body[:2000]}"
    )


def score_story(story: dict, members: list | None, client, *, timeout: float = 30.0) -> dict | None:
    """한 스토리 채점. 입력 비면 None(스킵). LLM 장애·무효 출력 → None(fail-soft)."""
    body = build_score_input(story, members)
    if not body.strip():
        return None                     # 멤버 0 + 요약 없음 → 스킵(크래시 금지)
    try:
        raw = client.generate_json(build_score_prompt(story.get("title", ""), body),
                                   timeout=timeout, model=model_for("score"))
    except LLMError as e:               # LLM 장애만 fail-soft(로깅) — 코드 버그는 전파(FAIL-LOUD)
        log.warning("score skip story %s (LLM): %s", story.get("id"), e)
        return None
    return validate_score(raw)


def run_score_pass(store, client, *, now, cutoff,
                   min_members: int = MATERIALITY_MIN_MEMBERS) -> dict:
    """열린 스토리(incremental: count>scored_count)를 게이트 후 채점·저장. fail-soft(스토리 단위).

    lens_pass/summary_pass 미러. 반환 {scored, gated, skipped}."""
    t = topics.load_topics()
    totals = {"scored": 0, "gated": 0, "skipped": 0}
    for st in store.get_stories_for_scoring(cutoff=cutoff):
        if not should_score(st.get("lenses", []), t, st.get("count", 0), min_members=min_members):
            totals["gated"] += 1
            continue
        sid = st["id"]
        try:
            members = None
            if not (st.get("summary") or st.get("developments")):
                members = store.get_story_members(sid)   # 요약 없을 때만 멤버 폴백 읽기
            res = score_story(st, members, client)
            if res is None:
                totals["skipped"] += 1
                continue
            store.save_story_score(sid, risk=res["risk"], impact=res["impact"],
                                   risk_reason=res["risk_reason"],
                                   impact_reason=res["impact_reason"],
                                   count=st.get("count"), now=now)
            totals["scored"] += 1
        except LLMError as e:
            log.warning("score skip story %s (LLM): %s", sid, e)
            totals["skipped"] += 1
        except Exception:               # fail-soft: 한 스토리 버그가 전체를 안 죽임(traceback 로그)
            log.exception("score unexpected error story %s", sid)
            totals["skipped"] += 1
    log.info("score pass: %s", totals)
    return totals
