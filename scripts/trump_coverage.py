"""트럼프 소셜/발언이 기존 피드에서 커버되나 + 직접 소스 존재 여부 (스파이크)."""
import time, re
from datetime import datetime, timezone
import requests, feedparser
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
T = 45
PAT = re.compile(r"trump|트럼프|truth social", re.I)

FEEDS = [
    ("ForexLive", "https://www.forexlive.com/feed/news"),
    ("ForexLive 중앙은행", "https://www.forexlive.com/feed/centralbank"),
    ("Benzinga news", "https://www.benzinga.com/news/feed"),
    ("FXStreet", "https://www.fxstreet.com/rss/news"),
    ("인포맥스 국제 S1N23", "https://news.einfomax.co.kr/rss/S1N23.xml"),
    ("인포맥스 채권/외환", "https://news.einfomax.co.kr/rss/S1N16.xml"),
    ("GNews: Trump markets", "https://news.google.com/rss/search?q=Trump+(tariff+OR+Fed+OR+markets)+when:8h&hl=en-US&gl=US&ceid=US:en"),
    ("GNews: Truth Social", "https://news.google.com/rss/search?q=%22Truth+Social%22+when:24h&hl=en-US&gl=US&ceid=US:en"),
]

def dt_of(e):
    t = e.get("published_parsed") or e.get("updated_parsed")
    return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc) if t else None

def text(e):
    raw = e["content"][0]["value"] if e.get("content") else e.get("summary", "")
    return e.get("title", "") + " " + BeautifulSoup(raw, "lxml").get_text(" ", strip=True)

print("== (1) 기존 피드 내 트럼프 언급 스캔 ==")
for name, url in FEEDS:
    try:
        fp = feedparser.parse(requests.get(url, headers=UA, timeout=T).content)
        hits = [e for e in fp.entries if PAT.search(text(e))]
        print(f"\n  ▸ {name}: 전체{len(fp.entries)}건 중 트럼프언급 {len(hits)}건")
        for e in hits[:3]:
            d = dt_of(e); ds = d.strftime("%m-%d %H:%M") if d else "?"
            body = BeautifulSoup(e["content"][0]["value"] if e.get("content") else e.get("summary",""), "lxml").get_text(" ", strip=True)
            print(f"      · [{ds}] {e.get('title','')[:58]}")
            snip = re.sub(r'\s+', ' ', body)[:160]
            if snip: print(f"            {snip}")
    except Exception as ex:
        print(f"\n  ▸ {name}: FAIL {type(ex).__name__}")
    time.sleep(0.3)

print("\n\n== (2) Truth Social 직접 소스 후보 ==")
DIRECT = [
    "https://trumpstruth.org/feed",
    "https://trumpstruth.org/",
    "https://truthsocial.com/@realDonaldTrump",
]
for u in DIRECT:
    try:
        r = requests.get(u, headers=UA, timeout=T)
        fp = feedparser.parse(r.content)
        print(f"  {u}\n     status={r.status_code} len={len(r.text)} RSS항목={len(fp.entries)}")
        if fp.entries:
            print(f"     최신: {fp.entries[0].get('title','')[:70]}")
    except Exception as ex:
        print(f"  {u}\n     FAIL {type(ex).__name__}: {str(ex)[:40]}")
    time.sleep(0.3)
