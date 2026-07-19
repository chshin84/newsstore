from __future__ import annotations
import logging
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
import yaml
from bs4 import BeautifulSoup
from .collector import is_due          # 순수 스케줄 함수 재사용(collector 동작 불침범)
from .feeds import make_id
from .fmp_news import _mark_ok, _mark_fail   # 건강기록 재사용(SSOT — 드리프트 방지)
from ..contracts.models import RawItem

log = logging.getLogger(__name__)

DEFAULT_POLL_MINUTES = 30
DEFAULT_DISPLAY = 100


def _clean(html: str) -> str:
    """네이버 title/description의 <b> 하이라이트·HTML 엔티티 제거. FMP _clean과 달리 태그
    경계에 공백을 넣지 않는다(separator="") — 한국어는 키워드가 조사와 붙어 있어(예:
    '<b>증시</b>의') 공백을 넣으면 '증시 의'로 어절이 쪼개진다. 태그로 유실된 공백은
    원문 공백이 보존하므로 최종 collapse만 하면 된다."""
    text = BeautifulSoup(html or "", "lxml").get_text("")
    return " ".join(text.split())


def _parse_pubdate(s: str) -> datetime | None:
    """네이버 pubDate는 RFC822(예: 'Sun, 19 Jul 2026 18:50:00 +0900'). tz-aware로 파싱해 UTC 변환.
    오프셋이 없거나 파싱 실패면 None(FMP _parse_dt와 동형 — bad는 조용히 None)."""
    s = (s or "").strip()
    if not s:
        return None
    try:
        dt = parsedate_to_datetime(s)
    except (TypeError, ValueError):
        return None
    if dt is None or dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc)


def load_naver_config(path) -> dict:
    """활성 키워드 config(SSOT) 로더. 빈 queries는 fail-loud(ValueError)."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    queries = data.get("queries") or []
    if not queries:
        raise ValueError("naver_news config: queries 비어있음(fail-loud)")
    return {"queries": list(queries),
            "poll_minutes": int(data.get("poll_minutes", DEFAULT_POLL_MINUTES)),
            "display": int(data.get("display", DEFAULT_DISPLAY))}


def map_row(row: dict, query: str, asset_hint: str, fetched_at: datetime) -> RawItem | None:
    """네이버 검색 뉴스 item shape → RawItem. url(originallink 우선, 없으면 link)·title 둘 다
    없으면(중복 basis 없음) 드롭. title/description의 <b> 태그·HTML 엔티티는 _clean으로 제거."""
    url = (row.get("originallink") or row.get("link") or "").strip()
    title = _clean(row.get("title") or "")
    if not url and not title:
        return None
    return RawItem(
        id=make_id(url or title),
        feed_id=f"naver:{query}",
        source="네이버",
        asset_hint=asset_hint,
        language="ko",
        url=url,
        title=title,
        body=_clean(row.get("description") or ""),
        symbol="",
        published_at=_parse_pubdate(row.get("pubDate") or ""),
        fetched_at=fetched_at,
    )


def run_naver_pass(store, fetch, queries: list[dict], *, now: datetime,
                   poll_minutes: int = DEFAULT_POLL_MINUTES,
                   delay_s: float = 0.2) -> dict[str, int]:
    """키워드별 검색 뉴스 수집 → RawItem → 청크 배치 upsert. 커서 없음(멱등 URL 중복제거는
    store.upsert_items_batched의 존재검사에 위임). naver:{query} feed_state에 is_due·건강 기록.
    한 쿼리 실패는 격리(다음 쿼리로 진행)."""
    summary: dict[str, int] = {}
    for q in queries:
        query = (q.get("q") or "").strip()
        asset_hint = (q.get("asset_hint") or "").strip()
        if not query:                    # 잘못된 config 항목은 조용히 넘기지 않고 표면화
            log.warning("naver_news: 빈 q 항목 스킵 %r", q)
            continue
        feed_id = f"naver:{query}"
        try:
            state = store.get_feed_state(feed_id)
            if not is_due(state, poll_minutes, now):
                continue
            rows = fetch(query) or []
            items = [m for r in rows if (m := map_row(r, query, asset_hint, now)) is not None]
            new = store.upsert_items_batched(items)
            _mark_ok(store, feed_id, now=now)
            summary[feed_id] = new
            if delay_s:
                time.sleep(delay_s)
        except Exception as e:
            log.exception("naver_news %s: pass error (isolated)", feed_id)
            _mark_fail(store, feed_id, now=now, error=e)
            summary[feed_id] = -1
    return summary
