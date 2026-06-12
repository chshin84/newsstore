"""한국 금융매체 RSS 확장 테스트 + 하닉/삼성 레버리지 스쿱 한국매체 relay 확인."""
import time, re
from datetime import datetime, timezone, timedelta
import requests, feedparser
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
T = 40

FEEDS = [
    ("연합뉴스:경제", "https://www.yna.co.kr/rss/economy.xml"),
    ("연합뉴스:시장", "https://www.yna.co.kr/rss/market.xml"),
    ("한경", "https://www.hankyung.com/feed/finance"),
    ("한경:경제", "https://www.hankyung.com/feed/economy"),
    ("매경:증권", "https://www.mk.co.kr/rss/50200011/"),
    ("매경:경제", "https://www.mk.co.kr/rss/30000001/"),
    ("이데일리:증권", "https://www.edaily.co.kr/rss/edaily_stock.xml"),
    ("머니투데이:증권", "https://rss.mt.co.kr/mt_news_stock.xml"),
    ("서울경제", "https://www.sedaily.com/RSSFeed.xml"),
    ("파이낸셜뉴스", "https://www.fnnews.com/rss/fn_realnews_economy.xml"),
    ("아시아경제", "https://www.asiae.co.kr/rss/stock.htm"),
    ("GNews:하이닉스", "https://news.google.com/rss/search?q=SK%ED%95%98%EC%9D%B4%EB%8B%89%EC%8A%A4+OR+%ED%95%98%EC%9D%B4%EB%8B%89%EC%8A%A4+when:6h&hl=ko&gl=KR&ceid=KR:ko"),
    ("GNews:삼성전자", "https://news.google.com/rss/search?q=%EC%82%BC%EC%84%B1%EC%A0%84%EC%9E%90+(%ED%97%A4%EC%A7%80%ED%8E%80%EB%93%9C+OR+%EB%A0%88%EB%B2%84%EB%A6%AC%EC%A7%80+OR+%EC%9D%80%ED%96%89)+when:6h&hl=ko&gl=KR&ceid=KR:ko"),
]
SCOOP = re.compile(r"헤지펀드|레버리지|베팅|스왑|프라임|씨티|골드만|차입|증거금|마진|블룸버그.*제한|제한.*베팅", re.I)

def dt_of(e):
    t = e.get("published_parsed") or e.get("updated_parsed")
    return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc) if t else None

def body(e):
    raw = e["content"][0]["value"] if e.get("content") else e.get("summary", "")
    return re.sub(r"\s+", " ", BeautifulSoup(raw, "lxml").get_text(" ", strip=True))

print(f"{'소스':<18}{'상태':>6}{'항목':>5}{'최신':>12}  스쿱매칭")
print("-" * 70)
scoop_hits = []
for name, url in FEEDS:
    try:
        r = requests.get(url, headers=UA, timeout=T)
        fp = feedparser.parse(r.content)
        n = len(fp.entries)
        dts = sorted([d for d in (dt_of(e) for e in fp.entries) if d], reverse=True)
        newest = dts[0].strftime("%m-%d %H:%M") if dts else "?"
        sc = [e for e in fp.entries if SCOOP.search(e.get("title","") + body(e))]
        for e in sc:
            scoop_hits.append((dt_of(e), name, e.get("title",""), body(e)))
        flag = f"🔴{len(sc)}" if sc else "-"
        print(f"{name:<18}{r.status_code:>6}{n:>5}{newest:>12}  {flag}")
    except Exception as ex:
        print(f"{name:<18}  FAIL {type(ex).__name__}")
    time.sleep(0.25)

print("\n" + "=" * 70)
print("하닉/삼성 레버리지 스쿱 매칭 상세")
print("=" * 70)
if not scoop_hits:
    print("  ❌ 한국 매체 어디에도 아직 안 뜸")
for d, src, title, bd in sorted([x for x in scoop_hits if x[0]], key=lambda x: x[0], reverse=True)[:6]:
    print(f"\n[{d:%m-%d %H:%M}][{src}] {title[:60]}")
    print(f"   {bd[:200]}")
