"""Google News 링크 디코딩 + 실제소스 접근 차단 테스트 (스파이크).
(1) 인코딩 링크를 실제 기사 URL로 풀 수 있나
(2) 풀어도 그 소스가 HTTP GET 본문을 주나 / 막나
"""
import base64, re, time
import requests, feedparser
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
T = 45
DOMAIN = re.compile(rb'https?://(?:www\.)?(?:reuters|apnews|wsj|bloomberg|cnbc|'
                    rb'ft|marketwatch|barrons|investing|forexlive|fxstreet)\.com/[^\s"\\\x00-\x1f]+')

RSS = "https://news.google.com/rss/search?q=site:reuters.com+(inflation+OR+economy+OR+Fed)+when:12h&hl=en-US&gl=US&ceid=US:en"

def method_a_base64(link):
    """링크의 base64 id를 디코딩해 URL 추출 시도."""
    try:
        gid = link.split("/articles/")[1].split("?")[0]
        gid += "=" * (-len(gid) % 4)
        raw = base64.urlsafe_b64decode(gid)
        m = DOMAIN.search(raw)
        return m.group(0).decode("utf-8", "ignore") if m else None
    except Exception:
        return None

def method_b_fetch_page(link):
    """gnews 중간페이지 HTML에서 실제 소스 URL 추출 시도."""
    try:
        r = requests.get(link, headers=UA, timeout=T)
        m = DOMAIN.search(r.content)
        return m.group(0).decode("utf-8", "ignore") if m else None
    except Exception:
        return None

def try_fetch_real(url):
    try:
        r = requests.get(url, headers=UA, timeout=T, allow_redirects=True)
        txt = r.text
        body_len = len(BeautifulSoup(txt, "lxml").get_text())
        blocked = (r.status_code != 200) or ("are you a robot" in txt.lower()
                   or "captcha" in txt.lower() or "access denied" in txt.lower()
                   or body_len < 500)
        return f"status={r.status_code} 본문텍스트={body_len}자 -> {'✗ 막힘/빈약' if blocked else '✓ 통과'}"
    except Exception as ex:
        return f"✗ FAIL {type(ex).__name__}: {str(ex)[:40]}"

fp = feedparser.parse(requests.get(RSS, headers=UA, timeout=T).content)
print(f"Google News(reuters) 항목 {len(fp.entries)}개 중 상위 4개 디코딩 시도\n")
for e in fp.entries[:4]:
    print("=" * 70)
    print(f"제목: {e.get('title','')[:64]}")
    link = e.get("link", "")
    a = method_a_base64(link)
    print(f"  [A] base64 디코딩 -> {a or '실패(URL없음)'}")
    b = None
    if not a:
        b = method_b_fetch_page(link)
        print(f"  [B] 중간페이지 파싱 -> {b or '실패'}")
        time.sleep(0.4)
    real = a or b
    if real:
        print(f"  실제 소스 GET 시도: {real[:70]}")
        print(f"    -> {try_fetch_real(real)}")
    time.sleep(0.4)
