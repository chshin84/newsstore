"""Benzinga 카테고리 자동 수확 (스파이크).
추측 대신 홈페이지/사이트맵에서 카테고리 경로를 긁어 /feed 전수 검증한다.
"""
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlparse
import requests, feedparser, statistics
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
T = 40
SECTIONS = {"news", "markets", "trading-ideas", "money", "general", "tech",
            "trading", "topics", "topic"}

def harvest(url):
    try:
        r = requests.get(url, headers=UA, timeout=T)
    except Exception as e:
        print(f"  harvest 실패 {url}: {e}"); return set()
    soup = BeautifulSoup(r.text, "lxml")
    paths = set()
    for a in soup.find_all("a", href=True):
        p = urlparse(a["href"]).path.strip("/")
        if not p:
            continue
        segs = p.split("/")
        # 1~2 세그먼트, 첫 세그먼트가 섹션, 숫자/긴기사슬러그 제외
        if 1 <= len(segs) <= 2 and segs[0] in SECTIONS:
            if any(c.isdigit() for c in segs[-1]):
                continue
            if len(segs[-1]) > 24:  # 기사 슬러그 컷
                continue
            paths.add(p)
    return paths

cands = set()
for u in ["https://www.benzinga.com/", "https://www.benzinga.com/markets",
          "https://www.benzinga.com/news", "https://www.benzinga.com/topics"]:
    cands |= harvest(u)
    time.sleep(0.3)
print(f"수확된 후보 경로 {len(cands)}개\n")

def dt_of(e):
    t = e.get("published_parsed") or e.get("updated_parsed")
    return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc) if t else None

print(f"{'경로':<34}{'항목':>5}{'깊이':>7}{'간격':>7}  샘플")
print("-" * 90)
working = []
for p in sorted(cands):
    url = f"https://www.benzinga.com/{p}/feed"
    try:
        r = requests.get(url, headers=UA, timeout=T)
        fp = feedparser.parse(r.content)
        n = len(fp.entries)
        if r.status_code == 200 and n > 0:
            dts = sorted([d for d in (dt_of(e) for e in fp.entries) if d], reverse=True)
            if len(dts) >= 2:
                span = (dts[0]-dts[-1]).total_seconds()/60
                med = statistics.median([(dts[i]-dts[i+1]).total_seconds()/60 for i in range(len(dts)-1)])
                s = f"{span/60:.0f}h" if span >= 120 else f"{span:.0f}m"
                print(f"{p:<34}{n:>5}{s:>7}{med:>5.0f}m  {fp.entries[0].get('title','')[:24]}")
            working.append(p)
    except Exception:
        pass
    time.sleep(0.2)

print(f"\n작동 피드 {len(working)}개:\n  " + "\n  ".join(working))
