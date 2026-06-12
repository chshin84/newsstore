"""실시간 급락 추적 — 최신 항목 집중 + 코스피 급락 전용 쿼리."""
import time, re
from datetime import datetime, timezone, timedelta
import requests, feedparser
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
T = 45

FEEDS = [
    ("증권", "https://news.einfomax.co.kr/rss/S1N2.xml"),
    ("채권/외환", "https://news.einfomax.co.kr/rss/S1N16.xml"),
    ("인기", "https://news.einfomax.co.kr/rss/clickTop.xml"),
    ("국제", "https://news.einfomax.co.kr/rss/S1N23.xml"),
    ("전체", "https://news.einfomax.co.kr/rss/allArticle.xml"),
    ("GNews:코스피급락", "https://news.google.com/rss/search?q=%EC%BD%94%EC%8A%A4%ED%94%BC+%EA%B8%89%EB%9D%BD+OR+%ED%95%98%EB%9D%BD+OR+%EB%A7%A4%EB%8F%84+when:3h&hl=ko&gl=KR&ceid=KR:ko"),
    ("GNews:KOSPI", "https://news.google.com/rss/search?q=KOSPI+OR+%22Korea+stocks%22+when:3h&hl=en-US&gl=US&ceid=US:en"),
]
HOT = re.compile(r"급락|폭락|하락|급등|반전|금리인상|매도|외국인|코스피|kospi|선물|증시|약세|패닉|매도세", re.I)

def dt_of(e):
    t = e.get("published_parsed") or e.get("updated_parsed")
    return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc) if t else None

def body(e):
    raw = e["content"][0]["value"] if e.get("content") else e.get("summary", "")
    return re.sub(r"\s+", " ", BeautifulSoup(raw, "lxml").get_text(" ", strip=True))

items = []
for name, url in FEEDS:
    try:
        fp = feedparser.parse(requests.get(url, headers=UA, timeout=T).content)
        for e in fp.entries:
            items.append((dt_of(e), name, e.get("title", ""), body(e)))
    except Exception as ex:
        print(f"  [{name}] FAIL {type(ex).__name__}")
    time.sleep(0.2)

items = [x for x in items if x[0]]
items.sort(key=lambda x: x[0], reverse=True)
now = datetime.now(timezone.utc)
print(f"현재 {now:%H:%M}UTC = {(now+timedelta(hours=9)):%H:%M} KST / 수집 {len(items)}건\n")

print("=" * 80)
print("최신 25건 (시각=피드 pubDate 그대로, 인포맥스는 KST 표기)")
print("=" * 80)
for d, src, title, bd in items[:25]:
    mark = "🔴" if HOT.search(title + bd) else "  "
    print(f"{mark}[{d:%H:%M}][{src:>10}] {title[:56]}")

print("\n" + "=" * 80)
print("급락/금리/증시 키워드 상세 (최신 8건)")
print("=" * 80)
n = 0
for d, src, title, bd in items:
    if HOT.search(title + bd):
        print(f"\n[{d:%H:%M}][{src}] {title[:60]}")
        print(f"   {bd[:240]}")
        n += 1
        if n >= 8: break
