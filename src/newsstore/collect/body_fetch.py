from __future__ import annotations
import logging
import time
import httpx
from bs4 import BeautifulSoup
from .fetcher import DEFAULT_HEADERS

log = logging.getLogger("newsstore.collect.body_fetch")

BODY_SELECTORS: dict[str, str] = {"한국경제": ".article-body"}
MIN_BODY_CHARS = 80
MAX_FETCH_PER_FEED = 10
ARTICLE_TIMEOUT_S = 6.0
THROTTLE_S = 0.2
EMPTY_RATE_ALERT = 0.5


def fetch_body(client: httpx.Client, url: str, selector: str) -> str:
    """기사 페이지 fetch → selector 본문 추출. 실패/과소/예외 → "" (절대 raise 안 함)."""
    try:
        r = client.get(url, headers=DEFAULT_HEADERS,
                        follow_redirects=True, timeout=ARTICLE_TIMEOUT_S)
        if r.status_code != 200:
            return ""
        el = BeautifulSoup(r.text, "lxml").select_one(selector)
        if el is None:
            return ""
        text = " ".join(el.get_text(" ", strip=True).split())
        return text if len(text) >= MIN_BODY_CHARS else ""
    except Exception:
        return ""


def enrich_bodies(client, store, items):
    """화이트리스트+헤드라인+미저장 항목을 상한 내 fetch해 body 채움. 항목별 격리."""
    cand = [it for it in items if it.source in BODY_SELECTORS and not it.body]
    if not cand:
        return items
    new = set(store.filter_new_ids([it.id for it in cand]))
    targets = [it for it in cand if it.id in new][:MAX_FETCH_PER_FEED]
    empty = 0
    for it in targets:
        it.body = fetch_body(client, it.url, BODY_SELECTORS[it.source])
        if not it.body:
            empty += 1
            log.warning("body_fetch empty: %s %s", it.id, it.url)
        time.sleep(THROTTLE_S)
    if targets:
        rate = empty / len(targets)
        if rate >= EMPTY_RATE_ALERT:
            log.error("body_fetch: %d/%d empty (%.0f%%) — selector drift?",
                      empty, len(targets), rate * 100)
        else:
            log.info("body_fetch: %d/%d empty (%.0f%%)", empty, len(targets), rate * 100)
    return items
