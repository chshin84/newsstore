"""피드 '시간 깊이' 측정 (스파이크).

각 피드가 담은 가장 오래된~최신 항목의 시각차(span)를 잰다.
span = 이 피드가 '기억'하는 시간. 폴링 주기가 span보다 길면 그 사이
밀려난 기사는 영구 소실된다(RSS는 백필 불가). 따라서 안전 폴링주기 < span.
"""
import time
from datetime import datetime, timezone

import requests
import feedparser

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
T = 60

FEEDS = {
    "인포맥스 채권/외환": "https://news.einfomax.co.kr/rss/S1N16.xml",
    "인포맥스 전체": "https://news.einfomax.co.kr/rss/allArticle.xml",
    "Benzinga": "https://www.benzinga.com/feed",
    "CNBC top": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Cointelegraph": "https://cointelegraph.com/rss",
    "FXStreet": "https://www.fxstreet.com/rss/news",
    "ForexLive": "https://www.forexlive.com/feed/news",
    "Investing FX": "https://www.investing.com/rss/news_1.rss",
    "Investing bonds": "https://www.investing.com/rss/bonds.rss",
    "Fed 공식": "https://www.federalreserve.gov/feeds/press_all.xml",
    "GoogleNews reuters": "https://news.google.com/rss/search?q=reuters+markets&hl=en-US&gl=US&ceid=US:en",
}


def dt_of(entry):
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    if not t:
        return None
    return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc)


def measure(url):
    try:
        r = requests.get(url, headers=UA, timeout=T)
        fp = feedparser.parse(r.content)
    except Exception as e:
        return None, f"FAIL {type(e).__name__}"
    n = len(fp.entries)
    if n == 0:
        return None, f"항목0(status={r.status_code})"
    dts = sorted([d for d in (dt_of(e) for e in fp.entries) if d])
    if len(dts) < 2:
        return None, f"n={n} 타임스탬프부족"
    newest, oldest = dts[-1], dts[0]
    span_min = (newest - oldest).total_seconds() / 60
    rate = n / (span_min / 60) if span_min > 0 else 0  # 시간당 기사수
    return (n, span_min, rate, newest), None


print(f"{'소스':<20}{'항목':>5}{'시간깊이(span)':>16}{'시간당기사':>11}{'권장폴링':>10}")
print("-" * 72)
for name, url in FEEDS.items():
    res, err = measure(url)
    if err:
        print(f"{name:<20}  {err}")
        continue
    n, span_min, rate, newest = res
    # 안전 폴링주기 = span의 절반, 최대 60분으로 캡
    safe = min(span_min / 2, 60)
    if span_min >= 120:
        span_str = f"{span_min/60:.1f}시간"
    else:
        span_str = f"{span_min:.0f}분"
    print(f"{name:<20}{n:>5}{span_str:>16}{rate:>9.1f}/h{safe:>8.0f}분")
    time.sleep(0.3)
