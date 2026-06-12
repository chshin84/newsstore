"""FX / 채권 / 매크로 커버리지 실측 (스파이크).
각 후보 피드: 상태/항목/깊이/간격/본문 + 최신 헤드라인 4개를 출력해
실제 커버리지를 눈으로 확인한다.
"""
import time
from datetime import datetime, timezone
import requests, feedparser, statistics
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
T = 45

BUCKETS = {
    "FX (글로벌/북미)": [
        ("ForexLive", "https://www.forexlive.com/feed/news"),
        ("FXStreet", "https://www.fxstreet.com/rss/news"),
        ("Investing FX", "https://www.investing.com/rss/news_1.rss"),
        ("DailyFX", "https://www.dailyfx.com/feeds/market-news"),
        ("GoogleNews FX", "https://news.google.com/rss/search?q=forex+OR+%22US+dollar%22+when:6h&hl=en-US&gl=US&ceid=US:en"),
    ],
    "채권/금리 (미국)": [
        ("Fed 공식", "https://www.federalreserve.gov/feeds/press_all.xml"),
        ("Investing bonds", "https://www.investing.com/rss/bonds.rss"),
        ("CNBC bonds", "https://www.cnbc.com/id/10000664/device/rss/rss.html"),
        ("GoogleNews bonds", "https://news.google.com/rss/search?q=%22treasury+yields%22+OR+%22bond+market%22+when:12h&hl=en-US&gl=US&ceid=US:en"),
    ],
    "매크로/경제": [
        ("BLS(고용/물가)", "https://www.bls.gov/feed/bls_latest.rss"),
        ("Investing 경제", "https://www.investing.com/rss/news_25.rss"),
        ("CNBC 경제", "https://www.cnbc.com/id/20910232/device/rss/rss.html"),
        ("GoogleNews 매크로", "https://news.google.com/rss/search?q=FOMC+OR+CPI+OR+%22Federal+Reserve%22+OR+%22jobs+report%22+when:12h&hl=en-US&gl=US&ceid=US:en"),
        ("ECB(유럽)", "https://www.ecb.europa.eu/rss/press.html"),
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
                print(f"\n  ▸ {name}: [status={r.status_code}] 항목0 — ✗ 사용불가")
                continue
            dts = sorted([d for d in (dt_of(e) for e in fp.entries) if d], reverse=True)
            if len(dts) >= 2:
                span = (dts[0]-dts[-1]).total_seconds()/60
                gap = statistics.median([(dts[i]-dts[i+1]).total_seconds()/60 for i in range(len(dts)-1)])
                depth = f"{span/60:.0f}h" if span >= 120 else f"{span:.0f}m"
                newest = dts[0].strftime("%m-%d %H:%M")
            else:
                depth, gap, newest = "?", 0, "?"
            e0 = fp.entries[0]
            body = e0["content"][0]["value"] if e0.get("content") else e0.get("summary", "")
            blen = len(BeautifulSoup(body, "lxml").get_text()) if body else 0
            ftxt = "전문" if blen > 600 else f"요약{blen}자"
            print(f"\n  ▸ {name}: 항목{n} 깊이{depth} 간격{gap:.0f}m 최신{newest}(UTC) 본문={ftxt}")
            for e in fp.entries[:4]:
                d = dt_of(e)
                ds = d.strftime("%m-%d %H:%M") if d else "  ?  "
                print(f"      · [{ds}] {e.get('title','')[:62]}")
        except Exception as ex:
            print(f"\n  ▸ {name}: ✗ FAIL {type(ex).__name__}: {str(ex)[:50]}")
        time.sleep(0.3)
