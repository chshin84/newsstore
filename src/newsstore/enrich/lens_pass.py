"""렌즈 패스 — 열린 스토리를 멤버 신호로 분류해 stories.lenses[] 채움(Stage1 결정론)."""
from __future__ import annotations
import logging
from . import topics
from .lens_classify import classify_stage1, classify_stage2

log = logging.getLogger("newsstore.enrich.lens_pass")


def run_lens_pass(store, *, now, cutoff, client=None) -> int:
    """열린 스토리 분류 → stories.lenses[]. client 있으면 LLM 1차 분류(asset_hint prior),
    없으면 결정론 prior만. LLM 빈 결과·장애 시 prior로 폴백(fail-soft)."""
    t = topics.load_topics()
    rows = store.get_stories_for_lensing(cutoff=cutoff)
    n = 0
    for r in rows:
        sig = store.get_story_member_signals(r.get("member_ids", []))   # 배치 집계(store 계약)
        langs = sig["languages"]
        tags = sig["tags"]                       # flat tags(tickers+entities+topics 혼재) — 교집합이 거름
        prior = classify_stage1(
            t, asset_hints=sig["asset_hints"], tickers=tags, entities=tags, topics=tags,
            language=("ko" if langs and langs.count("ko") >= len(langs) / 2 else "en"),
            keyword_text=sig["keyword_text"])
        if client is not None:
            lenses = classify_stage2(
                t, client, story_text=r.get("title", "") + "\n" + sig["keyword_text"][:1200],
                candidates=prior)
            if not lenses:                       # LLM 빈 결과 → prior 유지(보수)
                lenses = prior
        else:
            lenses = prior
        store.save_story_lenses(r["id"], lenses)
        n += 1
    log.info("lens pass: %d stories classified (llm=%s)", n, client is not None)
    return n
