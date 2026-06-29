"""렌즈 패스 — 열린 스토리를 멤버 신호로 분류해 stories.lenses[] 채움(Stage1 결정론)."""
from __future__ import annotations
import logging
from . import topics
from .lens_classify import classify_stage1

log = logging.getLogger("newsstore.enrich.lens_pass")


def run_lens_pass(store, *, now, cutoff) -> int:
    t = topics.load_topics()
    rows = store.get_stories_for_lensing(cutoff=cutoff)
    n = 0
    for r in rows:
        sig = store.get_story_member_signals(r.get("member_ids", []))   # 배치 집계(store 계약)
        langs = sig["languages"]
        tags = sig["tags"]                       # flat tags(tickers+entities+topics 혼재) — 교집합이 거름
        lenses = classify_stage1(
            t, asset_hints=sig["asset_hints"], tickers=tags, entities=tags, topics=tags,
            language=("ko" if langs and langs.count("ko") >= len(langs) / 2 else "en"),
            keyword_text=sig["keyword_text"])
        store.save_story_lenses(r["id"], lenses)
        n += 1
    log.info("lens pass: %d stories classified", n)
    return n
