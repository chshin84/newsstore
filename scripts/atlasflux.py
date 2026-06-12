"""atlasflux Bloomberg 피드 검증 — 폴링 가능한 RSS인가? 스쿱 잡나? 본문 있나?"""
import re
import requests, feedparser
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
T = 45

URLS = [
    ("디렉토리", "https://atlasflux.saynete.net/atlas_des_flux_rss_ang_dedicated_bloomberg.htm"),
    ("리더php", "http://atlasflux.suptribune.org/Outil_RSS_lecture.php?code_id=37957&charge=_n_i_ag_&urllist=ang_dedicated_bloomberg"),
]

for name, url in URLS:
    print("\n" + "=" * 72)
    print(f"[{name}] {url}")
    print("=" * 72)
    try:
        r = requests.get(url, headers=UA, timeout=T)
        ct = r.headers.get("Content-Type", "?")
        head = r.text[:120].replace("\n", " ")
        print(f"status={r.status_code} type={ct} len={len(r.text)}")
        print(f"머리: {head}")
        # RSS 파싱 시도
        fp = feedparser.parse(r.content)
        print(f"feedparser 항목수: {len(fp.entries)}")
        if fp.entries:
            for e in fp.entries[:8]:
                t = e.get("title", "")
                body = e.get("summary", "")
                blen = len(BeautifulSoup(body, "lxml").get_text()) if body else 0
                print(f"   · {t[:66]}  (본문 {blen}자)")
        else:
            # HTML이면 내부 피드/xml 링크 탐색
            soup = BeautifulSoup(r.text, "lxml")
            links = set()
            for a in soup.find_all("a", href=True):
                h = a["href"]
                if re.search(r"\.xml|rss|flux|lecture\.php|feed", h, re.I):
                    links.add(h)
            print("발견된 피드/xml 후보 링크 (상위 12):")
            for h in list(links)[:12]:
                print(f"     {h}")
    except Exception as ex:
        print(f"FAIL {type(ex).__name__}: {ex}")

# 스쿱 키워드 직접 확인 (리더php 기준)
print("\n" + "=" * 72)
print("스쿱(하닉/삼성/헤지펀드/leverage) 매칭 확인")
print("=" * 72)
try:
    r = requests.get(URLS[1][1], headers=UA, timeout=T)
    fp = feedparser.parse(r.content)
    pat = re.compile(r"hynix|samsung|hedge|leverage|chipmaker|korea", re.I)
    hits = [e for e in fp.entries if pat.search(e.get("title","") + e.get("summary",""))]
    print(f"매칭 {len(hits)}건 / 전체 {len(fp.entries)}")
    for e in hits[:5]:
        print(f"\n · {e.get('title','')[:70]}")
        print(f"   {BeautifulSoup(e.get('summary',''),'lxml').get_text()[:240]}")
except Exception as ex:
    print(f"FAIL {type(ex).__name__}")
