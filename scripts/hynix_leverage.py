"""SK하이닉스·삼성 헤지펀드 레버리지 제한 스쿱을 우리 파이프라인이 잡나?"""
import time, re
from datetime import datetime, timezone, timedelta
import requests, feedparser
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
T = 45

FEEDS = [
    ("인포맥스:해외주식", "https://news.einfomax.co.kr/rss/S1N21.xml"),
    ("인포맥스:증권", "https://news.einfomax.co.kr/rss/S1N2.xml"),
    ("인포맥스:국제", "https://news.einfomax.co.kr/rss/S1N23.xml"),
    ("인포맥스:채권/외환", "https://news.einfomax.co.kr/rss/S1N16.xml"),
    ("인포맥스:전체", "https://news.einfomax.co.kr/rss/allArticle.xml"),
    ("GNews:한글스쿱", "https://news.google.com/rss/search?q=(SK%ED%95%98%EC%9D%B4%EB%8B%89%EC%8A%A4+OR+%EC%82%BC%EC%84%B1%EC%A0%84%EC%9E%90)+(%ED%97%A4%EC%A7%80%ED%8E%80%EB%93%9C+OR+%EB%A0%88%EB%B2%84%EB%A6%AC%EC%A7%80+OR+%EC%8A%A4%EC%99%91)+when:12h&hl=ko&gl=KR&ceid=KR:ko"),
    ("GNews:EngScoop", "https://news.google.com/rss/search?q=(%22SK+Hynix%22+OR+Samsung)+(hedge+fund+OR+leverage+OR+swaps+OR+%22prime+broker%22)+when:12h&hl=en-US&gl=US&ceid=US:en"),
    ("GNews:루머", "https://news.google.com/rss/search?q=(reportedly+OR+%22sources+say%22+OR+Bloomberg)+(hedge+fund+OR+leverage+OR+chipmaker)+when:12h&hl=en-US&gl=US&ceid=US:en"),
]
PAT = re.compile(r"하이닉스|하닉|삼성전자|hynix|samsung|헤지펀드|hedge fund|레버리지|leverage|스왑|swap|prime broker|프라임|씨티|citi|jpmorgan|골드만|goldman|디레버리지|마진|financing|중개", re.I)

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

hits = [x for x in items if PAT.search(x[2] + " " + x[3]) and x[0]]
hits.sort(key=lambda x: x[0], reverse=True)
now = datetime.now(timezone.utc)
print(f"현재 {now:%H:%M}UTC = {(now+timedelta(hours=9)):%H:%M}KST / 매칭 {len(hits)}건\n")
for d, src, title, bd in hits[:12]:
    print(f"[{d:%m-%d %H:%M}][{src}] {title[:62]}")
    print(f"   {bd[:280]}\n")
