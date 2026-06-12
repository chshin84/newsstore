"""진짜 Bloomberg RSS 엔드포인트 직접 검증 (atlasflux가 노출시킨 URL들)."""
import time, re
from datetime import datetime, timezone
import requests, feedparser
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
T = 40

FEEDS = [
    ("BBG markets", "https://feeds.bloomberg.com/markets/news.rss"),
    ("BBG technology", "https://feeds.bloomberg.com/technology/news.rss"),
    ("BBG economics", "https://feeds.bloomberg.com/economics/news.rss"),
    ("BBG politics", "https://feeds.bloomberg.com/politics/news.rss"),
    ("BBG wealth", "https://feeds.bloomberg.com/wealth/news.rss"),
    ("BBG industries", "https://feeds.bloomberg.com/industries/news.rss"),
    ("BBG green", "https://feeds.bloomberg.com/green/news.rss"),
    ("author:Dinesh Nair", "https://www.bloomberg.com/authors/ARyyGQR8v_w/dinesh-nair.rss"),
    ("Flipboard BBG Korea", "https://flipboard.com/@bloomberg/korea-gaa61f1tz.rss"),
]
SCOOP = re.compile(r"hynix|samsung|hedge fund|leverage|chipmaker|korea|prime broker", re.I)

def dt_of(e):
    t = e.get("published_parsed") or e.get("updated_parsed")
    return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc) if t else None

def body(e):
    raw = e["content"][0]["value"] if e.get("content") else e.get("summary", "")
    return re.sub(r"\s+", " ", BeautifulSoup(raw, "lxml").get_text(" ", strip=True))

print(f"{'피드':<22}{'상태':>5}{'항목':>5}{'최신':>12}{'본문':>8}  스쿱")
print("-" * 70)
allhits = []
for name, url in FEEDS:
    try:
        r = requests.get(url, headers=UA, timeout=T)
        fp = feedparser.parse(r.content)
        n = len(fp.entries)
        dts = sorted([d for d in (dt_of(e) for e in fp.entries) if d], reverse=True)
        newest = dts[0].strftime("%m-%d %H:%M") if dts else "?"
        blen = len(body(fp.entries[0])) if n else 0
        sc = [e for e in fp.entries if SCOOP.search(e.get("title","") + body(e))]
        for e in sc:
            allhits.append((name, e.get("title",""), body(e)))
        print(f"{name:<22}{r.status_code:>5}{n:>5}{newest:>12}{blen:>6}자  {('🔴'+str(len(sc))) if sc else '-'}")
    except Exception as ex:
        print(f"{name:<22}  FAIL {type(ex).__name__}")
    time.sleep(0.25)

print("\n" + "=" * 70)
print("스쿱(하닉/삼성/한국/헤지펀드) 매칭 상세")
print("=" * 70)
if not allhits:
    print("  매칭 없음")
for name, title, bd in allhits[:8]:
    print(f"\n[{name}] {title[:66]}")
    print(f"   {bd[:240]}")
