"""Benzinga 피드 정체 규명 (스파이크).
benzinga.com/feed의 실제 항목 시각/제목을 까보고, 대체 피드 URL을 시험한다.
"""
import time
import requests
import feedparser

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
T = 60

print("=" * 64)
print("1) benzinga.com/feed 실제 항목 덤프")
print("=" * 64)
r = requests.get("https://www.benzinga.com/feed", headers=UA, timeout=T)
fp = feedparser.parse(r.content)
for e in fp.entries:
    print(f"  {e.get('published','?'):<34} {e.get('title','')[:50]}")

print("\n" + "=" * 64)
print("2) 대체 Benzinga 피드 URL 시험")
print("=" * 64)
CANDS = [
    "https://www.benzinga.com/feed/markets",
    "https://www.benzinga.com/markets/feed",
    "https://www.benzinga.com/news/feed",
    "https://www.benzinga.com/feed/news",
    "https://www.benzinga.com/category/news/feed",
    "https://feeds.benzinga.com/benzinga",
    "https://www.benzinga.com/partner/rss",
]
for u in CANDS:
    try:
        r = requests.get(u, headers=UA, timeout=T)
        fp = feedparser.parse(r.content)
        n = len(fp.entries)
        if n:
            first = fp.entries[0]
            print(f"  [OK {r.status_code}] n={n:>3} 최신={first.get('published','?')[:31]}  {first.get('title','')[:34]}")
        else:
            print(f"  [WARN {r.status_code}] n=0  {u}")
    except Exception as ex:
        print(f"  [FAIL] {type(ex).__name__}  {u}")
    time.sleep(0.3)

print("\n" + "=" * 64)
print("3) 대안: 미국주식 속보용 다른 소스 후보")
print("=" * 64)
ALT = {
    "CNBC 마켓": "https://www.cnbc.com/id/20910258/device/rss/rss.html",
    "Investing 주식뉴스": "https://www.investing.com/rss/news_25.rss",
    "GoogleNews US stocks": "https://news.google.com/rss/search?q=US+stocks+when:2h&hl=en-US&gl=US&ceid=US:en",
    "Seeking Alpha": "https://seekingalpha.com/market_currents.xml",
}
for name, u in ALT.items():
    try:
        r = requests.get(u, headers=UA, timeout=T)
        fp = feedparser.parse(r.content)
        n = len(fp.entries)
        print(f"  {name:<22} [status={r.status_code}] n={n:>3}" +
              (f"  최신={fp.entries[0].get('published','?')[:31]}" if n else ""))
    except Exception as ex:
        print(f"  {name:<22} FAIL {type(ex).__name__}")
    time.sleep(0.3)
