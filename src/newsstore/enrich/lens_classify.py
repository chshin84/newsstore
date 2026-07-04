"""Stage1 결정론 렌즈 분류 — asset_hint 1차(신뢰), 태그 보조, region 변별, MAX_LENSES 상한.

production 태그가 자주 비므로(클러스터 패스 tag=False) asset_hint가 핵심 prior다."""
from __future__ import annotations
import logging

from .gemini import LLMError
from .model_config import model_for
from .topics import valid_ids

log = logging.getLogger("newsstore.enrich.lens_classify")

MAX_LENSES = 4
_REGION_PAIRS = [("kr_equity", "us_equity"), ("kr_econ", "us_econ"), ("kr_policy", "us_policy")]


def _region_hint_sets(t: dict) -> tuple[set[str], set[str]]:
    """region 변별 어휘를 topics.yaml(SSOT)에서 도출 — 손복제 상수는 topics.yaml
    개정 시 어긋났던 실적이 있다(us_stock·kr_stock 누락). 규칙 두 가지의 합집합:
    (a) kr_*/us_* 렌즈에 등재된 asset_hint, (b) 어휘 자체의 kr_/us_ 접두사(예: fx
    렌즈의 kr_fx). 양쪽에 다 걸린 어휘는 모호하므로 어느 지역 신호도 아니다."""
    kr: set[str] = set()
    us: set[str] = set()
    all_hints: set[str] = set()
    for lens in t["lenses"]:
        hints = set(lens.get("hints", {}).get("asset_hint", []))
        all_hints |= hints
        if lens["id"].startswith("kr_"):
            kr |= hints
        elif lens["id"].startswith("us_"):
            us |= hints
    kr |= {h for h in all_hints if h.startswith("kr_")}
    us |= {h for h in all_hints if h.startswith("us_")}
    ambiguous = kr & us
    return kr - ambiguous, us - ambiguous


def _match_score(lens: dict, *, asset_hints, tickers, entities, topics, keyword_text) -> int:
    h = lens.get("hints", {})
    score = 0
    score += 2 * len(set(h.get("asset_hint", [])) & set(asset_hints))   # asset_hint 가중(신뢰)
    score += len(set(h.get("entities", [])) & set(entities))
    score += len(set(h.get("topics", [])) & set(topics))
    if lens.get("ticker") and lens["ticker"] in tickers:
        score += 3                                                      # watch ticker 강매칭
    kt = (keyword_text or "").lower()      # 대소문자 무시 — 제목 첫머리 대문자(Gold …) 매칭
    for kw in (h.get("keywords", []) + lens.get("keywords", [])):
        if kw and kw.lower() in kt:
            score += 2
    return score


def classify_stage1(t: dict, *, asset_hints, tickers, entities, topics, language,
                    keyword_text="") -> list[str]:
    scored = []
    for lens in t["lenses"]:
        s = _match_score(lens, asset_hints=asset_hints, tickers=tickers,
                         entities=entities, topics=topics, keyword_text=keyword_text)
        if s > 0:
            scored.append((s, lens["id"]))
    chosen = {lid for _, lid in scored}

    # region 변별: kr/us 쌍 둘 다면 asset_hint로 결정(언어는 약신호 폴백). 모호하면 둘 다 유지(MAX_LENSES가 정리).
    kr_hint, us_hint = _region_hint_sets(t)
    kr_sig = bool(set(asset_hints) & kr_hint)
    us_sig = bool(set(asset_hints) & us_hint)
    for kr, us in _REGION_PAIRS:
        if kr in chosen and us in chosen:
            if kr_sig and not us_sig:
                chosen.discard(us)
            elif us_sig and not kr_sig:
                chosen.discard(kr)
            elif language == "ko" and not us_sig:
                chosen.discard(us)        # 약신호 폴백(asset_hint 모호 시에만)

    # MAX_LENSES: score 내림차순 상위 + 결정론 tiebreak(id)
    ranked = sorted((p for p in scored if p[1] in chosen), key=lambda p: (-p[0], p[1]))
    return [lid for _, lid in ranked[:MAX_LENSES]]


def _lens_menu(t: dict) -> str:
    return "\n".join(f"{l['id']}: {l['label'].get('ko', '')} / {l['label'].get('en', '')}"
                     for l in t["lenses"])


def classify_stage2(t: dict, client, *, story_text, candidates, timeout=30.0) -> list[str]:
    """LLM 1차 멀티라벨 분류 + 결정론 validator. 장애 시 candidates 폴백(fail-soft).

    LLM이 의미로 렌즈를 고르되, 출력은 topics.yaml 어휘로 강제 정제(환각 차단)."""
    prompt = (
        "You classify ONE financial-news story into topic lenses (multi-label, 0 or more).\n"
        "Lenses (id: meaning):\n" + _lens_menu(t) + "\n"
        f"Rules: choose ONLY ids from the list above; multiple allowed; at most {MAX_LENSES}; "
        "choose none if nothing fits; prefer specificity (watch/sector over generic).\n"
        f"Source-hint candidates (may be incomplete): {list(candidates)}\n"
        f"Story:\n{story_text[:1500]}\n"
        'Return JSON {"lenses": ["id", ...]} only.')
    try:
        resp = client.generate_json(prompt, timeout=timeout, model=model_for("lenses"))
    except LLMError as e:                   # LLM 장애만 prior 폴백(로깅) — 코드 버그는 전파(FAIL-LOUD)
        log.warning("lens stage2 fallback to prior (LLM): %s", e)
        return list(candidates)[:MAX_LENSES]
    ids = resp.get("lenses") if isinstance(resp, dict) else None
    if not isinstance(ids, list):           # {"lenses": null}·top-level 배열 등 형태 위반 → prior(fail-soft)
        log.warning("lens stage2 malformed output (lenses=%s) — prior fallback",
                    type(ids).__name__)
        return list(candidates)[:MAX_LENSES]
    valid = valid_ids(t)
    out: list[str] = []
    for i in ids:                           # 결정론 validator: 어휘 밖·중복 제거(FAIL-LOUD 대신 드롭)
        if isinstance(i, str) and i in valid and i not in out:
            out.append(i)
    return out[:MAX_LENSES]                 # 빈 리스트는 정상 무선택 판정 — 호출자가 prior로 덮지 않는다
