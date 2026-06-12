"""일회용 크롤링 타당성 테스트 (스파이크).

목적: 사내 ePrism 프록시 뒤 docker 컨테이너 안에서
  1) 외부 HTTPS(인증서 주입)가 동작하는지
  2) 인포맥스 RSS -> 기사 링크 -> 본문 전체 추출이 되는지
를 확인한다. 본 구현 아님. 검증 끝나면 삭제 가능.
"""
import os
import re
import sys
import time

import requests
from bs4 import BeautifulSoup

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}
TIMEOUT = 90  # 사내 프록시 첫 연결 지연 대비

RSS_FEEDS = {
    "채권/외환 (S1N16)": "https://news.einfomax.co.kr/rss/S1N16.xml",
    "해외주식 (S1N21)": "https://news.einfomax.co.kr/rss/S1N21.xml",
}


def banner(msg):
    print("\n" + "=" * 60)
    print(msg)
    print("=" * 60)


def show_ssl_env():
    banner("1) 컨테이너 SSL 환경변수 (인증서 주입 확인)")
    for k in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"):
        val = os.environ.get(k, "(없음)")
        exists = os.path.exists(val) if val != "(없음)" else False
        print(f"  {k} = {val}  (파일존재={exists})")


def extract_links(xml_text, limit=3):
    return re.findall(r"<link>(https://news\.einfomax\.co\.kr/news/[^<]+)</link>", xml_text)[:limit]


def fetch_article_body(url):
    r = requests.get(url, headers=UA, timeout=TIMEOUT)
    soup = BeautifulSoup(r.text, "lxml")
    node = soup.select_one("#article-view-content-div")
    if node is None:
        return r.status_code, None
    text = re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()
    return r.status_code, text


def main():
    show_ssl_env()

    banner("2) 외부 HTTPS 연결 테스트 (프록시+인증서)")
    for name, url in [("Benzinga", "https://www.benzinga.com/feed"),
                      ("Infomax RSS", RSS_FEEDS["채권/외환 (S1N16)"])]:
        try:
            t0 = time.time()
            r = requests.get(url, headers=UA, timeout=TIMEOUT)
            print(f"  [OK] {name:14s} status={r.status_code} len={len(r.text):>7} "
                  f"({time.time()-t0:.1f}s)")
        except Exception as e:
            print(f"  [FAIL] {name:14s} {type(e).__name__}: {e}")

    banner("3) 인포맥스 RSS -> 기사 본문 전체 추출")
    ok, fail = 0, 0
    for feed_name, feed_url in RSS_FEEDS.items():
        print(f"\n[{feed_name}]")
        try:
            xml = requests.get(feed_url, headers=UA, timeout=TIMEOUT).text
        except Exception as e:
            print(f"  RSS 수집 실패: {e}")
            fail += 1
            continue
        links = extract_links(xml, limit=2)
        if not links:
            print("  기사 링크 추출 실패 (RSS 구조 변경?)")
            continue
        for link in links:
            try:
                status, body = fetch_article_body(link)
                if body:
                    ok += 1
                    print(f"  [OK] {link}")
                    print(f"       status={status} 본문길이={len(body)}자")
                    print(f"       머리말: {body[:120]}...")
                else:
                    fail += 1
                    print(f"  [본문없음] {link} status={status}")
            except Exception as e:
                fail += 1
                print(f"  [FAIL] {link} -> {type(e).__name__}: {e}")

    banner(f"결과: 본문추출 성공 {ok}건 / 실패 {fail}건")
    sys.exit(0 if ok > 0 else 1)


if __name__ == "__main__":
    main()
