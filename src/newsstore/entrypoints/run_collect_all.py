"""통합 수집 엔트리포인트 — RSS·네이버·FMP를 병렬 실행하고, 셋 다 끝난 뒤 임베딩 패스를
한 번만 호출한다(2026-07-23 수집 파이프라인 통합 설계).

이전에는 newsstore-collector(RSS, 5분)·newsstore-naver-news(15분)·newsstore-fmp-news(15분)
3개 Cloud Run Job이 서로 완전히 독립적으로 돌았다. 이 엔트리포인트가 그 셋을 대체한다.
"""
from __future__ import annotations
import argparse
import logging
import os
from datetime import datetime, timedelta, timezone

import httpx

from ..collect.feeds import load_feeds, distinct_sources, source_tiers
from ..collect.ssl_config import make_client
from ..collect.collector import collect_once
from ..collect.naver_news import load_naver_config, run_naver_pass
from ..collect.fmp_news import load_fmp_news_config, run_fmp_news_pass, PAGE_LIMIT
from ..store.factory import make_store
from ._health import job_health, classify_systemic_failure, JobDegraded, \
    FAIL_RATE_ALERT, MIN_ATTEMPTED_FOR_ALERT
from ._parallel import run_sources_parallel

log = logging.getLogger("newsstore.entrypoints.run_collect_all")

DEADLINE_SECONDS = 180.0   # 소스별 자체 예산(1단) — 설계 문서 "3분 강제종료" 참고
BACKSTOP_SECONDS = 200.0   # 오케스트레이터 result(timeout=) 백스톱(2단) — 1단보다 20초 여유

NAVER_NEWS_URL = "https://openapi.naver.com/v1/search/news.json"
FMP_BASE_NEWS = "https://financialmodelingprep.com/stable/news/"
FMP_BASE_ARTICLES = "https://financialmodelingprep.com/stable/fmp-articles"


def build_naver_fetch(client, display: int):
    """쿼리 → 검색 뉴스 GET. 인증은 client 헤더에만(params·URL·로그에 비밀 금지, SECRETS)."""
    def fetch(query):
        r = client.get(NAVER_NEWS_URL, params={"query": query, "display": display, "sort": "date"})
        r.raise_for_status()
        return (r.json() or {}).get("items") or []
    return fetch


def build_fmp_fetchers(client, endpoints: list[str]) -> dict:
    """엔드포인트별 GET 함수. -latest는 from/to 지원, fmp-articles는 page/limit만."""
    def make(ep):
        def fetch(frm, to, page):
            if ep == "fmp-articles":
                r = client.get(FMP_BASE_ARTICLES, params={"limit": PAGE_LIMIT, "page": page})
            else:
                r = client.get(f"{FMP_BASE_NEWS}{ep}",
                               params={"from": frm, "to": to, "limit": PAGE_LIMIT, "page": page})
            r.raise_for_status()
            return r.json() or []
        return fetch
    return {ep: make(ep) for ep in endpoints}


def _summary_verdict(name: str, summary: dict, store) -> tuple[str, bool]:
    """한 소스의 summary를 시스템 장애 여부로 판정. 반환: (detail 조각, degraded?).

    두 조건 중 하나면 시스템 장애: (1) 시도분 중 일정 비율 이상 실패(MIN_ATTEMPTED_FOR_ALERT
    이상인 소스용 — 피드·쿼리가 수십 개인 RSS·네이버), (2) 시도분이 있는데 전부 실패(개수
    무관 — FMP처럼 엔드포인트가 6개뿐이라 MIN_ATTEMPTED_FOR_ALERT를 절대 못 넘는 소스가
    전체 장애에도 항상 ok로 잡히는 사각지대를 막는다. FMP_API_KEY가 유효하지 않으면
    missing-key와 달리 fail-loud하지 않고 엔드포인트 전부가 -1로 조용히 죽는다)."""
    new_failed, chronic = classify_systemic_failure(summary, store)
    attempted = len(summary)
    healthy_attempted = attempted - len(chronic)
    if healthy_attempted == 0:
        return f"{name}=ok", False
    all_failed = len(new_failed) == healthy_attempted
    rate_alert = healthy_attempted >= MIN_ATTEMPTED_FOR_ALERT and \
        len(new_failed) / healthy_attempted >= FAIL_RATE_ALERT
    if all_failed or rate_alert:
        return f"{name}=fail({len(new_failed)}/{healthy_attempted})", True
    return f"{name}=ok", False


def _run_once(store, *, rss_task, naver_task, fmp_task, api_key, gemini_client_factory,
              embed_pass_fn) -> str:
    """세 소스를 병렬 실행하고 결과를 종합해 job_health를 기록한다. 시스템 장애나 임베딩
    실패가 있으면 JobDegraded를 raise한다(job_health 블록 안에서 raise돼야 last_status='fail'이
    정확히 기록된다 — 설계 문서 'job_health 정확한 실패 기록' 참고). 성공 시 detail 문자열을
    반환한다. embed_pass_fn은 (store, client) -> {"pending":.., "embedded":.., "permanent":.., "retryable":..}."""
    with job_health(store, "collect_all") as h:
        results = run_sources_parallel(
            {"rss": rss_task, "naver": naver_task, "fmp": fmp_task},
            timeout=BACKSTOP_SECONDS,
        )

        details = []
        degraded = False
        for name in ("rss", "naver", "fmp"):
            summary, error = results[name]
            if error:
                details.append(f"{name}={error}")
                degraded = True
            else:
                piece, is_degraded = _summary_verdict(name, summary, store)
                details.append(piece)
                degraded = degraded or is_degraded

        embed_failed = False
        try:
            if api_key:
                client = gemini_client_factory(api_key)
                es = embed_pass_fn(store, client)
                log.info("embed pass: pending=%d embedded=%d permanent=%d retryable=%d",
                         es["pending"], es["embedded"], es["permanent"], es["retryable"])
                details.append("embed=ok")
            elif store.get_pending_embed_items(limit=1):
                log.error("GEMINI_API_KEY missing but embed_pending items exist (embedding stalled)")
                details.append("embed=fail(no_key)")
                embed_failed = True
            else:
                details.append("embed=skip(no_key_no_pending)")
        except Exception:
            log.exception("embed pass failed")
            details.append("embed=fail")
            embed_failed = True

        detail = " ".join(details)
        h["detail"] = detail
        if degraded or embed_failed:
            raise JobDegraded(detail)
        return detail


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="newsstore 통합 수집(RSS+네이버+FMP+임베딩)")
    ap.add_argument("--feeds", default="config/feeds.yaml")
    ap.add_argument("--naver-config", default="config/naver_news.yaml")
    ap.add_argument("--fmp-config", default="config/fmp_news.yaml")
    args = ap.parse_args(argv)
    logging.basicConfig(level=os.environ.get("NEWSSTORE_LOG_LEVEL", "INFO"),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    # 시크릿은 클라이언트를 하나라도 만들기 전에 전부 먼저 읽는다(fail-loud) — 순서가
    # 반대면(클라이언트부터 만들고 나중에 시크릿을 읽으면) 뒤쪽 시크릿이 없을 때 앞서
    # 만든 클라이언트가 닫히지 않고 새고, job_health 블록에 들어가기도 전에 죽어서
    # 대시보드가 '실패'가 아니라 '미실행'으로만 잡는다(옛 run_naver_news.py도 이 순서였다).
    naver_client_id = os.environ["NAVER_CLIENT_ID"]          # fail-loud
    naver_client_secret = os.environ["NAVER_CLIENT_SECRET"]  # fail-loud
    fmp_api_key = os.environ["FMP_API_KEY"]                  # fail-loud
    api_key = os.environ.get("GEMINI_API_KEY")               # 임베딩은 선택 — 없으면 _run_once가 판단

    feeds = load_feeds(args.feeds)
    naver_cfg = load_naver_config(args.naver_config)
    fmp_cfg = load_fmp_news_config(args.fmp_config)
    delay_s = float(os.environ.get("NEWSSTORE_NEWS_DELAY_S", "0.2"))

    rss_client = make_client()
    naver_client = httpx.Client(timeout=30.0, headers={
        "X-Naver-Client-Id": naver_client_id, "X-Naver-Client-Secret": naver_client_secret})
    fmp_client = httpx.Client(timeout=30.0, headers={"apikey": fmp_api_key})

    now = datetime.now(timezone.utc)
    deadline = now + timedelta(seconds=DEADLINE_SECONDS)
    naver_fetch = build_naver_fetch(naver_client, naver_cfg["display"])
    fmp_fetchers = build_fmp_fetchers(fmp_client, fmp_cfg["endpoints"])

    try:
        with make_store() as store:
            # SSOT: 사이트 소스 목록·tier를 feeds.yaml에서 도출해 기록(하드코딩 X).
            store.set_meta("sources", {"sources": distinct_sources(feeds),
                                       "tiers": source_tiers(feeds)})

            def rss_task():
                return collect_once(rss_client, store, feeds, now=now, deadline=deadline)

            def naver_task():
                return run_naver_pass(store, naver_fetch, naver_cfg["queries"], now=now,
                                      deadline=deadline, delay_s=delay_s)

            def fmp_task():
                return run_fmp_news_pass(store, fmp_fetchers, fmp_cfg["endpoints"], now=now,
                                         lookback_days=fmp_cfg["lookback_days"],
                                         blackout_start_hour=fmp_cfg["blackout_start_hour"],
                                         blackout_end_hour=fmp_cfg["blackout_end_hour"],
                                         deadline=deadline, delay_s=delay_s)

            def gemini_client_factory(key):
                from ..embed.gemini import GeminiEmbedClient
                return GeminiEmbedClient(key)

            from ..embed.embed_pass import embed_pass

            detail = _run_once(store, rss_task=rss_task, naver_task=naver_task,
                               fmp_task=fmp_task, api_key=api_key,
                               gemini_client_factory=gemini_client_factory,
                               embed_pass_fn=embed_pass)
            log.info("collect_all done: %s", detail)
    except JobDegraded as e:
        log.error("collect_all FAILED (systemic): %s", e)
        return 1
    finally:
        rss_client.close()
        naver_client.close()
        fmp_client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
