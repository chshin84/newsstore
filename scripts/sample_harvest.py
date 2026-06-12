"""실제 수집 결과물 샘플 — 버킷별 확정소스에서 제목+시각+본문텍스트 출력.
Gemini가 실제로 받게 될 내용을 눈으로 확인한다.
"""
import time, re
from datetime import datetime, timezone
import requests, feedparser
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
T = 45

SOURCES = [
    ("한국 채권/외환", "인포맥스 S1N16", "https://news.einfomax.co.kr/rss/S1N16.xml"),
    ("한국 증시", "인포맥스 S1N2", "https://news.einfomax.co.kr/rss/S1N2.xml"),
    ("미국주식", "Benzinga news", "https://www.benzinga.com/news/feed"),
    ("크립토", "Benzinga crypto", "https://www.benzinga.com/markets/cryptocurrency/feed"),
    ("FX", "ForexLive", "https://www.forexlive.com/feed/news"),
    ("채권/금리", "ForexLive 중앙은행", "https://www.forexlive.com/feed/centralbank"),
    ("매크로(Reuters)", "GoogleNews", "https://news.google.com/rss/search?q=site:reuters.com+(inflation+OR+economy+OR+Fed)+when:12h&hl=en-US&gl=US&ceid=US:en"),
    ("매크로(AP)", "GoogleNews", "https://news.google.com/rss/search?q=site:apnews.com+(economy+OR+inflation+OR+Fed)+when:12h&hl=en-US&gl=US&ceid=US:en"),
]

def dt_of(e):
    t = e.get("published_parsed") or e.get("updated_parsed")
    return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc) if t else None

def body_text(e):
    raw = e["content"][0]["value"] if e.get("content") else e.get("summary", "")
    txt = BeautifulSoup(raw, "lxml").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", txt).strip()

for bucket, src, url in SOURCES:
    print("\n" + "=" * 72)
    print(f"  [{bucket}]  {src}")
    print("=" * 72)
    try:
        r = requests.get(url, headers=UA, timeout=T)
        fp = feedparser.parse(r.content)
        if not fp.entries:
            print(f"   (항목 없음, status={r.status_code})"); continue
        for e in fp.entries[:2]:
            d = dt_of(e); ds = d.strftime("%Y-%m-%d %H:%M UTC") if d else "시각없음"
            body = body_text(e)
            print(f"\n  · 제목: {e.get('title','')}")
            print(f"    시각: {ds}   본문길이: {len(body)}자")
            print(f"    본문: {body[:320]}{'...' if len(body) > 320 else ''}")
    except Exception as ex:
        print(f"   FAIL {type(ex).__name__}: {ex}")
    time.sleep(0.3)
