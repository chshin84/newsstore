"""Benzinga 카테고리별 피드 전수 탐색 (스파이크).
/{category}/feed 패턴으로 토픽별 피드 존재/볼륨/깊이를 훑는다.
"""
import time
from datetime import datetime, timezone
import requests, feedparser, statistics

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
T = 45

CATS = [
    "markets", "news", "general", "trading-ideas",
    "earnings", "analyst-ratings", "ratings", "price-target",
    "options", "etfs", "etf", "dividends", "ipos", "m-a",
    "cryptocurrency", "crypto", "markets/cryptocurrency",
    "commodities", "markets/commodities", "bonds", "fixed-income",
    "economics", "macro-economic-events", "government", "politics",
    "forex", "markets/forex", "tech", "sec", "movers",
    "pre-market-outlook", "after-hours", "large-cap", "mid-cap",
    "small-cap", "penny-stocks", "short-sellers", "fintech",
    "trading", "stock", "stocks",
]

def dt_of(e):
    t = e.get("published_parsed") or e.get("updated_parsed")
    return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc) if t else None

print(f"{'카테고리':<26}{'상태':>5}{'항목':>5}{'깊이':>9}{'간격중앙':>9}  샘플제목")
print("-" * 88)
found = []
for c in CATS:
    url = f"https://www.benzinga.com/{c}/feed"
    try:
        r = requests.get(url, headers=UA, timeout=T)
        fp = feedparser.parse(r.content)
        n = len(fp.entries)
        if r.status_code == 200 and n > 0:
            dts = sorted([d for d in (dt_of(e) for e in fp.entries) if d], reverse=True)
            if len(dts) >= 2:
                span = (dts[0]-dts[-1]).total_seconds()/60
                gaps = [(dts[i]-dts[i+1]).total_seconds()/60 for i in range(len(dts)-1)]
                med = statistics.median(gaps)
                s = f"{span/60:.1f}h" if span >= 120 else f"{span:.0f}m"
                title = fp.entries[0].get("title", "")[:30]
                print(f"{c:<26}{r.status_code:>5}{n:>5}{s:>9}{med:>7.0f}m  {title}")
                found.append(c)
            else:
                print(f"{c:<26}{r.status_code:>5}{n:>5}   타임스탬프부족")
        else:
            print(f"{c:<26}{r.status_code:>5}{n:>5}   -")
    except Exception as ex:
        print(f"{c:<26}  FAIL {type(ex).__name__}")
    time.sleep(0.25)

print("\n작동 카테고리 피드:", ", ".join(found))
