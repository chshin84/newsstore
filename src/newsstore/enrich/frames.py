"""프레임 패스(리포트 탭 v1) — standing 프레임(risk/premium/watchpoints) 이월·재심.

스펙 docs/superpowers/specs/2026-06-30-report-tab-design.md §3: 전용 패스가 어제 프레임을
입력으로 전체 극을 재심(유지/수정/탈락 — 나이 기반 밀어내기 없음), diff(신규/수정)만
grounding 리뷰. 실패 시 어제 프레임 유지(이월 폴백)."""
from __future__ import annotations
import json
import logging
import os
from datetime import datetime, timedelta, timezone

from .gemini import LLMError
from .model_config import model_for

log = logging.getLogger("newsstore.enrich.frames")

FRAME_MAX_POLES = 5           # 축당 극 상한(결정⑧ — 무상한이면 리포트 입력 폭탄)
FRAME_MAX_INPUT_STORIES = 30  # 프레임 패스 입력 캡(§3 — 프레임 패스가 새 토큰 폭탄 금지)
MAX_POLE_TEXT = 120
AXES = ("risks", "premiums", "watchpoints")
MARKET_ID = "_market"            # 글로벌 시장 프레임(#44) 문서 id — 렌즈 아님, 별도 생성
MARKET_SAMPLE_PER_LENS = 2       # 시장 프레임 입력: 렌즈당 top-N 스토리
MARKET_MAX_STORIES = 24          # 시장 프레임 입력 캡(토큰 폭탄 차단)
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


def build_market_prompt(stories: list[dict]) -> str:
    """글로벌 시장 프레임(#44) — 전 자산군 스토리로 '시장 전체가 가장 두려워할 것'을 RAS로 도출.
    개별 렌즈가 아니라 자산군을 가로지르는(interconnectivity) 구조적 급소 우선."""
    lines = []
    for s in stories[:MARKET_MAX_STORIES]:
        arc = dev_arc(s)                                 # 전개 시간순 — 인과·되돌림 신호
        tail = f" :: 전개(시간순): {arc}" if arc else ""
        lines.append(f'[{s["id"]}] {s.get("title", "")} :: {(s.get("summary") or "")[:150]}{tail}')
    return (
        "당신은 전 자산군을 가로지르는 매크로/시스템 리스크 데스크 총괄이다.\n"
        "센티먼트 근사 준거 — 말이 아니라 '비용을 치른 행동(RAS)'. 아래는 오늘 전 자산군 주요 스토리다.\n"
        "시간적 인과: 각 스토리 '전개(시간순)'은 →로 오래된→최신. 나중 전개가 앞을 갱신·반박·되돌리면 "
        "현재(최신) 상태가 기준 — 되돌림(A→B→A 허위→B 되돌림)이 있으면 그 되돌림이 핵심 신호다.\n"
        "임무: 개별 자산군이 아니라 '시장 전체'가 지금 터지면 가장 두려워할 소수·고강도 시나리오를 뽑아라 — "
        "여러 자산군을 하나로 꿰는 구조적 급소(예: 하이퍼스케일러 capex 철회가 반도체·주식·전력을 동시에 "
        "흔드는 급). 자산군 교차로 연결되는(interconnectivity) 것을 우선. 장황 나열 금지, 강도로 골라라.\n"
        "3축: risks(시장급 아킬레스건), premiums(시장 전체를 떠받치는 컨센서스), watchpoints(트리거 관찰점).\n"
        "스토리(맨 앞 [id]가 story_id):\n" + "\n".join(lines) + "\n"
        f"축당 최대 {FRAME_MAX_POLES}개. 각 극에 achilles_kind('words_deeds'|'structural')·"
        "evidence_dev_ids(위 목록 실재 id).\n"
        '아래 JSON만: {"risks":[{"id":"...","text":"...","achilles_kind":"words_deeds|structural",'
        '"evidence_dev_ids":["..."]}],"premiums":[...],"watchpoints":[...]}')


_MIN_DT = datetime.min.replace(tzinfo=timezone.utc)


def _dev_time(d: dict):
    return d.get("delta_time") or d.get("time")


def _fmt_dev_time(t) -> str:
    try:
        return t.strftime("%m-%d")                       # datetime(Firestore Timestamp)
    except AttributeError:
        return ""


def dev_arc(story: dict, n: int = 5) -> str:
    """스토리 전개를 시간순(오래된→최신)으로 최근 n개 — 시간적 인과·되돌림 추론용.
    나중 항목이 앞 항목을 갱신/반박/되돌릴 수 있어 '순서 자체가 신호'다(평면 나열 금지)."""
    devs = [d for d in (story.get("developments") or []) if d.get("text")]
    try:
        devs = sorted(devs, key=lambda d: _dev_time(d) or _MIN_DT)   # 오래된→최신
    except TypeError:
        pass                                             # 시간 타입 혼합이면 원순서 유지
    parts = []
    for d in devs[-n:]:
        mark, txt = _fmt_dev_time(_dev_time(d)), (d.get("text") or "")[:90]
        parts.append(f"({mark}) {txt}" if mark else txt)
    return " → ".join(parts)


def build_frame_prompt(lens_id: str, old: dict, stories: list[dict], market: dict | None = None,
                       reject_notes: str | None = None) -> str:
    """이월 재심 프롬프트 — 어제 극 전부 + 최근 스토리(캡). 유지 판단에도 근거 검토 요구(§3 재심 계약).

    market: 글로벌 시장 프레임(#44) — 주어지면 시장급 공포를 컨텍스트로 주입(interconnectivity 입구).
    reject_notes: 직전 시도의 diff-grounding 기각 사유 — 있으면 재작성 지시를 임무 뒤에 덧붙인다(1회 재시도)."""
    # 실 프레임은 updated_at(datetime) 등 비직렬화 필드를 포함 — 3축(AXES)만 추려 직렬화(C1)
    axes_only = {a: (old or {}).get(a) or [] for a in AXES}
    lines = []
    for i, s in enumerate(stories[:FRAME_MAX_INPUT_STORIES]):
        arc = dev_arc(s)                                 # 전개 시간순(오래된→최신) — 인과·되돌림 신호
        tail = f" :: 전개(시간순): {arc}" if arc else ""
        lines.append(f'{i}. [{s["id"]}] {s.get("title", "")} :: {(s.get("summary") or "")[:150]}{tail}')
    market_block = ""
    if market:
        mr = [p["text"] for p in (market.get("risks") or []) if p.get("text")][:5]
        if mr:
            market_block = ("오늘의 글로벌 시장 프레임(전 자산군 공통 공포 — 이 자산군에 어떻게 사영되는지 "
                            "고려하되 중복 나열 말고 이 렌즈 고유 급소에 집중):\n- " + "\n- ".join(mr) + "\n")
    return (
        f"당신은 '{lens_id}' 자산군의 standing 프레임을 유지하는 시니어 애널리스트다.\n"
        + market_block +
        "센티먼트 근사 준거 — 말이 아니라 '비용을 치른 행동(RAS)'을 본다: 브로커 목표가 상향·"
        "낙관 논평(말)이 아니라, 스토리 전개(developments)에 담긴 비가역 행동 — capex 감축·"
        "잉여자원 매도·감원·정점 증자·비중 축소 — 을 근거로 삼아라. 서술 톤과 행동의 부호가 "
        "어긋나는 곳(톤↑·행동↓ 또는 그 반대)이 숨은 공포의 시그니처다.\n"
        "시간적 인과(가장 중요): 각 스토리의 '전개(시간순)'은 →로 오래된→최신이다. 나중 전개가 "
        "앞 전개를 갱신·반박·되돌리면 **현재(최신) 상태**를 극의 기준으로 삼아라 — 어제 급변이 "
        "오늘 진정/반전됐으면 '진정/반전'이 현재다(옛 급변을 오늘 것처럼 쓰지 마라). 가장 중요한 "
        "신호는 종종 **되돌림**이다: 사건 A→여파 B→A가 허위로 판명→B 되돌림이면, 극은 'A 자체'가 "
        "아니라 'A 허위 판명에 따른 B 되돌림'이어야 한다. **무효화(negate)된 이전 국면을 살아있는 "
        "극으로 남기지 마라** — 극은 지금 유효한 것만. 시차가 미세하면 강행 말고 병존.\n"
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
        + (f"직전 시도가 다음 사유로 기각됨: {reject_notes}. 이를 반영해 기각 사유를 해소한 극으로 "
           "재작성하라.\n" if reject_notes else "") +
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


def _ensure_market_frame(store, client, per_lens: dict, *, now, min_age) -> dict:
    """글로벌 시장 프레임(#44) 생성·저장. age-gate(신선하면 재사용). 전 렌즈 top 스토리 샘플로 1콜.
    실패(콜·검증)는 어제 판 유지(fail-soft). 반환=시장 프레임(렌즈 프롬프트 주입용)."""
    old = store.get_frame(MARKET_ID)
    ua = (old or {}).get("updated_at")
    if ua is not None and (now - ua) < min_age:
        return old                                      # 신선 → 재사용(콜 0)
    sample = [s for ss in per_lens.values() for s in ss[:MARKET_SAMPLE_PER_LENS]][:MARKET_MAX_STORIES]
    if not sample:
        return old or {}
    try:
        raw = client.generate_json(build_market_prompt(sample), timeout=60.0,
                                   model=model_for("frame_gen"))
    except LLMError as e:
        log.warning("market frame: LLM 실패 — 어제 판 유지: %s", e)
        return old or {}
    frame = validate_frame(raw, input_story_ids={s["id"] for s in sample if s.get("id")})
    if frame is None:
        log.warning("market frame: 결정론 검증 실패 — 어제 판 유지")
        return old or {}
    store.save_frame(MARKET_ID, frame, now=now)
    return frame


def _attempt_frame(client, lens_id, old, stories, market, *, reject_notes=None):
    """1회 생성→결정론 검증→diff→diff-grounding 리뷰. 반환 (frame|None, verdict|None).

    frame None = LLM 콜 실패 또는 결정론 검증 실패(어제 판 유지 대상, fail-soft).
    verdict None = diff 없음(리뷰 불요 — frame 그대로 저장 가능).
    verdict dict = 리뷰 결과(호출부가 passed 확인). reject_notes는 재시도 프롬프트에 실린다."""
    try:
        raw = client.generate_json(
            build_frame_prompt(lens_id, old, stories, market=market, reject_notes=reject_notes),
            timeout=60.0, model=model_for("frame_gen"))
    except LLMError as e:
        log.warning("frame pass %s: LLM 실패 — 어제 판 유지: %s", lens_id, e)
        return None, None
    frame = validate_frame(raw, input_story_ids={s["id"] for s in stories if s.get("id")})
    if frame is None:
        log.warning("frame pass %s: 결정론 검증 실패 — 어제 판 유지", lens_id)
        return None, None
    diff = frame_diff(old, frame)
    if not diff:
        return frame, None                              # 유지 극뿐 → 리뷰 0콜
    try:
        verdict = client.generate_json(
            build_frame_review_prompt(diff, stories), timeout=60.0,
            model=model_for("frame_review"))
    except LLMError as e:
        log.warning("frame pass %s: 리뷰 콜 실패 — 어제 판 유지: %s", lens_id, e)
        return None, None
    return frame, verdict


def run_frame_pass(store, client, *, lens_ids: list[str], now, window=None,
                   context_lens_ids: list[str] | None = None) -> int:
    """렌즈별 프레임 재심. 실패(콜·검증·리뷰 기각)는 어제 판 유지(fail-soft, §5(c)). 반환=갱신 수.

    #44: 시작에 글로벌 시장 프레임을 먼저 생성해 각 렌즈 프롬프트에 주입(interconnectivity).
    개별 프레임은 lens_ids(=자산)만 생성하되, context_lens_ids(비자산 포함)가 주어지면 시장
    프레임 샘플을 그 넓은 풀에서 뽑아 정치·정책·경제 공포를 자산 프레임으로 녹인다(#2 fold-in).
    6a age-gate: updated_at이 min_age(env NEWSSTORE_FRAME_MIN_AGE_HOURS, 기본 20h) 이내로
    신선하면 재심 스킵(#45 완화 — 프레임은 준정적, 리포트 4×/일마다 재생성할 필요 없음)."""
    cutoff = now - (window or timedelta(hours=72))
    min_age = timedelta(hours=float(os.environ.get("NEWSSTORE_FRAME_MIN_AGE_HOURS", "20")))
    # 사전수집 — 시장 프레임은 context 풀(비자산 포함), 개별 프레임은 lens_ids만. read 공유(중복 방지).
    ctx_ids = context_lens_ids or lens_ids
    per_lens = {lid: store.get_stories_for_report(lid, cutoff=cutoff) for lid in ctx_ids}
    for lid in lens_ids:                                 # 방어: 자산 렌즈가 context에 없으면 보충
        if lid not in per_lens:
            per_lens[lid] = store.get_stories_for_report(lid, cutoff=cutoff)
    market = _ensure_market_frame(store, client, per_lens, now=now, min_age=min_age)
    n = 0
    failures: list[dict] = []          # IB3: silent-stale 실패 렌즈 귀속(어제 판 조용히 유지 → stale 원인)
    for lens_id in lens_ids:
        old = store.get_frame(lens_id)
        ua = (old or {}).get("updated_at")
        if ua is not None and (now - ua) < min_age:    # 신선 → 스킵(콜 0, 실패 아님)
            continue
        stories = per_lens[lens_id]
        frame, verdict = _attempt_frame(client, lens_id, old, stories, market)
        if frame is None:
            failures.append({"lens_id": lens_id, "reason": "attempt_failed"})   # 콜·검증 실패
            continue                                    # 콜·검증 실패 → 어제 판 유지(fail-soft)
        if verdict is not None and not (isinstance(verdict, dict) and verdict.get("passed") is True):
            # diff-grounding 기각 → 실패 사유(notes)를 넣어 워커가 1회만 재작성·재검증·재리뷰(루프 금지)
            notes = (verdict or {}).get("notes")
            log.info("frame pass %s: diff-grounding 기각(%s) — 1회 재생성", lens_id, notes)
            frame, verdict = _attempt_frame(client, lens_id, old, stories, market, reject_notes=notes)
            if frame is None:
                failures.append({"lens_id": lens_id, "reason": "retry_failed"})  # 재생성 콜·검증 실패
                continue                                # 재생성 콜·검증 실패 → 어제 판 유지
            if verdict is not None and not (isinstance(verdict, dict) and verdict.get("passed") is True):
                log.warning("frame pass %s: 재시도도 diff-grounding 기각 — 어제 판 유지", lens_id)
                failures.append({"lens_id": lens_id, "reason": "retry_rejected"})  # 재시도도 기각
                continue
        store.save_frame(lens_id, frame, now=now)
        n += 1
    # IB3: silent-stale 실패 렌즈 발행(_market과 동일 채널 — 메타 프레임 doc). UI가 stale 원인 귀속. 멱등.
    # generated_at은 report _failures와 동일 필드로 두어 소비자(UI)가 두 채널을 같은 shape로 읽게 한다.
    store.save_frame("_failures", {"lenses": failures, "generated_at": now}, now=now)
    log.info("frame pass: %d/%d updated failures=%s", n, len(lens_ids), failures)
    return n
