from __future__ import annotations
import logging
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse
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


# originallink 도메인 → 실제 발행처(본 뉴스). 네이버는 검색 API라 발행처명을 직접 안 주므로
# 도메인에서 유도한다. 주요 매체는 한글명, 미등록은 도메인 그대로, 네이버 자체 호스팅/불명은 "네이버".
# (2026-07-19 실측 상위 도메인 기반. 새 도메인은 여기 추가.)
_PUBLISHERS = {
    "mk.co.kr": "매일경제", "hankyung.com": "한국경제", "wowtv.co.kr": "한국경제TV",
    "sedaily.com": "서울경제", "edaily.co.kr": "이데일리", "fnnews.com": "파이낸셜뉴스",
    "mt.co.kr": "머니투데이", "moneys.co.kr": "머니S", "etoday.co.kr": "이투데이",
    "asiae.co.kr": "아시아경제", "ajunews.com": "아주경제", "newspim.com": "뉴스핌",
    "g-enews.com": "글로벌이코노믹", "heraldcorp.com": "헤럴드경제", "thebell.co.kr": "더벨",
    "businesspost.co.kr": "비즈니스포스트", "yna.co.kr": "연합뉴스", "einfomax.co.kr": "연합인포맥스",
    "news1.kr": "뉴스1", "newsis.com": "뉴시스", "etnews.com": "전자신문", "dt.co.kr": "디지털타임스",
    "digitaltoday.co.kr": "디지털투데이", "zdnet.co.kr": "ZDNet Korea", "inews24.com": "아이뉴스24",
    "chosun.com": "조선일보", "biz.chosun.com": "조선비즈", "joongang.co.kr": "중앙일보",
    "donga.com": "동아일보", "hani.co.kr": "한겨레", "khan.co.kr": "경향신문",
    "seoul.co.kr": "서울신문", "kmib.co.kr": "국민일보", "hankookilbo.com": "한국일보",
    "tokenpost.kr": "토큰포스트", "coinreaders.com": "코인리더스", "pinpointnews.co.kr": "핀포인트뉴스",
    "topstarnews.net": "톱스타뉴스", "ytn.co.kr": "YTN",
}


def _publisher(url: str) -> str:
    """originallink 도메인에서 발행처 유도. 매핑 우선, 미등록은 도메인, 네이버 호스팅·불명은 '네이버'."""
    try:
        host = (urlparse(url or "").netloc or "").lower().split(":")[0]
    except Exception:
        return "네이버"
    if not host or "naver." in host:
        return "네이버"
    if host in _PUBLISHERS:                       # 서브도메인 완전일치 먼저(biz.chosun 등)
        return _PUBLISHERS[host]
    stripped = re.sub(r"^(www|m|news|n|view|biz|it)\.", "", host)
    return _PUBLISHERS.get(stripped, stripped or "네이버")


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
        source=_publisher(url),
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
