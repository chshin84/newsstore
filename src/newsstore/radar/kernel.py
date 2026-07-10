"""레이더 커널 — 신호 1~4의 원값 계산(무임계). 임계·필터는 뷰 계층(daily)에서.

- 렌즈 분류: classify_stage1을 asset_hint·language·keyword_text만으로 호출(태깅 컷 —
  tickers/entities/topics 공집합, 해상도 약화는 스펙 §10 리스크). article_lenses는 '같은
  행 집합을 신호 간 재분류하지 않기 위한 공유 지점'이다 — 호출자가 슬라이스별로 부르는
  것은 허용(로컬 규모에서 비용 무해), 동일 슬라이스의 중복 호출만 금지.
- 신호3 z는 기준선 '일별 분포'로 계산한다(총빈도 비율 근사 금지 — 이진 퇴화 방지).
"""
from __future__ import annotations

import re
import statistics
from collections import Counter

from newsstore.enrich import topics as _topics
from newsstore.enrich.lens_classify import classify_stage1

_ws = re.compile(r"\s+")
STOPWORDS = {"및", "등", "의", "를", "은", "는", "이", "가", "와", "과", "에", "도"}
# 영어 기능어 — 첫 실데이터 일보(2026-07-10)에서 신호3·4가 on/as/Is/Why/After 류에
# 침수된 실측 결함의 수정. 내용어(AI·Stock 등)는 남긴다 — 추가 조정은 백테스트 캘리브레이션의 몫.
STOPWORDS_EN = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "at", "as", "is", "are",
    "was", "were", "be", "been", "it", "its", "this", "that", "these", "those",
    "what", "why", "how", "when", "where", "here", "there", "with", "for", "by",
    "from", "after", "before", "while", "will", "would", "can", "could", "has",
    "have", "had", "but", "not", "no", "so", "if", "than", "then", "into", "about",
    "over", "under", "out", "up", "down", "says", "said", "say", "amid", "his",
    "her", "their", "our", "your", "my", "off", "all", "more", "most",
}


def _norm_token(t: str) -> str:
    """라틴 토큰은 소문자로 접어 대소문자 변형('After'/'after')의 이중 집계를 막는다."""
    return t.lower() if t.isascii() else t


def dedup(rows: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out = []
    for r in rows:
        key = _ws.sub(" ", (r.get("title") or "").strip()).lower()
        if key and key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def zscore(current: float, baseline: list[float]):
    if not baseline:
        return "new" if current > 0 else 0.0
    mean = statistics.fmean(baseline)
    sd = statistics.pstdev(baseline)
    if sd == 0:
        return "new" if current > mean else 0.0
    return (current - mean) / sd


def baseline_coverage(days_with_data: list, *, window_days: int, min_ratio: float) -> tuple[bool, str]:
    ratio = len(days_with_data) / window_days
    if ratio < min_ratio:
        return False, f"결측: 기준선 데이터 부족({len(days_with_data)}/{window_days}일)"
    return True, ""


def article_lenses(rows: list[dict]) -> dict[str, list[str]]:
    """기사 id → 렌즈 목록. 기사당 1회만 분류(신호1·4 공유)."""
    t = _topics.load_topics()
    out: dict[str, list[str]] = {}
    for r in rows:
        kt = ((r.get("title") or "") + " " + (r.get("body") or "")[:200]).lower()
        out[r["id"]] = classify_stage1(
            t, asset_hints=[r["asset_hint"]] if r.get("asset_hint") else [],
            tickers=[], entities=[], topics=[],
            language=r.get("language") or "", keyword_text=kt)
    return out


def lens_counts_from(per_article: dict[str, list[str]]) -> dict[str, int]:
    c: Counter = Counter()
    for lenses in per_article.values():
        for lens in lenses:
            c[lens] += 1
    return dict(c)


def new_edges(current: set[tuple[str, str]], prev_weeks: list[set]) -> set:
    prev_all = set().union(*prev_weeks) if prev_weeks else set()
    return current - prev_all


def cooccur_edges(rows: list[dict], vocab: list[str], find_alias) -> set[tuple[str, str]]:
    edges: set = set()
    for r in rows:
        text = (r.get("title") or "") + " " + (r.get("body") or "")[:200]
        hits = sorted({v for v in vocab if find_alias(v, text)})
        for i in range(len(hits)):
            for j in range(i + 1, len(hits)):
                edges.add((hits[i], hits[j]))
    return edges


def _tokens(title: str):
    """유니그램은 len≥2·불용어 필터, 바이그램은 필터 전 '원시 토큰열'로 조립한다 —
    1글자 토큰('덫')이 먼저 탈락하면 '변동성 덫' 같은 구가 구조적으로 검출 불가가 되고,
    탈락 토큰을 건너뛴 가짜 인접쌍이 생기기 때문(재리뷰 critical — 스펙 §5의 '1글자 제외'는
    유니그램에만 적용된다는 부록을 Task 8 커밋에서 스펙에 한 줄 추가한다)."""
    raw = [_norm_token(t) for t in re.split(r"[^0-9A-Za-z가-힣]+", title or "") if t]
    unigrams = [t for t in raw if len(t) >= 2 and t not in STOPWORDS
                and t not in STOPWORDS_EN]
    bigrams = [" ".join(p) for p in zip(raw, raw[1:])]
    return unigrams + bigrams


def emerging_terms(titles_now: list[str], baseline_days: list[list[str]],
                   *, w_days: int) -> list[tuple[str, int, object]]:
    """(term, 창 빈도, z 원값). 기준선은 '일별 제목 리스트' — 일별 카운트 분포로 진짜 z를 계산.
    창 빈도는 일평균(cnt/w_days)으로 정규화해 기준선 일별 분포와 스케일을 맞춘다."""
    now = Counter(t for title in titles_now for t in _tokens(title))
    day_counters = [Counter(t for title in day for t in _tokens(title)) for day in baseline_days]
    out = []
    for term, cnt in now.items():
        series = [dc.get(term, 0) for dc in day_counters]
        z = zscore(cnt / max(w_days, 1), series)
        out.append((term, cnt, z))
    out.sort(key=lambda x: (-x[1], x[0]))
    return out


def cross_lens_spread(term_hits: dict[str, list[str]],
                      per_article: dict[str, list[str]]) -> dict[str, int]:
    """term → 걸치는 렌즈 수. term_hits: term → 매칭 기사 id 목록(분류는 per_article 재사용)."""
    return {term: len({lens for iid in ids for lens in per_article.get(iid, [])})
            for term, ids in term_hits.items()}
