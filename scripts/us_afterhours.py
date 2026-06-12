"""미국 애프터장/선물 + 글로벌 리스크오프 실시간 확인."""
import time, re
from datetime import datetime, timezone, timedelta
import requests, feedparser
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
T = 45

FEEDS = [
    ("ForexLive", "https://www.forexlive.com/feed/news"),
    ("FXStreet", "https://www.fxstreet.com/rss/news"),
    ("Benzinga:mkt", "https://www.benzinga.com/markets/feed"),
    ("Benzinga:news", "https://www.benzinga.com/news/feed"),
    ("GNews:선물", "https://news.google.com/rss/search?q=(%22stock+futures%22+OR+%22S%26P+500%22+OR+Nasdaq+OR+Dow)+(fall+OR+drop+OR+slump+OR+plunge+OR+lower+OR+sink)+when:3h&hl=en-US&gl=US&ceid=US:en"),
    ("GNews:riskoff", "https://news.google.com/rss/search?q=(selloff+OR+%22risk-off%22+OR+rout+OR+tumble+OR+VIX)+when:3h&hl=en-US&gl=US&ceid=US:en"),
    ("GNews:Asia", "https://news.google.com/rss/search?q=(Asia+stocks+OR+Nikkei+OR+Hang+Seng+OR+Kospi)+(fall+OR+drop+OR+slump+OR+plunge)+when:3h&hl=en-US&gl=US&ceid=US:en"),
]
RISK = re.compile(r"futures|s&p|nasdaq|dow|nikkei|hang seng|kospi|slump|plunge|tumbl|sink|sell.?off|rout|risk.?off|vix|lower|fall|drop|선물|급락|하락|safe.?haven|gold|yield", re.I)

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
print(f"현재 {now:%H:%M}UTC = {(now+timedelta(hours=9)):%H:%M}KST = ET {(now-timedelta(hours=4)):%H:%M} / {len(items)}건\n")

print("=" * 80)
print("최신 20건 (UTC)  🔴=리스크/선물 키워드")
print("=" * 80)
for d, src, title, bd in items[:20]:
    mark = "🔴" if RISK.search(title + bd) else "  "
    print(f"{mark}[{d:%H:%M}][{src:>12}] {title[:54]}")

print("\n" + "=" * 80)
print("선물/리스크 상세 (최신 7건)")
print("=" * 80)
n = 0
for d, src, title, bd in items:
    if RISK.search(title + bd):
        print(f"\n[{d:%H:%M}][{src}] {title[:62]}")
        print(f"   {bd[:230]}")
        n += 1
        if n >= 7: break
