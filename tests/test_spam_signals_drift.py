"""SSOT 드리프트 가드: 백엔드 classify.SPAM_SIGNALS == 프런트 web/index.html JUNK.

두 곳이 같은 사실(스팸 시그널 어휘)을 각각 하드코딩 중이라(원칙1·2 위반, unsolved §14①),
한쪽만 고치면 backend kind=spam과 뷰 isJunk 판정이 조용히 드리프트한다.
뷰가 backend kind를 직접 쿼리하도록 이전하기 전까지의 최소 안전망(원칙3 fail-loud).
"""
from __future__ import annotations
import re
from pathlib import Path

from newsstore.enrich.classify import SPAM_SIGNALS

_INDEX = Path(__file__).resolve().parents[1] / "web" / "index.html"


def _parse_junk_array() -> list[str]:
    html = _INDEX.read_text(encoding="utf-8")
    m = re.search(r"const JUNK\s*=\s*\[(.*?)\]\s*;", html, re.DOTALL)
    assert m, "web/index.html에서 const JUNK 배열을 찾지 못함"
    body = m.group(1)
    # JS 줄 주석(//...) 제거 후 따옴표 문자열만 추출
    body = re.sub(r"//[^\n]*", "", body)
    return re.findall(r'"([^"]*)"', body)


def test_spam_signals_match_web_junk():
    junk = _parse_junk_array()
    assert set(SPAM_SIGNALS) == set(junk), (
        "classify.SPAM_SIGNALS와 web/index.html JUNK가 드리프트했다. "
        "한 곳을 고쳤으면 다른 곳도 동기화하라(또는 뷰를 backend kind 쿼리로 이전). "
        f"backend-only={set(SPAM_SIGNALS) - set(junk)} web-only={set(junk) - set(SPAM_SIGNALS)}"
    )
