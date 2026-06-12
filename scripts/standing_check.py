"""표준 레지스트리 피드/제네릭 쿼리만으로 하닉·삼성 레버리지 스쿱이 잡히나?
(타깃 쿼리 없이 = 실제 프로덕션이 '콜드'로 잡을지 검증)
"""
import time, re
from datetime import datetime, timezone, timedelta
import requests, feedparser
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
T = 45

# 레지스트리의 '표준' 피드 + '제네릭' 쿼리만 (스토리에 맞춘 타깃 쿼리 없음)
FEEDS = [
    ("인포맥스:전체", "https://news.einfomax.co.kr/rss/allArticle.xml"),
    ("인포맥스:증권", "https://news.einfomax.co.kr/rss/S1N2.xml"),
    ("인포맥스:국제", "https://news.einfomax.co.kr/rss/S1N23.xml"),
    ("인포맥스:해외주식", "https://news.einfomax.co.kr/rss/S1N21.xml"),
    ("Benzinga:news", "https://www.benzinga.com/news/feed"),
    ("Benzinga:markets", "https://www.benzinga.com/markets/feed"),
    ("Benzinga:movers", "https://www.benzinga.com/movers/feed"),
    ("ForexLive", "https://www.forexlive.com/feed/news"),
    ("FXStreet", "https://www.fxstreet.com/rss/news"),
    # 레지스트리 제네릭 GNews 쿼리(스토리 무관)
    ("GNews:rumor", "https://news.google.com/rss/search?q=(reportedly+OR+%22in+talks%22+OR+considering+OR+%22sources+say%22)+(stock+OR+merger+OR+acquisition+OR+raise)+when:12h&hl=en-US&gl=US&ceid=US:en"),
    ("GNews:macro_reuters", "https://news.google.com/rss/search?q=site:reuters.com+(inflation+OR+economy+OR+Fed)+when:12h&hl=en-US&gl=US&ceid=US:en"),
    ("GNews:macro_ap", "https://news.google.com/rss/search?q=site:apnews.com+(economy+OR+inflation+OR+Fed)+when:12h&hl=en-US&gl=US&ceid=US:en"),
]
PAT = re.compile(r"hynix|하이닉스|hedge fund|헤지펀드|leverage|레버리지|prime broker|curb|swap|스왑|베팅", re.I)
# (삼성/samsung 단독은 노이즈 많아 제외 — 핵심 키워드만)

def dt_of(e):
    t = e.get("published_parsed") or e.get("updated_parsed")
    return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc) if t else None

def body(e):
    raw = e["content"][0]["value"] if e.get("content") else e.get("summary", "")
    return re.sub(r"\s+", " ", BeautifulSoup(raw, "lxml").get_text(" ", strip=True))

hits = []
for name, url in FEEDS:
    try:
        fp = feedparser.parse(requests.get(url, headers=UA, timeout=T).content)
        for e in fp.entries:
            txt = e.get("title", "") + " " + body(e)
            if PAT.search(txt):
                hits.append((dt_of(e), name, e.get("title", ""), body(e)))
    except Exception as ex:
        print(f"  [{name}] FAIL {type(ex).__name__}")
    time.sleep(0.2)

hits.sort(key=lambda x: (x[0] is not None, x[0]), reverse=True)
now = datetime.now(timezone.utc)
print(f"현재 {(now+timedelta(hours=9)):%H:%M}KST / 표준 피드에서 레버리지/헤지펀드 키워드 매칭 {len(hits)}건\n")
for d, src, title, bd in hits[:15]:
    ds = d.strftime('%m-%d %H:%M') if d else '  ?  '
    print(f"[{ds}][{src}] {title[:62]}")
