"""마이크론(MU) 애프터장 집중 확인."""
import time, re
from datetime import datetime, timezone, timedelta
import requests, feedparser
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
T = 45

FEEDS = [
    ("BZ:news", "https://www.benzinga.com/news/feed"),
    ("BZ:markets", "https://www.benzinga.com/markets/feed"),
    ("BZ:movers", "https://www.benzinga.com/movers/feed"),
    ("BZ:earnings", "https://www.benzinga.com/news/earnings/feed"),
    ("BZ:tech", "https://www.benzinga.com/tech/feed"),
    ("GNews:Micron", "https://news.google.com/rss/search?q=Micron+OR+MU+(earnings+OR+%22after+hours%22+OR+guidance+OR+stock)+when:6h&hl=en-US&gl=US&ceid=US:en"),
    ("GNews:반도체", "https://news.google.com/rss/search?q=(Micron+OR+%EB%A7%88%EC%9D%B4%ED%81%AC%EB%A1%A0+OR+%EB%B0%98%EB%8F%84%EC%B2%B4)+when:6h&hl=ko&gl=KR&ceid=KR:ko"),
    ("인포맥스:해외주식", "https://news.einfomax.co.kr/rss/S1N21.xml"),
]
MU = re.compile(r"micron|마이크론|\bMU\b|반도체|memory|DRAM|HBM|chip", re.I)

def dt_of(e):
    t = e.get("published_parsed") or e.get("updated_parsed")
    return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc) if t else None

def body(e):
    raw = e["content"][0]["value"] if e.get("content") else e.get("summary", "")
    return re.sub(r"\s+", " ", BeautifulSoup(raw, "lxml").get_text(" ", strip=True))

items = []
for name, url in FEEDS:
    try:
        fp = feedparser.parse(requests.get(url, headers=UA, timeout=T).content)
        for e in fp.entries:
            items.append((dt_of(e), name, e.get("title", ""), body(e)))
    except Exception as ex:
        print(f"  [{name}] FAIL {type(ex).__name__}")
    time.sleep(0.2)

hits = [x for x in items if MU.search(x[2] + " " + x[3]) and x[0]]
hits.sort(key=lambda x: x[0], reverse=True)
now = datetime.now(timezone.utc)
print(f"현재 {now:%H:%M}UTC = ET {(now-timedelta(hours=4)):%H:%M} / Micron·반도체 매칭 {len(hits)}건\n")
for d, src, title, bd in hits[:12]:
    print(f"[{d:%H:%M}][{src}] {title[:64]}")
    print(f"   {bd[:260]}\n")
