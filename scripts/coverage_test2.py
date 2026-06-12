"""채권/매크로 보강 2라운드 — 타임스탬프 있는 전용 소스 사냥."""
import time
from datetime import datetime, timezone
import requests, feedparser, statistics
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
T = 45

BUCKETS = {
    "채권/금리 보강": [
        ("Investing GovBonds", "https://www.investing.com/rss/bonds_Government.rss"),
        ("FXStreet 중앙은행", "https://www.fxstreet.com/rss/news/central-banks"),
        ("ForexLive 중앙은행", "https://www.forexlive.com/feed/centralbank"),
        ("TradingEconomics", "https://tradingeconomics.com/rss/news.aspx"),
        ("GoogleNews UST6h", "https://news.google.com/rss/search?q=%22treasury+yields%22+OR+%22US+10-year%22+when:6h&hl=en-US&gl=US&ceid=US:en"),
        ("WSJ채권(GNews)", "https://news.google.com/rss/search?q=site:wsj.com+(bond+OR+yields)+when:1d&hl=en-US&gl=US&ceid=US:en"),
    ],
    "매크로 보강": [
        ("FXStreet 경제뉴스", "https://www.fxstreet.com/rss/news/economic-indicators"),
        ("TradingEconomics US", "https://tradingeconomics.com/united-states/rss"),
        ("ForexLive 헤드라인", "https://www.forexlive.com/feed/centralbanks"),
        ("Investing 경제지표", "https://www.investing.com/rss/economic_indicators.rss"),
        ("Reuters경제(GNews)", "https://news.google.com/rss/search?q=site:reuters.com+(inflation+OR+economy+OR+Fed)+when:12h&hl=en-US&gl=US&ceid=US:en"),
        ("AP경제(GNews)", "https://news.google.com/rss/search?q=site:apnews.com+(economy+OR+inflation+OR+Fed)+when:12h&hl=en-US&gl=US&ceid=US:en"),
    ],
}

def dt_of(e):
    t = e.get("published_parsed") or e.get("updated_parsed")
    return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc) if t else None

for bucket, feeds in BUCKETS.items():
    print("\n" + "#" * 70)
    print(f"#  {bucket}")
    print("#" * 70)
    for name, url in feeds:
        try:
            r = requests.get(url, headers=UA, timeout=T)
            fp = feedparser.parse(r.content)
            n = len(fp.entries)
            if r.status_code != 200 or n == 0:
                print(f"\n  ▸ {name}: [status={r.status_code}] 항목0 — ✗"); continue
            dts = sorted([d for d in (dt_of(e) for e in fp.entries) if d], reverse=True)
            ts = "있음" if len(dts) >= 2 else "✗없음"
            if len(dts) >= 2:
                span = (dts[0]-dts[-1]).total_seconds()/60
                gap = statistics.median([(dts[i]-dts[i+1]).total_seconds()/60 for i in range(len(dts)-1)])
                meta = f"깊이{span/60:.0f}h 간격{gap:.0f}m 최신{dts[0]:%m-%d %H:%M}"
            else:
                meta = ""
            print(f"\n  ▸ {name}: 항목{n} 타임스탬프{ts} {meta}")
            for e in fp.entries[:4]:
                d = dt_of(e); ds = d.strftime("%m-%d %H:%M") if d else "  ?  "
                print(f"      · [{ds}] {e.get('title','')[:60]}")
        except Exception as ex:
            print(f"\n  ▸ {name}: ✗ FAIL {type(ex).__name__}")
        time.sleep(0.3)
