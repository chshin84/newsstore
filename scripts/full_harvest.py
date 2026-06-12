"""전체 피드 실시간 하베스트 — 한국 급락 원인 탐색용."""
import time, re
from datetime import datetime, timezone
import requests, feedparser
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
T = 45

FEEDS = [
    ("인포맥스:인기", "https://news.einfomax.co.kr/rss/clickTop.xml"),
    ("인포맥스:증권", "https://news.einfomax.co.kr/rss/S1N2.xml"),
    ("인포맥스:채권/외환", "https://news.einfomax.co.kr/rss/S1N16.xml"),
    ("인포맥스:국제", "https://news.einfomax.co.kr/rss/S1N23.xml"),
    ("인포맥스:정책", "https://news.einfomax.co.kr/rss/S1N15.xml"),
    ("인포맥스:전체", "https://news.einfomax.co.kr/rss/allArticle.xml"),
    ("ForexLive", "https://www.forexlive.com/feed/news"),
    ("ForexLive:중앙은행", "https://www.forexlive.com/feed/centralbank"),
    ("FXStreet", "https://www.fxstreet.com/rss/news"),
    ("Benzinga:news", "https://www.benzinga.com/news/feed"),
    ("Benzinga:markets", "https://www.benzinga.com/markets/feed"),
    ("GNews:코스피", "https://news.google.com/rss/search?q=%EC%BD%94%EC%8A%A4%ED%94%BC+OR+KOSPI+when:1d&hl=ko&gl=KR&ceid=KR:ko"),
    ("GNews:매크로", "https://news.google.com/rss/search?q=site:reuters.com+(selloff+OR+plunge+OR+Korea+OR+Asia+OR+Fed)+when:12h&hl=en-US&gl=US&ceid=US:en"),
]

CRASH = re.compile(r"급락|폭락|급등|하락|약세|매도|패닉|plunge|crash|tumbl|sell.?off|rout|slump|sink|코스피|kospi|원화|환율", re.I)

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

now = datetime.now(timezone.utc)
print(f"\n현재 UTC {now:%H:%M} / KST {now.hour+9 if now.hour<15 else now.hour-15:02d}:{now.minute:02d}  (총 {len(items)}건 수집)\n")

withdt = [x for x in items if x[0]]
withdt.sort(key=lambda x: x[0], reverse=True)

print("#" * 78)
print("#  급락/시장 관련 매칭 (최신순)")
print("#" * 78)
shown = 0
for d, src, title, bd in withdt:
    if CRASH.search(title + " " + bd):
        print(f"\n[{d:%m-%d %H:%M}UTC][{src}] {title[:64]}")
        print(f"   {bd[:180]}")
        shown += 1
        if shown >= 18: break

print("\n\n" + "#" * 78)
print("#  전체 최신 12건")
print("#" * 78)
for d, src, title, bd in withdt[:12]:
    print(f"[{d:%m-%d %H:%M}][{src}] {title[:66]}")
