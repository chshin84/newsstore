from __future__ import annotations
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
from .feeds import make_id
from ..contracts.models import RawItem

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
