from __future__ import annotations

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


def classify_kind(title: str, body: str = "") -> str:
    """story | spam | digest. 비파괴 분류 — 저장은 보존, 임베딩/클러스터 제외 여부만 결정."""
    t = (title or "").strip().lower()
    s = f"{t} {(body or '').lower()}"
    if t.endswith(", more") or any(k in s for k in DIGEST_SIGNALS):
        return "digest"
    if any(k in s for k in SPAM_SIGNALS):
        return "spam"
    return "story"
