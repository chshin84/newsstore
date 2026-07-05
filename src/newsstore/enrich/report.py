"""리포트 패스(리포트 탭 v1) — 스토리-그라운디드 섹션 리포트 + 백드롭 + 급부상.

스펙 docs/superpowers/specs/2026-06-30-report-tab-design.md §4·§5. 프레임은 frames.py(입력으로만).
top-K 랭킹은 UI(web/index.html storyRank)와 같은 정의: impact × 신선도(delta_time 최신성)."""
from __future__ import annotations
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from .frames import AXES, dev_arc
from .gemini import LLMError
from .model_config import model_for

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


MAX_HEADLINE = 100
MAX_LEAD = 300
MAX_ITEM_TEXT = 240
SECTION_NAMES = ("risk_triggered", "premium_triggered", "not_triggered", "watchpoints")
_TRIGGER_SECTIONS = ("risk_triggered", "premium_triggered")


def _frame_pole_ids(frame: dict) -> set[str]:
    return {p["id"] for axis in AXES for p in (frame.get(axis) or [])}


def validate_report(raw, *, frame: dict, input_story_ids: set[str]) -> dict | None:
    """결정론 검증(§5 표): 스키마·headline/lead 필수·인용 story_id 실재(환각 드롭)·
    pole_id가 standing frame에 실재·트리거 항목은 인용 필수(B). 실패 → None."""
    if not isinstance(raw, dict):
        return None
    headline = raw.get("headline")
    lead = raw.get("lead")
    if not (isinstance(headline, str) and headline.strip()
            and isinstance(lead, str) and lead.strip()):
        return None
    pole_ids = _frame_pole_ids(frame)
    sections_in = raw.get("sections")
    if not isinstance(sections_in, list):
        return None
    sections = []
    for sec in sections_in:
        if not (isinstance(sec, dict) and sec.get("name") in SECTION_NAMES):
            continue
        items = []
        for it in (sec.get("items") or []):
            if not (isinstance(it, dict) and isinstance(it.get("text"), str)
                    and it["text"].strip()):
                continue
            ids = [i for i in (it.get("story_ids") or [])
                   if isinstance(i, str) and i in input_story_ids]   # 환각 story 드롭
            pid = it.get("pole_id")
            if pid is not None and pid not in pole_ids:
                continue                                              # 환각 극 드롭
            if sec["name"] in _TRIGGER_SECTIONS and not ids:
                continue                                              # 트리거 = 인용 필수(B)
            items.append({"text": it["text"].strip()[:MAX_ITEM_TEXT],
                          "story_ids": ids, "pole_id": pid})
        sections.append({"name": sec["name"], "items": items})
    return {"headline": headline.strip()[:MAX_HEADLINE], "lead": lead.strip()[:MAX_LEAD],
            "sections": sections}


def build_backdrop_prompt(excerpts: list[str]) -> str:
    return (
        "당신은 매크로/교차자산 데스크 에디터다. 아래 오늘의 주요 스토리 발췌로 "
        "채권·순환매·원자재·매크로 백드롭을 4~6문장으로 합성하라. 예측·매수/매도 조언 금지, "
        "관측된 사실·내러티브만.\n" + "\n".join(excerpts[:40]) +
        '\n아래 JSON만 출력: {"text": "..."}')


STORY_DEV_MAX = 4             # 프롬프트에 실을 스토리당 최신 전개 수(근거는 전개에 있음 — #1)


def _story_line(s: dict) -> str:
    """프롬프트용 스토리 한 줄 — 제목 + 요약 + 전개 시간순 arc. 구체 사실(수치·고유명사)은
    요약이 아니라 developments에 있어 생성기·리뷰어가 같은 근거를 보고(#1), 시간순(→)이라
    나중이 앞을 갱신/되돌리는 인과를 읽게 한다(temporal). 순서 도출은 frames.dev_arc가 SSOT."""
    base = f'[{s["id"]}] {s.get("title", "")} :: {(s.get("summary") or "")[:200]}'
    arc = dev_arc(s, STORY_DEV_MAX)
    return base + (f" :: 전개(시간순): {arc}" if arc else "")


def _g(v):
    """숫자면 짧게 포맷(소수 정리), 아니면 빈 문자열."""
    try:
        return f"{float(v):g}"
    except (TypeError, ValueError):
        return ""


def price_context(price: dict | None) -> str:
    """가격 문서 → 교차검증용 한 줄(현재값·전일 등락·최근 추세). 뉴스 지연을 가격으로 보정하는 앵커.
    가격 없음/무효 → 빈 문자열(교차검증 생략)."""
    if not isinstance(price, dict):
        return ""
    close = _g(price.get("close"))
    if not close:
        return ""
    label = price.get("label") or price.get("symbol") or "가격"
    pct = price.get("percent_change")
    pct_s = f"{pct:+.2f}%" if isinstance(pct, (int, float)) else "?"
    trend = ""
    pts = [s.get("c") for s in (price.get("series") or [])[-5:] if isinstance(s.get("c"), (int, float))]
    if len(pts) >= 2:
        arrow = "하락" if pts[-1] < pts[0] else ("상승" if pts[-1] > pts[0] else "횡보")
        trend = f", 최근 {len(pts)}일 {arrow}({_g(pts[0])}→{_g(pts[-1])})"
    return f"{label} {close} (전일 {pct_s}{trend})"


def build_section_prompt(lens_id: str, frame: dict, stories: list[dict], backdrop: str,
                         reject_notes: str | None = None, price_ctx: str | None = None) -> str:
    import json as _json
    # 실 프레임은 updated_at(datetime) 등 비직렬화 필드를 포함 — 3축(AXES)만 추려 직렬화(C1)
    axes_only = {a: frame.get(a) or [] for a in AXES}
    lines = [_story_line(s) for s in stories]
    return (
        f"당신은 '{lens_id}' 자산군 데일리 리포트 에디터다. standing 프레임(주어진 것 — "
        "새 프레임을 만들지 마라)에 오늘 스토리를 대조하라.\n"
        f"프레임:\n{_json.dumps(axes_only, ensure_ascii=False)}\n"
        f"매크로 참고 맥락: {backdrop or '(없음)'}\n"
        "스토리(각 줄 맨 앞 [id]가 story_id):\n" + "\n".join(lines) + "\n"
        "서사 구조(가장 중요 — 시간순 나열 절대 금지): 리포트는 '지금 상태'에 서사를 부여하는 것이지 "
        "시간 흐름을 동등하게 다 설명하는 게 아니다. 전개(시간순)은 무엇이 무엇을 무효화했는지 읽는 "
        "'근거'일 뿐, 출력을 그 순서대로 나열하지 마라.\n"
        "  · 현재 상태와 그것을 만든 **결정적(가장 최근·유효한) 원인을 먼저** 써라 — 'B로 인해 지금 C다'.\n"
        "  · 이전 국면, 특히 나중에 부정·되돌려진 이벤트는 **부가 맥락으로 강등**하고 '~했으나 B로 "
        "무효화(negate)됨'처럼 현재 관점에서 마킹하라. 무효화된 것을 살아있는 것처럼 쓰지 마라.\n"
        "  · 가중치는 현재 상태에 크게 둔다. 지나간 국면은 압축.\n"
        "  · 좋은 예: 'B로 C 안정. (부가: A 발생했으나 B로 negate).'  나쁜 예: '현재 C인데, A 후 B 후 C가 됨.'\n"
        + (f"가격 교차검증(중요): 이 자산의 실제 가격 = {price_ctx}. 뉴스는 지연될 수 있다 — "
           "뉴스 서술의 방향과 가격이 어긋나면(예: 뉴스는 급등·공포인데 가격은 하락·안정) "
           "**가격을 '현재 상태'의 우선 근거**로 삼아 서술을 보정하라(가격이 이미 반영했으면 그게 현재다). "
           "가격이 뉴스를 확증하면 그 판단의 신뢰를 높여라. 단 가격은 '왜'를 말하지 않으니 인과는 스토리로.\n"
           if price_ctx else "") +
        "규칙: 매수·매도·비중 조언 금지(재료만). 트리거 판정은 반드시 해당 story_id 인용 — "
        "인용 스토리에 실제로 담긴 사실만 근거로 삼아라. 스토리에 없는 수치·고유명사·협의/계약 "
        "진전 등을 지어내 트리거 근거로 쓰지 마라(과인용 금지 — grounding 리뷰 기각의 주 원인). "
        "근거가 약하거나 스토리로 뒷받침되지 않으면 그 극은 트리거로 올리지 말고 watchpoints로 내려라. "
        "미발생(not_triggered)은 프레임 극 중 72h 트리거 없는 것. watchpoints는 관찰 지점 재확인.\n"
        + (f"직전 시도가 다음 사유로 기각됨: {reject_notes}. 이를 반영해 기각 사유를 해소해 "
           "재작성하라.\n" if reject_notes else "") +
        '아래 JSON만 출력: {"headline":"...","lead":"...","sections":['
        '{"name":"risk_triggered","items":[{"text":"...","story_ids":["..."],"pole_id":"..."}]},'
        '{"name":"premium_triggered","items":[...]},{"name":"not_triggered","items":[...]},'
        '{"name":"watchpoints","items":[...]}]}')


MAX_BACKDROP = 1200


def build_review_prompt(report: dict, stories: list[dict], frame: dict | None = None,
                        price_ctx: str | None = None) -> str:
    import json as _json
    # 리뷰어는 생성기와 '같은' 근거(전개·가격 포함)를 봐야 한다 — 덜 보면 정당한 항목을 오탐(#1).
    lines = [_story_line(s) for s in stories]
    # 출처는 셋: ① 인용 스토리(+전개) ② standing 프레임 극 ③ 실제 가격(현재 상태 근거).
    frame_block = ""
    if frame:
        axes_only = {a: frame.get(a) or [] for a in AXES}
        frame_block = ("standing 프레임(출처② — 리포트가 이 극을 restate/관찰하는 것은 근거 있음):\n"
                       f"{_json.dumps(axes_only, ensure_ascii=False)}\n")
    price_block = (f"실제 가격(출처③ — 뉴스 지연 보정용, 가격 기반 '현재 상태' 서술은 근거 있음): {price_ctx}\n"
                   if price_ctx else "")
    return (
        "당신은 리포트 심사자다(grounding+fit). 출처는 셋: ① 인용 스토리(제목·요약·전개) ② standing "
        "프레임 극 ③ 실제 가격. 기각 기준: (1) 항목 주장이 셋 **어디에도 없는** 새 사실·수치를 날조 "
        "(하나라도 있으면 근거 있음 — 프레임 극을 watchpoints/트리거로 옮기거나, 가격에 근거해 현재 "
        "상태를 서술하는 것은 정상), (2) 매수/매도/비중 조언 포함, (3) 인용 story와 실제로 무관한 "
        "억지 연결(과인용). 단순히 요약 앞부분에 없다고 날조로 속단 말고 전개·프레임·가격까지 확인하라.\n"
        + frame_block + price_block +
        f"리포트:\n{_json.dumps(report, ensure_ascii=False)}\n스토리:\n" + "\n".join(lines) + "\n"
        '아래 JSON만 출력: {"passed": true|false, "notes": "기각 사유 또는 빈 문자열"}')


def _review(client, report: dict, stories: list[dict], frame: dict | None = None,
            price_ctx: str | None = None) -> dict:
    """리뷰 콜 — 실패는 passed=false(통과 위장 금지, §5 표). frame=극 출처(#1), price_ctx=가격 출처."""
    try:
        v = client.generate_json(build_review_prompt(report, stories, frame, price_ctx), timeout=60.0,
                                 model=model_for("report_review"))
    except LLMError as e:
        return {"passed": False, "notes": f"리뷰 불가: {e}"}
    if not isinstance(v, dict) or not isinstance(v.get("passed"), bool):
        return {"passed": False, "notes": "리뷰 응답 형식 위반"}
    return {"passed": v["passed"], "notes": str(v.get("notes") or "")}


def run_report_pass(store, client, *, lens_ids: list[str], now, window=None,
                    context_lens_ids: list[str] | None = None,
                    price_ctx_by_lens: dict[str, str] | None = None) -> dict:
    """§4 파이프라인: 백드롭 → 섹션(렌즈별) → 급부상 → 저장. 프레임은 입력(frames.py 선행).
    리포트는 lens_ids(=자산)만 생성. context_lens_ids(비자산 포함)가 주어지면 백드롭 입력을
    그 넓은 풀에서 뽑아 정치·정책·경제 뉴스를 자산 리포트로 녹인다(#2 fold-in)."""
    cutoff = now - (window or timedelta(hours=72))
    totals = {"reported": 0, "skipped_empty": 0, "failed": 0}

    ctx_ids = context_lens_ids or lens_ids
    ctx_per_lens: dict[str, list[dict]] = {l: store.get_stories_for_report(l, cutoff=cutoff)
                                           for l in ctx_ids}
    for l in lens_ids:                                    # 방어: 리포트 렌즈가 context에 없으면 보충
        if l not in ctx_per_lens:
            ctx_per_lens[l] = store.get_stories_for_report(l, cutoff=cutoff)
    per_lens: dict[str, list[dict]] = {l: ctx_per_lens[l] for l in lens_ids}   # 리포트=자산만
    # 백드롭(생성 1콜 + grounding 리뷰 1콜 — §5 표: 16개 섹션 공통 입력이라 오염 전파 지점).
    # 생성·검증·리뷰 어느 것이든 실패 → 서두 생략 + 섹션 미주입(degrade), _backdrop 미저장(기존 유지).
    # 입력=context 풀(비자산 top3 포함) → 매크로/정치/정책이 백드롭 통해 자산 섹션에 녹음(#2).
    backdrop = ""
    all_top3 = [s for lid in ctx_ids for s in ctx_per_lens[lid][:3]]
    excerpts = [f'{s.get("title", "")}' for s in all_top3]
    if excerpts:
        try:
            raw = client.generate_json(build_backdrop_prompt(excerpts), timeout=60.0,
                                       model=model_for("report_backdrop"))
            text = (raw.get("text") or "").strip() if isinstance(raw, dict) else ""
            if text and len(text) <= MAX_BACKDROP:       # 결정론: 비어있지 않음·길이 상한
                verdict = _review(client, {"text": text}, all_top3)
                if verdict["passed"]:
                    backdrop = text
                    store.save_report("_backdrop", {"text": backdrop, "generated_at": now,
                                                    "review": verdict})
                else:
                    log.warning("backdrop 리뷰 기각(%s) — 서두 생략", verdict["notes"])
        except LLMError as e:
            log.warning("backdrop 실패 — 서두 생략: %s", e)

    top_k_ids: set[str] = set()
    selected: dict[str, list[dict]] = {}
    skipped: list[str] = []
    for lens_id in lens_ids:
        stories = per_lens[lens_id]
        if len(stories) < REPORT_MIN_STORIES:
            totals["skipped_empty"] += 1
            skipped.append(lens_id)
            continue
        top = select_top_k(stories, now, stratify=lens_id.endswith("_equity"))
        selected[lens_id] = top
        top_k_ids |= {s["id"] for s in top}

    def _one(doc_id, lens_id, frame, top, price_ctx="", criteria=None) -> str:
        """한 렌즈 리포트 생성. 반환 'reported'|'failed'(집계는 호출부 — 스레드 안전).
        price_ctx=이 자산 실제 가격(뉴스 지연 보정 교차검증). store.save_report만 부수효과."""
        try:
            raw = client.generate_json(build_section_prompt(lens_id, frame, top, backdrop, price_ctx=price_ctx),
                                       timeout=90.0, model=model_for("report_section"))
        except LLMError as e:
            log.warning("report %s: 생성 실패 — 기존 유지(§5b): %s", doc_id, e)
            return "failed"
        v = validate_report(raw, frame=frame, input_story_ids={s["id"] for s in top})
        if v is None:
            log.warning("report %s: 결정론 검증 실패 — 기존 유지", doc_id)
            return "failed"
        review = _review(client, v, top, frame, price_ctx)   # frame=극 출처(#1), price=가격 출처
        if not review["passed"]:
            # 리뷰 실패 → 실패 사유(notes)를 넣어 1회만 재생성·재검증·재리뷰(루프 금지, 개선 기회).
            # 재리뷰 통과 시 개선분으로 교체; 실패해도 기존 v를 그대로 저장(배지 계약 불변).
            try:
                raw2 = client.generate_json(
                    build_section_prompt(lens_id, frame, top, backdrop,
                                         reject_notes=review["notes"], price_ctx=price_ctx),
                    timeout=90.0, model=model_for("report_section"))
                v2 = validate_report(raw2, frame=frame, input_story_ids={s["id"] for s in top})
                if v2 is not None:
                    review2 = _review(client, v2, top, frame, price_ctx)
                    if review2["passed"]:
                        v, review = v2, review2         # 개선분 채택
            except LLMError as e:                       # 재시도 콜 실패 → 기존 v 유지(전파 금지)
                log.warning("report %s: 재시도 생성 실패 — 기존 결과 유지: %s", doc_id, e)
        doc = {**v, "topic": lens_id, "generated_at": now,
               "frame_updated_at": frame.get("updated_at"), "review": review}
        if criteria:
            doc["criteria"] = criteria
        store.save_report(doc_id, doc)
        return "reported"

    # 5a: 렌즈별 리포트를 유계 동시성으로 병렬화(#45 벽시간 절감). 동시성=1이면 직렬과 동일(가역).
    # rising은 top_k 확정 의존이라 팬아웃 뒤 순차(§3.5 순서). save_report만 부수효과라 스레드 안전.
    conc = max(1, int(os.environ.get("NEWSSTORE_REPORT_CONCURRENCY", "6")))
    pctx = price_ctx_by_lens or {}
    units = [(lid, lid, store.get_frame(lid), top, pctx.get(lid, "")) for lid, top in selected.items()]
    with ThreadPoolExecutor(max_workers=min(conc, max(1, len(units)))) as ex:
        for r in ex.map(lambda u: _one(*u), units):
            totals[r] += 1

    # 급부상 — 전 렌즈 top-K 확정 후(§3.5 순서 의존)
    all_stories = {s["id"]: s for ss in per_lens.values() for s in ss}
    rising = select_rising(list(all_stories.values()), top_k_ids=top_k_ids, now=now)
    if len(rising) >= REPORT_MIN_STORIES:
        totals[_one("rising", "rising", {}, rising, price_ctx="",
                    criteria="최근 24h 델타 밀도 상위 + 타 리포트 top-K 미등장(결정론)")] += 1
    # 스킵 신호 발행(§4) — UI가 "아직 생성 전/오늘 스토리 부족" vs "갱신 지연"을 구분.
    # 스킵 0건이어도 빈 배열로 덮어써 전 런의 스킵 잔재를 제거한다(멱등).
    store.save_report("_skips", {"lenses": skipped, "generated_at": now})
    log.info("report pass: %s", totals)
    return totals
