from __future__ import annotations
import logging
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import httpx
from bs4 import BeautifulSoup
from .collector import is_due          # 순수 스케줄 함수 재사용(collector 동작 불침범)
from .feeds import make_id
from ..contracts.models import RawItem

log = logging.getLogger(__name__)

# FMP 뉴스 publishedDate/date는 미 동부시간이다(2026-07-19 실측: 저장 UTC 대비 일관 +4h=EDT,
# 겹침 CNBC 20건 대조). ZoneInfo로 EST(-5)/EDT(-4) DST를 자동 처리 — 고정 오프셋은 DST 경계에서
# 어긋난다. slim 이미지엔 IANA tz DB가 없어 pyproject 의존성에 tzdata 필요(Task2 Step4b).
FMP_NEWS_TZ = ZoneInfo("America/New_York")


def _clean(html: str) -> str:
    text = BeautifulSoup(html or "", "lxml").get_text(" ", strip=True)
    return " ".join(text.split())


def _parse_dt(s: str) -> datetime | None:
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            naive = datetime.strptime(s, fmt)
        except ValueError:
            continue
        return naive.replace(tzinfo=FMP_NEWS_TZ).astimezone(timezone.utc)
    return None


def map_standard_row(row: dict, endpoint: str, fetched_at: datetime) -> RawItem | None:
    """`*-latest` 5종 공통 shape → RawItem. url/title 둘 다 없으면(중복 basis 없음) 드롭."""
    url = (row.get("url") or "").strip()
    title = (row.get("title") or "").strip()
    if not url and not title:
        return None
    return RawItem(
        id=make_id(url or title),
        feed_id=f"fmp:{endpoint}",
        source=(row.get("publisher") or row.get("site") or "FMP"),
        url=url, title=title, body=_clean(row.get("text") or ""),
        symbol=(row.get("symbol") or "").strip(),
        published_at=_parse_dt(row.get("publishedDate") or ""),
        fetched_at=fetched_at,
    )


def _first_ticker(tickers: str) -> str:
    t = (tickers or "").split(",")[0].strip()
    return t.split(":")[-1].strip() if ":" in t else t


def map_article_row(row: dict, fetched_at: datetime) -> RawItem | None:
    """fmp-articles 변형 shape(link/content/date/tickers) → RawItem."""
    url = (row.get("link") or "").strip()
    title = (row.get("title") or "").strip()
    if not url and not title:
        return None
    return RawItem(
        id=make_id(url or title),
        feed_id="fmp:fmp-articles",
        source=(row.get("site") or "Financial Modeling Prep"),
        url=url, title=title, body=_clean(row.get("content") or ""),
        symbol=_first_ticker(row.get("tickers") or ""),
        published_at=_parse_dt(row.get("date") or ""),
        fetched_at=fetched_at,
    )


# --- 고정 lookback 오케스트레이션(페이지네이션·429·건강·격리) ---

PAGE_LIMIT = 250                          # SSOT — 요청 limit이자 '마지막 페이지' 판정 기준. 엔트리포인트가 import.
_DEFAULT_CAP = 100                        # date-bounded 엔드포인트 최대 페이지(FMP page≤100)
PAGE_CAP = {"fmp-articles": 2}            # from/to 미지원 → 최신 소수 페이지만. 캡 도달은 정상(오탐 아님).
DEFAULT_LOOKBACK_DAYS = 3
_GET_ALL_UNBOUNDED = {"fmp-articles"}     # date-bound 없어 절단을 건강 이상으로 기록하지 않는 엔드포인트


def _map_row(endpoint: str, row: dict, fetched_at: datetime) -> RawItem | None:
    if endpoint == "fmp-articles":
        return map_article_row(row, fetched_at)
    return map_standard_row(row, endpoint, fetched_at)


def _get_page(fetch, frm, to, page, *, retries=2, backoff=2.0):
    for attempt in range(retries + 1):
        try:
            return fetch(frm, to, page) or []
        except httpx.HTTPStatusError as e:
            if e.response is not None and e.response.status_code == 429 and attempt < retries:
                time.sleep(backoff * (attempt + 1))
                continue
            raise


def _fetch_all_pages(fetch, frm, to, *, max_pages, delay_s=0.2, retries=2):
    """0..max_pages-1 페이지를 순회. 짧은 페이지(<PAGE_LIMIT)나 빈 페이지에서 정상 종료(truncated=False).
    max_pages를 모두 가득 채우면 truncated=True(더 남았을 개연)."""
    rows: list[dict] = []
    for page in range(max_pages):
        batch = _get_page(fetch, frm, to, page, retries=retries)
        if not batch:
            return rows, False
        rows.extend(batch)
        if len(batch) < PAGE_LIMIT:
            return rows, False
        if delay_s and page < max_pages - 1:
            time.sleep(delay_s)
    return rows, True


def _mark_ok(store, feed_id, *, now):
    store.set_feed_state(feed_id, last_fetched=now, last_success=now,
                         consecutive_failures=0, last_error=None, last_error_at=None)


def _mark_fail(store, feed_id, *, now, error):
    try:
        cf = (store.get_feed_state(feed_id).get("consecutive_failures") or 0) + 1
        store.set_feed_state(feed_id, consecutive_failures=cf,
                             last_error=str(error)[:300], last_error_at=now)
    except Exception:
        log.debug("fmp_news %s: health record failed (ignored)", feed_id)


def run_fmp_news_pass(store, fetchers: dict, endpoints: list[str], *, now: datetime,
                      lookback_days: int = DEFAULT_LOOKBACK_DAYS, poll_minutes: int = 1440,
                      delay_s: float = 0.2) -> dict[str, int]:
    """엔드포인트별 고정 lookback 재스캔 → RawItem → 청크 배치 upsert. 커서 없음(멱등 URL 중복제거).
    fmp:{endpoint} feed_state에 is_due·건강 기록. 한 엔드포인트 실패는 격리."""
    summary: dict[str, int] = {}
    frm = (now - timedelta(days=lookback_days)).date().isoformat()
    to = now.date().isoformat()
    for ep in endpoints:
        feed_id = f"fmp:{ep}"
        try:
            state = store.get_feed_state(feed_id)
            if not is_due(state, poll_minutes, now):
                continue
            rows, truncated = _fetch_all_pages(
                fetchers[ep], frm, to, max_pages=PAGE_CAP.get(ep, _DEFAULT_CAP), delay_s=delay_s)
            items = [m for r in rows if (m := _map_row(ep, r, now)) is not None]
            new = store.upsert_items_batched(items)
            _mark_ok(store, feed_id, now=now)
            if truncated and ep not in _GET_ALL_UNBOUNDED:      # date-bounded 창이 넘침 → 이상 신호
                log.warning("fmp_news %s: page cap 도달(절단 개연)", feed_id)
                store.set_feed_state(feed_id, last_error="truncated at page cap", last_error_at=now)
            summary[feed_id] = new
        except Exception as e:
            log.exception("fmp_news %s: pass error (isolated)", feed_id)
            _mark_fail(store, feed_id, now=now, error=e)
            summary[feed_id] = -1
    return summary
