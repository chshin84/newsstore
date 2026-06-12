"""교정된 고볼륨 후보 피드들의 시간 깊이 재측정."""
import time
from datetime import datetime, timezone
import requests, feedparser

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
T = 60
FEEDS = {
    "Benzinga markets": "https://www.benzinga.com/markets/feed",
    "Benzinga news": "https://www.benzinga.com/news/feed",
    "CNBC markets": "https://www.cnbc.com/id/20910258/device/rss/rss.html",
    "GoogleNews US 2h": "https://news.google.com/rss/search?q=US+stocks+when:2h&hl=en-US&gl=US&ceid=US:en",
    "Seeking Alpha": "https://seekingalpha.com/market_currents.xml",
    "인포맥스 전체": "https://news.einfomax.co.kr/rss/allArticle.xml",
}

def dt_of(e):
    t = e.get("published_parsed") or e.get("updated_parsed")
    return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc) if t else None

print(f"{'소스':<20}{'항목':>5}{'시간깊이':>12}{'시간당':>9}{'권장폴링':>10}")
print("-" * 60)
for name, url in FEEDS.items():
    try:
        r = requests.get(url, headers=UA, timeout=T)
        fp = feedparser.parse(r.content)
        dts = sorted([d for d in (dt_of(e) for e in fp.entries) if d])
        n = len(fp.entries)
        if len(dts) < 2:
            print(f"{name:<20}{n:>5}   타임스탬프부족"); continue
        span = (dts[-1]-dts[0]).total_seconds()/60
        rate = n/(span/60) if span>0 else 9999
        safe = min(span/2, 60)
        s = f"{span/60:.1f}시간" if span>=120 else f"{span:.0f}분"
        print(f"{name:<20}{n:>5}{s:>12}{rate:>7.1f}/h{safe:>8.0f}분")
    except Exception as ex:
        print(f"{name:<20}  FAIL {type(ex).__name__}")
    time.sleep(0.3)
