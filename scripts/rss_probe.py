"""RSS 프로브 (스파이크). 각 버킷 후보 RSS를 실측한다.

각 피드에 대해: 접속 OK?, 항목수, 최신 발행시각, 샘플 제목/링크,
피드에 본문(full text) 포함 여부, 그리고 첫 기사 링크를 실제로 GET 해서
도달 가능한지(상태/길이)까지 확인한다. 또한 일부 홈페이지에서 RSS 자동탐색.
"""
import time
import requests
import feedparser
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
T = 60

CANDIDATES = {
    "미국주식": [
        "https://www.benzinga.com/feed",
        "https://finance.yahoo.com/news/rssindex",
        "https://feeds.content.dowjones.io/public/rss/mw_topstories",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    ],
    "크립토": [
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "https://cointelegraph.com/rss",
        "https://decrypt.co/feed",
    ],
    "FX": [
        "https://www.fxstreet.com/rss/news",
        "https://www.forexlive.com/feed/news",
        "https://www.investing.com/rss/news_1.rss",
    ],
    "미국채권/매크로": [
        "https://www.federalreserve.gov/feeds/press_all.xml",
        "https://feeds.content.dowjones.io/public/rss/mw_marketpulse",
        "https://news.google.com/rss/search?q=allinurl:reuters.com+markets+when:1d&hl=en-US&gl=US&ceid=US:en",
    ],
}

DISCOVER = ["https://www.reuters.com", "https://www.investing.com", "https://apnews.com"]


def probe_feed(url):
    try:
        r = requests.get(url, headers=UA, timeout=T)
    except Exception as e:
        return f"  [FAIL] GET 실패: {type(e).__name__}: {e}\n        {url}"
    if r.status_code != 200:
        return f"  [WARN] status={r.status_code}  {url}"
    fp = feedparser.parse(r.content)
    n = len(fp.entries)
    if n == 0:
        return f"  [WARN] status=200 이지만 항목 0 (RSS 아님?)  {url}"
    e0 = fp.entries[0]
    title = (e0.get("title") or "")[:55]
    link = e0.get("link") or ""
    pub = e0.get("published") or e0.get("updated") or "?"
    # 피드 내 본문 길이 (content > summary)
    body = ""
    if e0.get("content"):
        body = e0["content"][0].get("value", "")
    body = body or e0.get("summary", "")
    fulltext = "전문" if len(BeautifulSoup(body, "lxml").get_text()) > 600 else "요약/제목"
    # 첫 기사 링크 실제 도달 테스트
    art = ""
    if link:
        try:
            ar = requests.get(link, headers=UA, timeout=T)
            art = f"링크GET={ar.status_code}/{len(ar.text)}자"
        except Exception as ex:
            art = f"링크GET실패({type(ex).__name__})"
    return (f"  [OK] 항목={n:>3} 본문={fulltext:<6} 최신={pub}\n"
            f"       {title}\n"
            f"       {link}\n"
            f"       {art}")


def discover(url):
    try:
        r = requests.get(url, headers=UA, timeout=T)
        soup = BeautifulSoup(r.text, "lxml")
        feeds = [l.get("href") for l in soup.find_all("link",
                 type=lambda t: t and "rss" in t or t == "application/atom+xml")]
        feeds += [a.get("href") for a in soup.find_all("a", href=True)
                  if "rss" in a["href"].lower() or "/feed" in a["href"].lower()]
        feeds = sorted({f for f in feeds if f})[:6]
        return f"  {url} -> status={r.status_code}, 발견 RSS후보:\n" + \
               ("\n".join(f"     {f}" for f in feeds) if feeds else "     (없음)")
    except Exception as e:
        return f"  {url} -> 실패: {type(e).__name__}: {e}"


def main():
    for bucket, feeds in CANDIDATES.items():
        print("\n" + "=" * 64)
        print(f"버킷: {bucket}")
        print("=" * 64)
        for f in feeds:
            print(probe_feed(f))
            time.sleep(0.3)
    print("\n" + "=" * 64)
    print("RSS 자동탐색 (홈페이지 뒤지기)")
    print("=" * 64)
    for u in DISCOVER:
        print(discover(u))


if __name__ == "__main__":
    main()
