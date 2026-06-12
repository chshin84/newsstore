"""피드는 열리고 기사페이지는 막히나? + 피드가 전문/요약 어느쪽인가 (경량 확인)."""
import requests, feedparser
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
T = 40

FEEDS = ["https://www.benzinga.com/topic/stock-of-the-day/feed",
         "https://www.benzinga.com/markets/bonds/feed",
         "https://www.benzinga.com/news/earnings/feed"]

print("== 피드 접근 + 본문(전문/요약) ==")
first_link = None
for u in FEEDS:
    r = requests.get(u, headers=UA, timeout=T)
    fp = feedparser.parse(r.content)
    e = fp.entries[0] if fp.entries else None
    if not e:
        print(f"  [{r.status_code}] n=0  {u}"); continue
    enc = e["content"][0]["value"] if e.get("content") else ""
    summ = e.get("summary", "")
    enc_len = len(BeautifulSoup(enc, "lxml").get_text()) if enc else 0
    summ_len = len(BeautifulSoup(summ, "lxml").get_text()) if summ else 0
    kind = "전문(content:encoded)" if enc_len > 600 else ("요약" if summ_len else "제목만")
    print(f"  [{r.status_code}] {u.split('benzinga.com/')[1]}")
    print(f"        content:encoded={enc_len}자  summary={summ_len}자  -> {kind}")
    if not first_link:
        first_link = e.get("link")

print("\n== 기사 페이지 직접 접근 (막히나?) ==")
print(f"  대상: {first_link}")
try:
    ar = requests.get(first_link, headers=UA, timeout=T)
    blocked = "차단/챌린지" if (ar.status_code != 200 or "cf-" in ar.text[:2000].lower()
                              or "captcha" in ar.text.lower()) else "통과"
    print(f"  status={ar.status_code} len={len(ar.text)} -> {blocked}")
except Exception as ex:
    print(f"  실패: {type(ex).__name__}: {ex}")
