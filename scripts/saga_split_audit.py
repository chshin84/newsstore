"""사가 분리 측정(비침습·읽기 전용) — 스펙 2026-07-05-report-edge-and-saga.md A3.

목적: "같은 사가가 얼마나·어디서 여러 스토리로 갈리나 + 클러스터 재캘 vs LLM 사가 중 무엇이
처방인가"를 **측정**한다. 사가 병합 구현은 이 측정이 처방을 고른 뒤 별도 스펙(여기선 구현 X).

비침습 계약:
- 프로덕션 리포트 경로·store 코드·프로덕션 문서 **무변경**. stories 컬렉션을 **읽기 전용**으로
  직접 조회하고(get_stories_for_report는 entities/임베딩을 안 돌려줌), 결과는 사람이 읽는
  리포트(stdout)로만 낸다.
- **임베딩 공간 패리티(critical)**: 코사인을 gray-band 병합 임계와 대조하려면 프로덕션 클러스터가
  쓴 것과 같은 임베딩 공간이어야 한다. 저장된 스토리 임베딩(centroid_sum, 768차원)을 **재사용**해
  재임베딩 비용·드리프트를 피한다. 재임베딩이 불가피하면 embedder 설정(gemini-embedding-001,
  output_dimensionality=768, 동일 task_type, title+body 입력)을 그대로 재사용하고 `len(vec)==768`을
  fail-loud로 단언한다(차원 불일치 시 zip 무음 절단=가짜 코사인 — solved 교훈).

사용(Docker): `docker compose run --rm collect python scripts/saga_split_audit.py [--llm]`
(순수 로직은 tests/test_saga_split_audit.py가 fake 주입으로 결정론 검증.)
"""
from __future__ import annotations
import argparse
import math
import re
from datetime import datetime, timedelta, timezone
from statistics import median

EMBED_DIM = 768                       # enrich.embedder.EMBED_DIM와 동일 — 패리티 단언 기준(fail-loud)
DEFAULT_WINDOW_HOURS = 72.0           # 최근 리포트 스토리 창(cutoff)
DEFAULT_PROXIMITY_HOURS = 48.0        # 시간 근접(사가 전개는 대개 며칠 내)
DEFAULT_MIN_COS = 0.0                 # 후보 코사인 floor(0=분포 절단 없음 — 임계 대조를 위해 온전히 남김)
DEFAULT_LLM_CAP = 50                  # 오프라인 정밀도 1패스 상한 쌍 수(비용)
NEGLIGIBLE_RATIO = 0.05               # 분리율 < 5% → 사가 불필요(게이트)
CLEARLY_BELOW = 0.1                   # 중앙값 < 임계−0.1 → 임베딩상 확연히 낮음(LLM 사가 후보)

# 제목 키워드 폴백(entities 없을 때)용 흔한 불용어 — 개체 공유를 과대평가하지 않게 최소만.
_STOP = frozenset({
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "as", "at",
    "by", "is", "are", "was", "be", "그", "이", "저", "및", "등", "the", "news", "속보",
})
_WORD = re.compile(r"[0-9A-Za-z가-힣]{2,}")


# ── 벡터 산술(패리티 fail-loud) ─────────────────────────────────────────────────
def cosine(a, b) -> float:
    """코사인 유사도. 두 벡터 모두 정확히 EMBED_DIM이어야 한다(fail-loud) — 차원이 다르면
    zip이 짧은 쪽에 맞춰 조용히 절단해 '가짜 코사인'을 낸다(solved 교훈). centroid_sum은 정규화
    안 돼 있어도 코사인은 크기 불변이라 프로덕션 임베딩(합)을 그대로 대조할 수 있다."""
    if len(a) != EMBED_DIM or len(b) != EMBED_DIM:
        raise ValueError(f"embedding dim {len(a)}/{len(b)} != {EMBED_DIM} "
                         "(패리티 위반 — zip 무음 절단 방지 fail-loud)")
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return 0.0 if na == 0.0 or nb == 0.0 else dot / (na * nb)


# ── 후보 축소(결정론) ──────────────────────────────────────────────────────────
def dominant_keys(story: dict) -> set[str]:
    """스토리의 지배 개체 집합 — entities 우선, 없으면 제목 키워드 폴백. 사가 후보는 같은 개체를
    공유해야 한다(우연히 주제만 겹치는 무관 사가 배제)."""
    ents = {str(e).strip().lower() for e in (story.get("entities") or []) if str(e).strip()}
    if ents:
        return ents
    return {w.lower() for w in _WORD.findall(story.get("title") or "")
            if w.lower() not in _STOP}


def share_dominant_entity(a: dict, b: dict) -> bool:
    return bool(dominant_keys(a) & dominant_keys(b))


def _story_time(story: dict):
    """스토리 대표 시각 — last_seen 우선, 없으면 developments 최신 delta_time."""
    ls = story.get("last_seen")
    if ls is not None:
        return ls
    times = [d.get("delta_time") or d.get("time") for d in (story.get("developments") or [])]
    times = [t for t in times if t is not None]
    return max(times) if times else None


def time_proximate(a: dict, b: dict, *, window: timedelta) -> bool:
    ta, tb = _story_time(a), _story_time(b)
    if ta is None or tb is None:
        return False
    return abs((ta - tb).total_seconds()) <= window.total_seconds()


def _embed_of(story: dict):
    """스토리 임베딩(프로덕션 저장분 재사용) — centroid_sum(합) 우선, embedding 폴백."""
    return story.get("centroid_sum") or story.get("embedding")


def candidate_pairs(stories: list[dict], *, window: timedelta, min_cos: float = DEFAULT_MIN_COS,
                    embed_of=_embed_of) -> list[dict]:
    """결정론 후보 축소 — (지배 개체 공유) ∧ (시간 근접) ∧ (코사인 ≥ floor)인 스토리 쌍.
    같은 사가로 의심되는 서로 다른 스토리 쌍을 찾는다(임베딩은 패리티 준수). 코사인 내림차순.
    embed_of 주입 가능(기본=저장 임베딩 재사용).

    비교 의미 주의(측정 타당성): 여기 코사인은 스토리 centroid_sum(=멤버 임베딩 합, 코사인상 평균)
    끼리다. 프로덕션 gray-band 임계는 기사→스토리 centroid(온라인 assign)·max 기사쌍(배치 머지)에서
    캘리브레이션됐다. 임베딩 '공간'은 같지만(패리티 충족) centroid↔centroid 값은 그 비교들보다
    체계적으로 낮다 — 임계 대조는 **방향 지표**이지 정밀 판정이 아니다(스펙 A3: 임계는 산출 데이터로
    확정, 지금은 방향만)."""
    out: list[dict] = []
    n = len(stories)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = stories[i], stories[j]
            if not share_dominant_entity(a, b):
                continue
            if not time_proximate(a, b, window=window):
                continue
            va, vb = embed_of(a), embed_of(b)
            if not va or not vb:
                continue
            cos = cosine(va, vb)
            if cos < min_cos:
                continue
            shared = sorted(set(a.get("lenses") or []) & set(b.get("lenses") or []))
            out.append({"a": a.get("id"), "b": b.get("id"), "cosine": cos, "lenses": shared})
    out.sort(key=lambda p: (-p["cosine"], p["a"] or "", p["b"] or ""))
    return out


def cosine_distribution(candidates: list[dict]) -> dict:
    """후보 코사인 분포(min/p25/median/p75/max) — 병합 임계와 대조용."""
    cs = sorted(c["cosine"] for c in candidates)
    if not cs:
        return {"n": 0}

    def _pct(q: float) -> float:
        return cs[min(len(cs) - 1, int(q * len(cs)))]

    return {"n": len(cs), "min": cs[0], "p25": _pct(0.25), "median": median(cs),
            "p75": _pct(0.75), "max": cs[-1]}


def per_lens_counts(candidates: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for c in candidates:
        for l in (c["lenses"] or ["(공유 렌즈 없음)"]):
            out[l] = out.get(l, 0) + 1
    return out


def prescribe(*, n_stories: int, candidates: list[dict], merge_lo: float, merge_hi: float,
              negligible_ratio: float = NEGLIGIBLE_RATIO,
              clearly_below: float = CLEARLY_BELOW) -> dict:
    """정량 판정 게이트(스펙 A3) — 후보 코사인 중앙값 vs 병합 임계(gray-band lo)로 처방 도출.
    'cluster_recal'=임계 바로 아래서 갈림 → 재캘로 해소 / 'llm_saga'=임베딩상 멀지만 같은 사가일
    수 있음 → 의미 기반 LLM 사가 / 'saga_unnecessary'=분리율 무시 수준 / 'inconclusive'=애매."""
    n_cand = len(candidates)
    split_rate = (n_cand / n_stories) if n_stories else 0.0
    med = median([c["cosine"] for c in candidates]) if candidates else 0.0
    if split_rate < negligible_ratio:
        rx = "saga_unnecessary"
    elif med >= merge_lo:
        rx = "cluster_recal"
    elif med < merge_lo - clearly_below:
        rx = "llm_saga"
    else:
        rx = "inconclusive"
    return {"n_stories": n_stories, "n_candidates": n_cand, "split_rate": split_rate,
            "cosine_median": med, "merge_lo": merge_lo, "merge_hi": merge_hi, "prescription": rx}


def llm_same_saga_labels(candidates: list[dict], stories: list[dict], llm, *,
                         cap: int = DEFAULT_LLM_CAP) -> dict:
    """오프라인 정밀도(선택) — 후보 상위 cap쌍에 'SAME 사가?' 1패스 라벨. **프로덕션 콜 아님**
    (측정 스크립트 내부, 사람 판단 보조). llm 주입(fake 가능). 반환 {(a,b): bool}."""
    by_id = {s.get("id"): s for s in stories}
    labels: dict[tuple, bool] = {}
    for c in candidates[:cap]:
        a, b = by_id.get(c["a"]), by_id.get(c["b"])
        if not a or not b:
            continue
        prompt = (
            "두 뉴스 스토리가 같은 '사가'(하나의 큰 사건·위기가 펼쳐지는 여러 국면)에 속하나? "
            "핵심 사건이 같고 그 후속·측면·여파면 SAME, 주제만 겹칠 뿐 핵심 사건이 다르면 "
            "DIFFERENT. 첫 줄에 SAME 또는 DIFFERENT만.\n"
            f"[A] {a.get('title', '')} :: {(a.get('summary') or '')[:300]}\n"
            f"[B] {b.get('title', '')} :: {(b.get('summary') or '')[:300]}\n")
        resp = (llm.complete(prompt) or "").strip().upper()   # 실 SDK None 가드
        labels[(c["a"], c["b"])] = resp.startswith("SAME")
    return labels


def audit(stories: list[dict], *, window: timedelta, merge_lo: float, merge_hi: float,
          min_cos: float = DEFAULT_MIN_COS) -> dict:
    """측정 전체 산출(순수) — 후보·분포·렌즈별·예시·처방. I/O 없음(테스트 대상)."""
    cands = candidate_pairs(stories, window=window, min_cos=min_cos)
    verdict = prescribe(n_stories=len(stories), candidates=cands,
                        merge_lo=merge_lo, merge_hi=merge_hi)
    return {**verdict, "distribution": cosine_distribution(cands),
            "per_lens": per_lens_counts(cands), "examples": cands[:10], "candidates": cands}


# ── 리포트 포맷(사람 읽기용) ────────────────────────────────────────────────────
def format_report(result: dict, *, labels: dict | None = None) -> str:
    dist = result["distribution"]
    lines = [
        "=== 사가 분리 측정 (비침습·읽기 전용) ===",
        f"스토리 수: {result['n_stories']} | 후보 쌍: {result['n_candidates']} | "
        f"분리율(후보/스토리): {result['split_rate']:.1%}",
        f"병합 임계(gray-band): lo={result['merge_lo']:.3f} hi={result['merge_hi']:.3f}",
    ]
    if dist.get("n"):
        lines.append(f"후보 코사인 분포: min={dist['min']:.3f} p25={dist['p25']:.3f} "
                     f"median={dist['median']:.3f} p75={dist['p75']:.3f} max={dist['max']:.3f}")
        lines.append(f"코사인 vs 병합 임계(lo): 중앙값 {dist['median']:.3f} "
                     f"{'≥' if dist['median'] >= result['merge_lo'] else '<'} {result['merge_lo']:.3f}")
    else:
        lines.append("후보 코사인 분포: (후보 없음)")
    if result["per_lens"]:
        lines.append("렌즈별 후보 수: " + ", ".join(
            f"{k}={v}" for k, v in sorted(result["per_lens"].items(), key=lambda t: -t[1])))
    lines.append("예시(코사인 상위):")
    for e in result["examples"]:
        tag = ""
        if labels is not None:
            same = labels.get((e["a"], e["b"]))
            tag = f" [LLM={'SAME' if same else 'DIFF' if same is not None else '?'}]"
        lines.append(f"  cos={e['cosine']:.3f} {e['a']} ↔ {e['b']} "
                     f"(렌즈: {','.join(e['lenses']) or '-'}){tag}")
    if labels is not None and labels:
        agree = sum(1 for e in result["examples"]
                    if labels.get((e["a"], e["b"])) is True)
        lines.append(f"LLM 'SAME' 판정(상위 예시 {len(result['examples'])}쌍 중): {agree}")
    lines.append(f"→ 처방: {result['prescription']}  "
                 "(cluster_recal=임계 바로 아래 갈림·재캘 / llm_saga=의미 기반 / "
                 "saga_unnecessary=분리율 무시 / inconclusive=애매)")
    lines.append("주의: 코사인은 스토리 centroid_sum(평균)끼리다. 프로덕션 병합 임계는 "
                 "기사→centroid(온라인)·max 기사쌍(배치)에서 캘리브레이션됐으므로 이 값은 "
                 "그보다 체계적으로 낮다 — 임계 대조는 방향 지표이지 정밀 판정이 아니다"
                 "(스펙: 임계는 산출 데이터로 확정). 처방을 과신하지 말 것.")
    return "\n".join(lines)


# ── 읽기 전용 조회 + 엔트리 ─────────────────────────────────────────────────────
def load_stories(db, *, cutoff, dim: int = EMBED_DIM):
    """읽기 전용 — open 스토리에서 centroid_sum(프로덕션 임베딩) + 개체·시간·렌즈를 직접 조회한다.
    get_stories_for_report는 entities/centroid_sum을 안 돌려주므로 여기서 직접 읽는다(프로덕션 store
    코드 무변경). 차원≠dim(백필 전 스토리 등)은 코사인 무의미이므로 제외하고 그 수를 반환에 실어
    fail-loud로 노출한다(조용히 삼키지 않음)."""
    out, skipped_dim = [], 0
    for snap in db.collection("stories").where("status", "==", "open").stream():
        d = snap.to_dict() or {}
        if not (d.get("last_seen") and d["last_seen"] >= cutoff):
            continue
        csum = list(d.get("centroid_sum") or [])
        if len(csum) != dim:
            skipped_dim += 1
            continue
        out.append({"id": snap.id, "title": d.get("title") or "",
                    "summary": d.get("summary") or "", "entities": d.get("entities") or [],
                    "lenses": d.get("lenses") or [], "developments": d.get("developments") or [],
                    "last_seen": d.get("last_seen"), "centroid_sum": csum})
    return out, skipped_dim


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="사가 분리 측정(비침습·읽기 전용)")
    ap.add_argument("--window-hours", type=float, default=DEFAULT_WINDOW_HOURS,
                    help="최근 스토리 창(cutoff)")
    ap.add_argument("--proximity-hours", type=float, default=DEFAULT_PROXIMITY_HOURS,
                    help="후보 시간 근접 창")
    ap.add_argument("--min-cos", type=float, default=DEFAULT_MIN_COS, help="후보 코사인 floor")
    ap.add_argument("--llm", action="store_true",
                    help="오프라인 LLM 정밀도 1패스(선택·실 임베딩/LLM 콜 비용 발생)")
    ap.add_argument("--llm-cap", type=int, default=DEFAULT_LLM_CAP)
    args = ap.parse_args(argv)

    import os
    from newsstore.enrich.clustering import env_gray_band
    from newsstore.store.factory import make_store
    lo, hi = env_gray_band()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=args.window_hours)
    with make_store() as store:
        stories, skipped_dim = load_stories(store.db, cutoff=cutoff)
    if skipped_dim:
        print(f"[경고] centroid_sum 차원≠{EMBED_DIM}인 스토리 {skipped_dim}건 제외 "
              "(백필 전·재임베딩 필요 — 패리티 위반이라 코사인 대조 무의미).")
    result = audit(stories, window=timedelta(hours=args.proximity_hours),
                   merge_lo=lo, merge_hi=hi, min_cos=args.min_cos)
    labels = None
    if args.llm:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("[경고] --llm 지정됐으나 GEMINI_API_KEY 없음 — LLM 정밀도 생략.")
        else:
            from newsstore.enrich.gemini import GeminiClient
            client = GeminiClient(api_key)
            labels = llm_same_saga_labels(result["candidates"], stories, client, cap=args.llm_cap)
    print(format_report(result, labels=labels))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
