"""스토리 아티클 생성 패스(Phase 4) — headline/lead/article(bullet) + 전일대비 ref를
비파괴로 저장한다. **developments는 절대 안 건드림**(summary 단독 writer) — 자기 필드만 merge.

설계: docs/superpowers/specs/2026-06-29-phase4-story-report-ui-design.md
순서: cluster → summary(+event_time) → score(risk/impact) → article(마지막).
"""
from __future__ import annotations
import logging
from datetime import timedelta

from .gemini import LLMError
from .model_config import model_for

log = logging.getLogger("newsstore.enrich.article")

MAX_BULLETS = 6                 # article bullet 상한
MAX_HEADLINE = 100              # 헤드라인 길이 상한
MAX_LEAD = 300                  # 리드 길이 상한
MAX_BULLET_LEN = 240            # bullet 1개 길이 상한
ARTICLE_MAX_MEMBERS = 40        # LLM에 먹이는 멤버 발췌 상한(토큰)
REF_WINDOW = timedelta(hours=24)   # 전일대비 ref 롤링 창
IMPACT_PRIOR = 1                # 미채점 스토리 정렬 prior(UI와 공유 의미 — UI는 자체 상수)


def _nonempty_str(x):
    return isinstance(x, str) and x.strip()


def validate_article(raw: dict | None) -> dict | None:
    """결정론 검증. 필수키 headline/lead/article(비어있지 않은 str·list[str]). 길이·개수 상한.
    실패 → None(스토리 스킵)."""
    raw = raw or {}
    headline, lead, article = raw.get("headline"), raw.get("lead"), raw.get("article")
    if not _nonempty_str(headline) or not _nonempty_str(lead):
        return None
    if not isinstance(article, list):
        return None
    bullets = [b.strip()[:MAX_BULLET_LEN] for b in article if _nonempty_str(b)][:MAX_BULLETS]
    if not bullets:
        return None
    return {"headline": headline.strip()[:MAX_HEADLINE],
            "lead": lead.strip()[:MAX_LEAD], "article": bullets}


def compute_ref(*, now, risk, impact, risk_ref, impact_ref, score_ref_at):
    """전일대비 기준 스냅샷(24h 롤링). 미채점(risk/impact None)이면 갱신 안 함.
    score_ref_at 없거나 REF_WINDOW 지났으면 현재 점수를 ref로 전진, 아니면 유지."""
    if risk is None or impact is None:
        return risk_ref, impact_ref, score_ref_at
    if score_ref_at is None or (now - score_ref_at) >= REF_WINDOW:
        return risk, impact, now
    return risk_ref, impact_ref, score_ref_at


def build_article_input(story: dict, members: list | None) -> str:
    """생성 입력. summary·developments(text) 1차 → 없으면 멤버 제목 폴백. 둘 다 비면 ''."""
    parts: list[str] = []
    if story.get("summary"):
        parts.append(str(story["summary"]))
    for d in (story.get("developments") or []):
        if isinstance(d, dict) and d.get("text"):
            parts.append(str(d["text"]))
    if not parts and members:
        # 멤버 폴백은 최신순으로 — get_story_members는 published_at asc라 앞에서 자르면
        # '가장 오래된 40'이 되어 최신 전개가 통째로 빠진다('최신 전개 전면' 헤드라인 계약 §스펙).
        for m in list(reversed(members))[:ARTICLE_MAX_MEMBERS]:
            if m.get("title"):
                parts.append(str(m["title"]))
    return "\n".join(parts)


def build_article_prompt(title: str, impact, body: str) -> str:
    """헤드라인(가장 최신 전개 주도)+리드(1~2문장)+bullet 아티클. impact는 텍스트 입력 아님(톤 참고만)."""
    return (
        "당신은 한국어 금융 뉴스 스토리를 합성하는 에디터다. 아래 스토리(같은 사건 클러스터)의 "
        "요약·전개를 읽고 투자자용 보고서를 만들어라.\n"
        "- headline: 가장 최신 전개를 전면에 둔 한 줄 제목(≤80자). 단정적이되 출처 밖 추측 금지.\n"
        "- lead: 핵심과 '왜 중요한가'를 1~2문장으로.\n"
        "- article: 핵심 근거를 bullet 리스트로(최대 6개, 각 한 줄). 본문에서 합리적으로 추론한 "
        "맥락을 채우되 사실에 근거. 마지막 bullet은 '변수/리스크'를 다뤄도 좋다.\n"
        "아래 JSON만 출력:\n"
        '{"headline":"...","lead":"...","article":["...", "..."]}\n\n'
        f"제목: {title}\n내용:\n{body[:3000]}"
    )


def article_story(story: dict, members: list | None, client, *, now,
                  timeout: float = 30.0) -> dict | None:
    """한 스토리 생성. 입력 비면 None. LLM 장애·무효 출력 → None(fail-soft). ref 스냅샷 포함."""
    body = build_article_input(story, members)
    if not body.strip():
        return None
    try:
        raw = client.generate_json(
            build_article_prompt(story.get("title", ""), story.get("impact"), body),
            timeout=timeout, model=model_for("article"))
    except LLMError as e:                   # LLM 장애만 fail-soft(로깅) — 코드 버그는 전파(FAIL-LOUD)
        log.warning("article skip story %s (LLM): %s", story.get("id"), e)
        return None
    v = validate_article(raw)
    if v is None:
        return None
    rr, ir, ra = compute_ref(now=now, risk=story.get("risk"), impact=story.get("impact"),
                             risk_ref=story.get("risk_ref"), impact_ref=story.get("impact_ref"),
                             score_ref_at=story.get("score_ref_at"))
    return {**v, "risk_ref": rr, "impact_ref": ir, "score_ref_at": ra}


def run_article_pass(store, client, *, now, cutoff) -> dict:
    """열린 스토리(incremental: count>articled_count)에 보고서 생성·저장. fail-soft(스토리 단위)."""
    totals = {"articled": 0, "skipped": 0}
    for st in store.get_stories_for_article(cutoff=cutoff):
        sid = st["id"]
        try:
            members = None
            if not (st.get("summary") or st.get("developments")):
                members = store.get_story_members(sid)   # 요약 없을 때만 멤버 폴백
            res = article_story(st, members, client, now=now)
            if res is None:
                totals["skipped"] += 1
                continue
            store.save_story_article(sid, headline=res["headline"], lead=res["lead"],
                                     article=res["article"], risk_ref=res["risk_ref"],
                                     impact_ref=res["impact_ref"], score_ref_at=res["score_ref_at"],
                                     count=st.get("count"), now=now)
            totals["articled"] += 1
        except LLMError as e:
            log.warning("article skip story %s (LLM): %s", sid, e)
            totals["skipped"] += 1
        except Exception:                # fail-soft: 한 스토리 버그가 전체를 안 죽임(traceback 로그)
            log.exception("article unexpected error story %s", sid)
            totals["skipped"] += 1
    log.info("article pass: %s", totals)
    return totals
