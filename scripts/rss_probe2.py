"""RSS 프로브 라운드2 (스파이크): 라운드1 공백 메우기.
- Reuters 대체: AP 직접 피드 / Google News 쿼리 교정
- 채권 전용 소스 추가 탐색
"""
import time
import requests
import feedparser
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
T = 60

CANDIDATES = {
    "글로벌백본(Reuters대체)": [
        "https://apnews.com/index.rss",
        "https://apnews.com/hub/business.rss",
        "https://news.google.com/rss/search?q=reuters+markets&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=when:1d+US+treasury+yields&hl=en-US&gl=US&ceid=US:en",
    ],
    "채권/금리 전용": [
        "https://www.investing.com/rss/news_25.rss",
        "https://www.investing.com/rss/bonds.rss",
        "https://www.cnbc.com/id/10000664/device/rss/rss.html",
        "https://home.treasury.gov/system/files/126/news.xml",
    ],
}


def probe(url):
    try:
        r = requests.get(url, headers=UA, timeout=T)
    except Exception as e:
        return f"  [FAIL] {type(e).__name__}: {e}\n        {url}"
    fp = feedparser.parse(r.content)
    n = len(fp.entries)
    if r.status_code != 200 or n == 0:
        return f"  [WARN] status={r.status_code} 항목={n}  {url}"
    e0 = fp.entries[0]
    title = (e0.get("title") or "")[:55]
    link = e0.get("link") or ""
    pub = e0.get("published") or e0.get("updated") or "?"
    body = e0["content"][0]["value"] if e0.get("content") else e0.get("summary", "")
    full = "전문" if len(BeautifulSoup(body, "lxml").get_text()) > 600 else "요약/제목"
    art = ""
    if link:
        try:
            ar = requests.get(link, headers=UA, timeout=T)
            art = f"링크GET={ar.status_code}/{len(ar.text)}자"
        except Exception as ex:
            art = f"링크GET실패({type(ex).__name__})"
    return (f"  [OK] 항목={n:>3} 본문={full:<6} 최신={pub}\n"
            f"       {title}\n       {link}\n       {art}")


for bucket, feeds in CANDIDATES.items():
    print("\n" + "=" * 64)
    print(f"버킷: {bucket}")
    print("=" * 64)
    for f in feeds:
        print(probe(f))
        time.sleep(0.3)
