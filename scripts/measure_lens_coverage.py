"""Stage1 렌즈 분류 커버리지 측정(spec §5 '$0 실증').
입력 JSON: [{asset_hints:[], tags:[], members:[{title,body}]}] (예: 실험 stories_full.json).
사용: python scripts/measure_lens_coverage.py <stories.json>"""
import json
import sys
import re
from collections import Counter

from newsstore.enrich import topics
from newsstore.enrich.lens_classify import classify_stage1

_HANGUL = re.compile(r"[가-힣]")


def main(path):
    T = topics.load_topics()
    stories = json.load(open(path, encoding="utf-8"))
    assigned, label_counts, lens_freq = 0, [], Counter()
    for s in stories:
        ahints = s.get("asset_hints", []) or []
        tags = [t for t in (s.get("tags", []) or []) if isinstance(t, str)]
        text = " ".join((m.get("title", "") + " " + (m.get("body") or ""))
                        for m in s.get("members", []))
        lang = "ko" if _HANGUL.search(text) else "en"
        lenses = classify_stage1(T, asset_hints=ahints, tickers=tags, entities=tags,
                                 topics=tags, language=lang, keyword_text=text + " " + " ".join(tags))
        if lenses:
            assigned += 1
            label_counts.append(len(lenses))
            lens_freq.update(lenses)
    n = len(stories)
    print(f"stories={n} | assigned={assigned} ({assigned/n:.0%}) | unassigned={n-assigned} ({(n-assigned)/n:.0%})")
    if label_counts:
        print(f"labels/story: avg={sum(label_counts)/len(label_counts):.2f} max={max(label_counts)}")
    print("top lenses:", lens_freq.most_common(12))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/data/stories_full.json")
