"""Benzinga 실제 볼륨 규명 (스파이크).
- 현재 시각/미국장 상태
- 각 피드의 항목 상한 + 발행 간격(cadence) + 시간깊이
- 추가 카테고리 피드 탐색
"""
import time
from datetime import datetime, timezone, timedelta
import requests, feedparser, statistics

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
T = 60

now = datetime.now(timezone.utc)
et = now - timedelta(hours=4)  # 대략 ET (EDT)
print(f"현재 UTC: {now:%Y-%m-%d %H:%M}  /  대략 ET: {et:%H:%M}")
print("미국 정규장: 09:30~16:00 ET. (장중이면 볼륨↑, 새벽이면 볼륨↓)")

FEEDS = {
    "markets": "https://www.benzinga.com/markets/feed",
    "news": "https://www.benzinga.com/news/feed",
    "analyst-ratings": "https://www.benzinga.com/analyst-ratings/feed",
    "trading-ideas": "https://www.benzinga.com/trading-ideas/feed",
    "general": "https://www.benzinga.com/general/feed",
    "money": "https://www.benzinga.com/money/feed",
    "pressreleases": "https://www.benzinga.com/pressreleases/feed",
}

def dt_of(e):
    t = e.get("published_parsed") or e.get("updated_parsed")
    return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc) if t else None

print(f"\n{'카테고리':<18}{'상태':>6}{'항목':>5}{'시간깊이':>11}{'발행간격(중앙값)':>16}")
print("-" * 62)
for name, url in FEEDS.items():
    try:
        r = requests.get(url, headers=UA, timeout=T)
        fp = feedparser.parse(r.content)
        n = len(fp.entries)
        if n == 0:
            print(f"{name:<18}{r.status_code:>6}{n:>5}   (피드아님/빈값)"); continue
        dts = sorted([d for d in (dt_of(e) for e in fp.entries) if d], reverse=True)
        if len(dts) < 2:
            print(f"{name:<18}{r.status_code:>6}{n:>5}   타임스탬프부족"); continue
        span = (dts[0]-dts[-1]).total_seconds()/60
        gaps = [(dts[i]-dts[i+1]).total_seconds()/60 for i in range(len(dts)-1)]
        med = statistics.median(gaps)
        s = f"{span/60:.1f}시간" if span>=120 else f"{span:.0f}분"
        print(f"{name:<18}{r.status_code:>6}{n:>5}{s:>11}{med:>13.1f}분")
    except Exception as ex:
        print(f"{name:<18}  FAIL {type(ex).__name__}")
    time.sleep(0.3)
