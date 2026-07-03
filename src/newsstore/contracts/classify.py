from __future__ import annotations

# kind triage(순수 키워드 매칭, 무거운 의존 없음) — collect/store/enrich 공유 계약이라 contracts에 둔다
# (contracts/vectors.add_vectors 와 같은 공유 순수함수 선례). 어휘 SSOT는 이 파일.

# 집단소송 로펌 PR + "$X 투자했다면" 클릭베이트 (web/index.html의 JUNK에서 이식·통합)
SPAM_SIGNALS = [
    "lead plaintiff", "class action", "deadline alert", "shareholder rights law firm",
    "suffered losses in", "encourages investors", "reminds investors", "securities fraud",
    "bragar eagel", "rosen law", "pomerantz", "levi & korsinsky", "glancy prongay",
    "kahn swick", "robbins geller", "faruqi", "schall law", "hagens berman",
    "kessler topaz", "bronstein, gewirtz", "gross law firm", "johnson fistel",
    "kirby mcinerney", "would be worth this much today", "if an investor had bought",
]
# Bloomberg 다이제스트/미디어 롤업 (단일 스토리 아님)
DIGEST_SIGNALS = ["balance of power", "(podcast)", "(video)"]
# 스포츠 (analysis-design §4 — 비파괴 마킹 후 기본 숨김). 명확한 리그/대회 용어만(금융 오분류 회피).
SPORTS_SIGNALS = [
    # " kbo": 선행 경계만 요구 — checkbook/backbone 등 영단어 내부 매칭을 막으면서
    # "KBO리그" 같은 한글 복합어(후행 경계 없음)는 계속 잡는다.
    "한국시리즈", "프로야구", " kbo", "k리그", "프리미어리그", "월드컵", "올림픽",
    "premier league", "world cup", " nba ", " mlb ", " nfl ", "la liga", "bundesliga",
]


def classify_kind(title: str, body: str = "") -> str:
    """story | spam | digest | sports. 비파괴 분류 — 저장은 보존, 임베딩/클러스터·노출 제외 여부만 결정.

    분류는 **제목 기준**(#19): 본문에 우연히 든 신호(예: 멀쩡한 기사 본문의 'class action')로
    오분류(false-positive)하지 않게 한다. body는 호환을 위해 받되 키워드 매칭엔 쓰지 않는다."""
    t = (title or "").strip().lower()
    hay = f" {t} "                     # 양옆 패딩 — ' nba ' 등 경계 신호가 제목 끝에서도 매칭
    if t.endswith(", more") or any(k in hay for k in DIGEST_SIGNALS):
        return "digest"
    if any(k in hay for k in SPAM_SIGNALS):
        return "spam"
    if any(k in hay for k in SPORTS_SIGNALS):
        return "sports"
    return "story"
