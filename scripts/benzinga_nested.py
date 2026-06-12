"""Benzinga 중첩 카테고리 피드 탐색 (스파이크).
/{섹션}/{하위}/feed 패턴. 사용자가 markets/bonds, news/large-cap 발견.
"""
import time
from datetime import datetime, timezone
import requests, feedparser, statistics

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
T = 40

PATHS = [
    # 사용자 발견 확인
    "news/large-cap", "markets/bonds",
    # markets/* 자산군
    "markets/cryptocurrency", "markets/commodities", "markets/forex",
    "markets/equities", "markets/currencies", "markets/emerging-markets",
    "markets/etfs", "markets/options", "markets/futures", "markets/penny-stocks",
    # news/* 하위
    "news/mid-cap", "news/small-cap", "news/m-a", "news/offerings",
    "news/earnings", "news/dividends", "news/buybacks", "news/guidance",
    "news/regulations", "news/government", "news/politics", "news/economics",
    "news/global", "news/eurozone", "news/emerging-markets", "news/hot",
    "news/movers", "news/pre-market", "news/after-hours", "news/options",
    "news/analyst-ratings", "news/price-target", "news/upgrades", "news/downgrades",
    "news/tech", "news/health-care", "news/financials", "news/energy",
    "news/commodities", "news/bonds", "news/treasuries", "news/federal-reserve",
    # trading-ideas 하위
    "trading-ideas/long-ideas", "trading-ideas/short-ideas", "trading-ideas/technicals",
]

def dt_of(e):
    t = e.get("published_parsed") or e.get("updated_parsed")
    return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc) if t else None

print(f"{'경로':<30}{'상태':>5}{'항목':>5}{'깊이':>9}{'간격':>7}  샘플")
print("-" * 92)
ok = []
for p in PATHS:
    url = f"https://www.benzinga.com/{p}/feed"
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
                s = f"{span/60:.0f}h" if span >= 120 else f"{span:.0f}m"
                print(f"{p:<30}{r.status_code:>5}{n:>5}{s:>9}{med:>5.0f}m  {fp.entries[0].get('title','')[:26]}")
                ok.append(p)
            else:
                print(f"{p:<30}{r.status_code:>5}{n:>5}  ts부족"); ok.append(p)
        else:
            print(f"{p:<30}{r.status_code:>5}{n:>5}")
    except Exception as ex:
        print(f"{p:<30}  FAIL {type(ex).__name__}")
    time.sleep(0.2)

print(f"\n작동 {len(ok)}개:", ", ".join(ok))
