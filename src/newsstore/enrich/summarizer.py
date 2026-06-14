"""스토리 요약 패스(플랜 A) — 순수 로직 + 오케스트레이션.

새 멤버가 생긴 스토리를 골라 flash-lite로 title/summary/developments를 만들고
stories 문서에 merge 저장한다. time·latest는 LLM이 아니라 코드가 도출(grounding).
"""
from __future__ import annotations
import logging

from ..contracts.ports import LLMClient
from .gemini import LLMError

log = logging.getLogger("newsstore.enrich.summarizer")

SUMMARY_MAX_MEMBERS = 200    # LLM에 먹이는 멤버 상한(토큰/출력품질). summary_count는 전체수(D3).
MAX_TITLE = 80


def _excerpt_len(n_members: int) -> int:
    """멤버가 많으면 발췌를 짧게(입력 토큰 통제)."""
    return 80 if n_members > 40 else 200


def build_summary_prompt(members: list[dict], *, omitted: int = 0) -> str:
    """members: published_at asc, 각 {title,body,source,published_at}. 번호를 매겨 프롬프트화.

    omitted>0이면 이 목록이 최신 일부이고 그 이전 omitted건이 생략됐음을 LLM에 알린다(D4 — 절단
    인지 없이 first_idx 오배치 방지)."""
    elen = _excerpt_len(len(members))
    lines = []
    if omitted > 0:
        lines.append(f"(참고: 아래는 최신 {len(members)}건이며 그 이전 {omitted}건은 생략됨. "
                     "first_idx는 아래 번호 기준.)")
    for i, m in enumerate(members):
        title = (m.get("title") or "").strip()
        body = (m.get("body") or "").strip()[:elen]
        source = m.get("source") or "?"
        lines.append(f"{i}. [{source}] {title} :: {body}")
    return (
        "당신은 한국어 금융 뉴스 스토리를 추적하는 에디터다. 아래는 한 스토리(같은 사건 클러스터)에 "
        "속한 기사들을 시간순(오래된→최신)으로 번호를 매긴 목록이다. 전체 흐름을 전개(development) "
        "단위로 묶어 요약하라. 의미상 같은 전개의 다른 표현(출처가 달라도)은 하나의 전개로 합쳐라. "
        "최근 전개에 가중치를 둬라. 사실만 쓰고 출처 밖 내용·추측은 금지한다.\n"
        "각 전개에 first_idx(그 전개를 처음 보도한 기사 번호)와 source_count(그 전개를 다룬 서로 "
        "다른 출처 수 추정)를 넣어라. 아래 JSON만 출력:\n"
        '{"title":"스토리 캐노니컬 제목(≤40자)","summary":"2~3문장 요약(최근 가중)",'
        '"developments":[{"text":"전개 한 줄","first_idx":0,"source_count":1}]}\n\n'
        + "\n".join(lines)
    )


def _is_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def validate_summary(raw: dict, *, n_members: int) -> dict | None:
    """결정론 검증(advisor-fit). 파싱/필수키 실패면 None(스토리 스킵). 형식만, 환각은 안 봄."""
    raw = raw or {}
    title = raw.get("title")
    summary = raw.get("summary")
    devs = raw.get("developments")
    if not isinstance(title, str) or not title.strip():
        return None
    if not isinstance(summary, str) or not summary.strip():
        return None
    if not isinstance(devs, list):
        return None
    out = []
    for d in devs:
        if not isinstance(d, dict):
            continue
        text = d.get("text")
        idx = d.get("first_idx")
        if not isinstance(text, str) or not text.strip():
            continue
        if not _is_int(idx) or not (0 <= idx < n_members):
            continue                                   # 범위 밖 → 드롭(grounding 불가)
        sc = d.get("source_count")
        sc = sc if _is_int(sc) and sc >= 1 else 1
        out.append({"text": text.strip(), "first_idx": idx,
                    "source_count": min(sc, n_members)})
    return {"title": title.strip()[:MAX_TITLE], "summary": summary.strip(),
            "developments": out}


def summarize_story(members_all: list[dict], client: LLMClient, *, now=None,
                    max_members: int = SUMMARY_MAX_MEMBERS) -> dict | None:
    """전체 멤버 중 최신 max_members건을 LLM에 먹여 요약. 반환 dict 또는 None(스킵)."""
    if not members_all:
        return None
    members_fed = members_all[-max_members:]
    n = len(members_fed)
    omitted = len(members_all) - n
    raw = client.generate_json(build_summary_prompt(members_fed, omitted=omitted), timeout=30.0)
    v = validate_summary(raw, n_members=n)
    if v is None:
        return None
    devs = []
    for d in v["developments"]:
        pub = members_fed[d["first_idx"]].get("published_at")
        if pub is None:                                # 시각 grounding 불가 → 드롭
            continue
        devs.append({"text": d["text"], "time": pub, "source_count": d["source_count"]})
    devs.sort(key=lambda x: x["time"], reverse=True)   # 안정정렬, time DESC(위=최신)
    latest = devs[0]["text"] if devs else ""
    return {"title": v["title"], "summary": v["summary"], "latest": latest,
            "developments": devs, "summary_count": len(members_all)}   # D3: 전체수


def run_summary_pass(store, client: LLMClient, *, limit: int, now,
                     max_members: int = SUMMARY_MAX_MEMBERS) -> dict:
    """새 멤버가 생긴 스토리(최신 limit개 스캔)를 요약해 저장. fail-soft(스토리 단위)."""
    totals = {"summarized": 0, "skipped": 0}
    for st in store.get_stories_needing_summary(limit):
        sid = st["id"]
        try:
            members = store.get_story_members(sid)
            if not members:
                totals["skipped"] += 1
                continue
            res = summarize_story(members, client, now=now, max_members=max_members)
            if res is None:
                totals["skipped"] += 1
                continue
            store.save_story_summary(sid, title=res["title"], summary=res["summary"],
                                     latest=res["latest"], developments=res["developments"],
                                     summary_count=res["summary_count"], now=now)
            totals["summarized"] += 1
        except LLMError as e:
            log.warning("summary skip story %s (LLM): %s", sid, e)
            totals["skipped"] += 1
        except Exception:                              # fail-soft: 한 스토리 실패가 전체를 안 죽임
            # 예기치 못한 예외는 traceback까지 로그(코드 버그를 'skip'으로 조용히 묻지 않게 — FAIL-LOUD)
            log.exception("summary unexpected error story %s", sid)
            totals["skipped"] += 1
    log.info("summary pass: %s", totals)
    return totals
