"""태그 커버리지 측정(#8) — 통제 어휘 범위 결정을 위한 데이터.

순수 함수(tag_coverage)는 store 없이 단위 테스트한다. 라이브 집계는 얇은 엔트리포인트가
`items.tags`를 읽어 이 함수에 넘긴다 — '어디까지 태그 어휘에 넣을지'를 빈도·미매칭으로 본다.
"""
from __future__ import annotations
from collections import Counter


def tag_coverage(items_tags: list[list[str]], vocab: set[str] | None = None) -> dict:
    """기사별 태그 리스트 → 커버리지 리포트.

    - total/untagged/untagged_rate: 태깅 누락(무태그) 정도.
    - tag_freq: (태그, 빈도) 내림차순 — 실제로 쓰이는 어휘.
    - out_of_vocab: vocab 주면, 거기 없는 태그의 (태그, 빈도) — 추가 후보 또는 노이즈.
    """
    total = len(items_tags)
    untagged = sum(1 for t in items_tags if not t)
    freq = Counter(tag for t in items_tags for tag in t)
    report = {
        "total": total,
        "untagged": untagged,
        "untagged_rate": (untagged / total) if total else 0.0,
        "tag_freq": freq.most_common(),
    }
    if vocab is not None:
        report["out_of_vocab"] = [(tag, n) for tag, n in freq.most_common()
                                  if tag not in vocab]
    return report
