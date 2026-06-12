"""추가 커버리지 테스트: 경제지표 컨센서스 / Axios / 루머·스쿱."""
import time, re
from datetime import datetime, timezone
import requests, feedparser
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
T = 45

def dt_of(e):
    t = e.get("published_parsed") or e.get("updated_parsed")
    return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc) if t else None

def body(e):
    raw = e["content"][0]["value"] if e.get("content") else e.get("summary", "")
    return re.sub(r"\s+", " ", BeautifulSoup(raw, "lxml").get_text(" ", strip=True))

def scan(name, url, pat, show=4):
    try:
        fp = feedparser.parse(requests.get(url, headers=UA, timeout=T).content)
    except Exception as ex:
        print(f"  ▸ {name}: FAIL {type(ex).__name__}"); return
    hits = [e for e in fp.entries if pat.search(e.get("title","") + " " + body(e))]
    print(f"\n  ▸ {name}: 전체{len(fp.entries)} 중 매칭 {len(hits)}")
    for e in hits[:show]:
        d = dt_of(e); ds = d.strftime("%m-%d %H:%M") if d else "?"
        print(f"      · [{ds}] {e.get('title','')[:60]}")
        print(f"            {body(e)[:170]}")

print("=" * 72)
print("(1) 경제지표 컨센서스 vs 실제  [ForexLive/FXStreet 본문에 'expected/forecast/vs']")
print("=" * 72)
DATA = re.compile(r"expected|forecast|estimate|consensus|prior|f'cast|vs\.?\s|%\s*(?:vs|exp)", re.I)
scan("ForexLive", "https://www.forexlive.com/feed/news", DATA)
scan("FXStreet", "https://www.fxstreet.com/rss/news", DATA)

print("\n" + "=" * 72)
print("(2) Axios RSS")
print("=" * 72)
for u in ["https://api.axios.com/feed/", "https://www.axios.com/feeds/feed.rss",
          "https://api.axios.com/feed/business", "https://api.axios.com/feed/markets"]:
    try:
        r = requests.get(u, headers=UA, timeout=T)
        fp = feedparser.parse(r.content)
        print(f"\n  ▸ {u}  status={r.status_code} 항목={len(fp.entries)}")
        for e in fp.entries[:3]:
            d = dt_of(e); ds = d.strftime("%m-%d %H:%M") if d else "?"
            print(f"      · [{ds}] {e.get('title','')[:64]}")
    except Exception as ex:
        print(f"\n  ▸ {u}  FAIL {type(ex).__name__}")
    time.sleep(0.3)

print("\n" + "=" * 72)
print("(3) 루머/스쿱  [Benzinga rumors + GoogleNews 'reportedly/in talks/considering']")
print("=" * 72)
ANY = re.compile(r".")
scan("Benzinga rumors", "https://www.benzinga.com/news/rumors/feed", ANY)
scan("GNews 루머/스쿱",
     "https://news.google.com/rss/search?q=(reportedly+OR+%22in+talks%22+OR+%22considering%22+OR+%22sources+say%22)+(stock+OR+merger+OR+acquisition+OR+raise)+when:12h&hl=en-US&gl=US&ceid=US:en",
     ANY)
