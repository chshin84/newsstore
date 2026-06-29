# Phase 1 — 토픽 렌즈 멀티라벨 분류 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`).

**Goal:** 스토리를 큐레이션 토픽 렌즈에 멀티라벨로 분류해 `stories.lenses[]`를 채운다(결정론 Stage1 중심, asset_hint 기반).

**Architecture:** `config/topics.yaml`(렌즈 SSOT, 모든 렌즈를 `lenses[]` 한 배열에 `type` 포함) → `enrich/topics.py`(로더+registry) → `enrich/lens_classify.py`(Stage1 결정론 매칭: asset_hint 1차·태그 보조·region 변별·MAX_LENSES) → `run_enrich --mode lenses`가 스토리에 적용 → `stories.lenses[]`. Stage2 LLM은 후속 task(조건부).

**Tech Stack:** Python 3.12, pyyaml, Docker(`MSYS_NO_PATHCONV=1 docker compose run --rm test`). 새 의존성 0(pyyaml 이미 있음).

**Spec:** `docs/superpowers/specs/2026-06-29-phase1-topic-lenses-design.md`

**핵심 gotchas:** 매직넘버 금지(불변식) · mock/None 가드 · asset_hint가 신뢰 prior(태그는 자주 빔) · 비파괴(additive 필드).

---

## File Structure
| 파일 | 책임 | 변경 |
|---|---|---|
| `config/topics.yaml` | 렌즈 SSOT(lenses[] + type + hints) | Create |
| `src/newsstore/enrich/topics.py` | topics.yaml 로드 + registry + `lens_type`/`valid_ids` | Create |
| `src/newsstore/enrich/lens_classify.py` | Stage1 결정론 분류 | Create |
| `src/newsstore/store/firestore_store.py` | `save_story_lenses` + `get_stories_for_lensing` | Modify |
| `src/newsstore/contracts/ports.py` | Store 계약에 두 메서드 | Modify |
| `src/newsstore/entrypoints/run_enrich.py` | `--mode lenses` 패스 | Modify |
| `docs/firestore-contract.md` | `stories.lenses[]` 필드 | Modify |
| `tests/test_topics.py`·`test_lens_classify.py`·`test_lens_pass.py` | 단위·골든·계약 | Create |

---

## Task 1: `topics.yaml` + 로더 + 무결성 테스트

**Files:** Create `config/topics.yaml`, `src/newsstore/enrich/topics.py`, `tests/test_topics.py`

- [ ] **Step 1: 실패 테스트**

`tests/test_topics.py`:
```python
from newsstore.enrich import topics


def test_load_and_registry():
    t = topics.load_topics()
    ids = topics.valid_ids(t)
    assert "kr_rates" in ids and "watch_samsung" in ids and "sector_tech" in ids
    assert topics.lens_type(t, "kr_rates") == "standing"
    assert topics.lens_type(t, "kr_policy") == "development"
    assert topics.lens_type(t, "sector_tech") == "sector"
    assert topics.lens_type(t, "watch_samsung") == "watch"
    assert topics.lens_type(t, "risk") == "risk"


def test_hint_vocab_integrity():
    # 모든 topics/entities hint가 taxonomy.yaml 어휘에 실재(드리프트 가드)
    import yaml
    tax = yaml.safe_load(open("config/taxonomy.yaml", encoding="utf-8"))
    tv, ev = set(tax["topics"]), set(tax["entities"])
    t = topics.load_topics()
    for lens in t["lenses"]:
        h = lens.get("hints", {})
        assert set(h.get("topics", [])) <= tv, f"{lens['id']} topics drift: {h.get('topics')}"
        assert set(h.get("entities", [])) <= ev, f"{lens['id']} entities drift"


def test_watch_count_and_max():
    t = topics.load_topics()
    watch = [l for l in t["lenses"] if l["type"] == "watch"]
    assert len(watch) <= 10
    sectors = [l for l in t["lenses"] if l["type"] == "sector"]
    assert len(sectors) <= 11   # GICS vocab
```

- [ ] **Step 2: 실패 확인** — `... pytest tests/test_topics.py -v` → FAIL (ModuleNotFound)

- [ ] **Step 3: `config/topics.yaml` 작성**

모든 렌즈를 `lenses[]` 한 배열에 `type` 포함(일관성 리뷰 반영). hints의 topics/entities는 `taxonomy.yaml` 어휘만 사용:
```yaml
version: "2026-06-29"
sectors_surface_top_n: 5          # 활성 top-N 노출 메타(Phase 4에서 소비)
lenses:
  # ── 금융자산 (standing) ──
  - {id: kr_rates, type: standing, label: {ko: 한국 금리·채권, en: KR Rates}, hints: {asset_hint: [kr_bond, kr_macro], entities: [한국은행], topics: [rates, bonds, central_bank]}}
  - {id: us_rates, type: standing, label: {ko: 미국 금리·채권, en: US Rates}, hints: {entities: [Fed, Treasury], topics: [rates, bonds, central_bank]}}
  - {id: fx, type: standing, label: {ko: 환율, en: FX}, hints: {asset_hint: [fx, kr_fx], topics: [fx]}}
  - {id: oil_energy, type: standing, label: {ko: 유가·에너지, en: Oil/Energy}, hints: {asset_hint: [energy], entities: [OPEC], topics: [energy]}}
  - {id: precious_metals, type: standing, label: {ko: 귀금속, en: Metals}, hints: {keywords: [금값, gold, silver, 은값], topics: [commodities]}}
  - {id: commodities, type: standing, label: {ko: 기타 원자재, en: Commodities}, hints: {asset_hint: [commodity], topics: [commodities]}}
  - {id: kr_realestate, type: standing, label: {ko: 한국 부동산, en: KR Real Estate}, hints: {asset_hint: [kr_realestate], topics: [housing]}}
  - {id: kr_equity, type: standing, label: {ko: 한국 주식, en: KR Equities}, hints: {asset_hint: [kr_market, kr_corp], topics: [equities]}}
  - {id: us_equity, type: standing, label: {ko: 미국 주식, en: US Equities}, hints: {asset_hint: [equity], topics: [equities]}}
  - {id: crypto, type: standing, label: {ko: 크립토, en: Crypto}, hints: {asset_hint: [crypto], topics: [crypto]}}
  # ── 경제·정책 (development) ──
  - {id: kr_econ, type: development, label: {ko: 한국 경제, en: KR Economy}, hints: {asset_hint: [kr_macro], topics: [inflation, jobs, recession]}}
  - {id: us_econ, type: development, label: {ko: 미국 경제, en: US Economy}, hints: {asset_hint: [global_macro], topics: [inflation, jobs, recession]}}
  - {id: kr_policy, type: development, label: {ko: 한국 정책, en: KR Policy}, hints: {asset_hint: [kr_politics], topics: [regulation, trade]}}
  - {id: us_policy, type: development, label: {ko: 미국 정책, en: US Policy}, hints: {asset_hint: [policy, trump, global_policy], topics: [regulation, trade]}}
  # ── 리스크 (risk) ──
  - {id: risk, type: risk, label: {ko: 지정학·시스템 리스크, en: Risk}, hints: {topics: [geopolitics]}}
  # ── 섹터 (sector, GICS vocab) ──
  - {id: sector_tech, type: sector, label: {ko: 테크, en: Tech}, hints: {topics: [tech], keywords: [반도체, AI칩, semiconductor, chip]}}
  - {id: sector_financials, type: sector, label: {ko: 금융, en: Financials}, hints: {topics: [banking]}}
  - {id: sector_energy, type: sector, label: {ko: 에너지, en: Energy}, hints: {topics: [energy]}}
  - {id: sector_healthcare, type: sector, label: {ko: 헬스케어, en: Healthcare}, hints: {keywords: [제약, 바이오, pharma, biotech]}}
  - {id: sector_industrials, type: sector, label: {ko: 산업재, en: Industrials}, hints: {keywords: [자동차, 조선, 항공, auto, defense]}}
  # ── 워치종목 (watch) ──
  - {id: watch_samsung, type: watch, label: {ko: 삼성전자, en: Samsung}, ticker: "005930", keywords: [삼성전자, Samsung Electronics]}
  - {id: watch_skhynix, type: watch, label: {ko: SK하이닉스, en: SK Hynix}, ticker: "000660", keywords: [SK하이닉스, SK Hynix]}
  - {id: watch_nvidia, type: watch, label: {ko: 엔비디아, en: NVIDIA}, ticker: NVDA, keywords: [엔비디아, NVIDIA]}
  - {id: watch_apple, type: watch, label: {ko: 애플, en: Apple}, ticker: AAPL, keywords: [애플, Apple]}
  - {id: watch_tesla, type: watch, label: {ko: 테슬라, en: Tesla}, ticker: TSLA, keywords: [테슬라, Tesla]}
  - {id: watch_msft, type: watch, label: {ko: 마이크로소프트, en: Microsoft}, ticker: MSFT, keywords: [마이크로소프트, Microsoft]}
  - {id: watch_alphabet, type: watch, label: {ko: 알파벳, en: Alphabet}, ticker: GOOGL, keywords: [알파벳, 구글, Alphabet, Google]}
  - {id: watch_tsmc, type: watch, label: {ko: TSMC, en: TSMC}, ticker: TSM, keywords: [TSMC]}
  - {id: watch_micron, type: watch, label: {ko: 마이크론, en: Micron}, ticker: MU, keywords: [마이크론, Micron]}
  - {id: watch_amazon, type: watch, label: {ko: 아마존, en: Amazon}, ticker: AMZN, keywords: [아마존, Amazon]}
```

- [ ] **Step 4: `topics.py` 로더**

`src/newsstore/enrich/topics.py`:
```python
"""topics.yaml 렌즈 SSOT 로더 + registry. 분류·UI·정렬이 전부 여기서 도출."""
from __future__ import annotations
import functools
import yaml

_TYPES = {"standing", "development", "sector", "watch", "risk"}


@functools.lru_cache(maxsize=4)
def load_topics(path: str = "config/topics.yaml") -> dict:
    t = yaml.safe_load(open(path, encoding="utf-8"))
    bad = [l["id"] for l in t["lenses"] if l["type"] not in _TYPES]
    if bad:                       # FAIL-LOUD: 미지정 type 즉시 폭발
        raise ValueError(f"topics.yaml unknown type for: {bad}")
    return t


def valid_ids(t: dict) -> set[str]:
    return {l["id"] for l in t["lenses"]}


def lens_type(t: dict, lens_id: str) -> str:
    for l in t["lenses"]:
        if l["id"] == lens_id:
            return l["type"]
    raise KeyError(f"unknown lens id: {lens_id}")
```

- [ ] **Step 5: 통과** — `... pytest tests/test_topics.py -v` → PASS

- [ ] **Step 6: Commit** — `git add config/topics.yaml src/newsstore/enrich/topics.py tests/test_topics.py && git commit -m "feat(enrich): topics.yaml lens taxonomy (unified lenses[] + type) + loader"`

---

## Task 2: Stage1 결정론 분류기

**Files:** Create `src/newsstore/enrich/lens_classify.py`, `tests/test_lens_classify.py`

- [ ] **Step 1: 실패 테스트**

`tests/test_lens_classify.py`:
```python
from newsstore.enrich import topics
from newsstore.enrich.lens_classify import classify_stage1

T = topics.load_topics()


def _c(**kw):
    base = dict(asset_hints=[], tickers=[], entities=[], topics=[], language="en", keyword_text="")
    base.update(kw)
    return classify_stage1(T, **base)


def test_asset_hint_is_primary_signal():
    # 태그 비어도 asset_hint만으로 분류(신뢰 prior)
    assert "kr_rates" in _c(asset_hints=["kr_bond"])
    assert "crypto" in _c(asset_hints=["crypto"])


def test_watch_ticker_exact_match():
    assert "watch_samsung" in _c(tickers=["005930"], asset_hints=["kr_market"])
    assert "watch_nvidia" in _c(keyword_text="엔비디아 신제품")


def test_region_disambiguation_equities():
    # equities topic이지만 한국 신호 → kr_equity만(둘 다 X)
    out = _c(topics=["equities"], asset_hints=["kr_market"], language="ko")
    assert "kr_equity" in out and "us_equity" not in out
    out2 = _c(topics=["equities"], asset_hints=["equity"], language="en")
    assert "us_equity" in out2 and "kr_equity" not in out2


def test_max_lenses_cap():
    # 많은 신호 → 상한(MAX_LENSES=4) 준수
    out = _c(asset_hints=["kr_bond", "kr_macro", "crypto", "energy", "commodity", "kr_realestate"])
    assert len(out) <= 4


def test_empty_signals_no_assignment():
    assert _c() == []          # fail-safe: 신호 없음 → 미배정(emergent)
```

- [ ] **Step 2: 실패 확인** — FAIL (ModuleNotFound)

- [ ] **Step 3: 구현**

`src/newsstore/enrich/lens_classify.py`:
```python
"""Stage1 결정론 렌즈 분류 — asset_hint 1차(신뢰), 태그 보조, region 변별, MAX_LENSES 상한.

production 태그가 자주 비므로(클러스터 패스 tag=False) asset_hint가 핵심 prior다."""
from __future__ import annotations

MAX_LENSES = 4
_REGION_PAIRS = [("kr_equity", "us_equity"), ("kr_econ", "us_econ"), ("kr_policy", "us_policy")]
_KR_HINT = {"kr_bond", "kr_fx", "kr_macro", "kr_market", "kr_corp", "kr_realestate",
            "kr_policy", "kr_politics"}
_US_HINT = {"equity", "global_macro", "policy", "global_policy", "trump", "global", "global_market"}


def _match_score(lens: dict, *, asset_hints, tickers, entities, topics, keyword_text) -> int:
    h = lens.get("hints", {})
    score = 0
    score += 2 * len(set(h.get("asset_hint", [])) & set(asset_hints))   # asset_hint 가중(신뢰)
    score += len(set(h.get("entities", [])) & set(entities))
    score += len(set(h.get("topics", [])) & set(topics))
    if lens.get("ticker") and lens["ticker"] in tickers:
        score += 3                                                      # watch ticker 강매칭
    for kw in (h.get("keywords", []) + lens.get("keywords", [])):
        if kw and kw in keyword_text:
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
    kr_sig = bool(set(asset_hints) & _KR_HINT)
    us_sig = bool(set(asset_hints) & _US_HINT)
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
```

- [ ] **Step 4: 통과** — `... pytest tests/test_lens_classify.py -v` → PASS (5 passed)

- [ ] **Step 5: Commit** — `git commit -m "feat(enrich): Stage1 deterministic lens classifier (asset_hint primary, region, MAX_LENSES)"`

---

## Task 3: store — 스토리 lensing 읽기/쓰기

**Files:** Modify `src/newsstore/store/firestore_store.py`, `src/newsstore/contracts/ports.py`; Test `tests/test_firestore_store.py`

- [ ] **Step 1: 실패 테스트** — `tests/test_firestore_store.py` 끝에:
```python
def test_save_and_read_story_lenses(store):
    from datetime import datetime, timezone, timedelta
    now = datetime(2026, 6, 29, tzinfo=timezone.utc)
    store.create_story("s1", title="t", vec=[1.0], member_id="a", entities=[], now=now)
    store.save_story_lenses("s1", ["kr_rates", "risk"])
    rows = store.get_stories_for_lensing(cutoff=now - timedelta(hours=1))
    assert rows and rows[0]["id"] == "s1" and rows[0]["lenses"] == ["kr_rates", "risk"]
```

- [ ] **Step 2: 실패 확인** — FAIL (no attribute)

- [ ] **Step 3: 구현** — `firestore_store.py`에 추가(merge=비파괴):
```python
    def save_story_lenses(self, story_id, lenses: list) -> None:
        self.db.collection("stories").document(story_id).set(
            {"lenses": list(lenses)}, merge=True)

    def get_stories_for_lensing(self, cutoff) -> list[dict]:
        out = []
        for snap in self.db.collection("stories").where("status", "==", "open").stream():
            d = snap.to_dict() or {}
            if d.get("last_seen") and d["last_seen"] >= cutoff:
                out.append({"id": snap.id, "title": d.get("title", ""),
                            "member_ids": d.get("member_ids", []),
                            "lenses": d.get("lenses", [])})
        return out

    def get_story_member_signals(self, member_ids: list) -> dict:
        """멤버 기사 분류 신호를 **배치(get_all)**로 집계(per-member 읽기 금지).
        반환 {asset_hints, languages, tags(flat), keyword_text}."""
        col = self.db.collection(_ITEMS)
        refs = [col.document(i) for i in member_ids]
        ahints, langs, tags, texts = set(), [], [], []
        for s in (self.db.get_all(refs) if member_ids else []):
            d = (s.to_dict() or {})
            for a in str(d.get("asset_hint") or "").split(","):
                if a.strip():
                    ahints.add(a.strip())
            if d.get("language"):
                langs.append(d["language"])
            texts.append(d.get("title", "") + " " + (d.get("body") or "")[:200])
            tags.extend(t for t in (d.get("tags") or []) if isinstance(t, str))
        texts.extend(tags)
        return {"asset_hints": list(ahints), "languages": langs,
                "tags": tags, "keyword_text": " ".join(texts)}
```
`ports.py`의 `Store`에 세 메서드 시그니처 추가(docstring 1줄).

- [ ] **Step 4: 통과 + 회귀** — `... pytest tests/test_firestore_store.py -v` → PASS

- [ ] **Step 5: Commit** — `git commit -m "feat(store): save_story_lenses + get_stories_for_lensing (additive)"`

---

## Task 4: 렌즈 패스 — `run_enrich --mode lenses`

**Files:** Modify `src/newsstore/entrypoints/run_enrich.py`; Create `src/newsstore/enrich/lens_pass.py`, `tests/test_lens_pass.py`

- [ ] **Step 1: 실패 테스트(에뮬레이터)** — `tests/test_lens_pass.py`:
```python
from datetime import datetime, timezone, timedelta
from newsstore.contracts.models import RawItem
from newsstore.enrich.lens_pass import run_lens_pass

NOW = datetime(2026, 6, 29, tzinfo=timezone.utc)


def _item(i, **kw):
    base = dict(id=i, feed_id="f", source="S", url=f"https://e/{i}", title="t",
                fetched_at=NOW, asset_hint="")
    base.update(kw)
    return RawItem(**base)


def test_lens_pass_assigns_from_member_asset_hint(store):
    store.upsert_items([_item("a", asset_hint="kr_bond", language="ko")])
    store.create_story("s1", title="한은 기준금리 동결", vec=[1.0], member_id="a", entities=[], now=NOW)
    n = run_lens_pass(store, now=NOW, cutoff=NOW - timedelta(hours=1))
    rows = {r["id"]: r for r in store.get_stories_for_lensing(cutoff=NOW - timedelta(hours=1))}
    assert "kr_rates" in rows["s1"]["lenses"] and n == 1
```

- [ ] **Step 2: 실패 확인** — FAIL

- [ ] **Step 3: 구현** — `src/newsstore/enrich/lens_pass.py`:
```python
"""렌즈 패스 — 열린 스토리를 멤버 신호로 분류해 stories.lenses[] 채움(Stage1 결정론)."""
from __future__ import annotations
import logging
from . import topics
from .lens_classify import classify_stage1

log = logging.getLogger("newsstore.enrich.lens_pass")


def run_lens_pass(store, *, now, cutoff) -> int:
    t = topics.load_topics()
    rows = store.get_stories_for_lensing(cutoff=cutoff)
    n = 0
    for r in rows:
        sig = store.get_story_member_signals(r.get("member_ids", []))   # 배치 집계(store 계약)
        langs = sig["languages"]
        tags = sig["tags"]                       # flat tags(tickers+entities+topics 혼재) — 교집합이 거름
        lenses = classify_stage1(
            t, asset_hints=sig["asset_hints"], tickers=tags, entities=tags, topics=tags,
            language=("ko" if langs and langs.count("ko") >= len(langs) / 2 else "en"),
            keyword_text=sig["keyword_text"])
        store.save_story_lenses(r["id"], lenses)
        n += 1
    log.info("lens pass: %d stories classified", n)
    return n
```
`run_enrich.py`: `--mode` choices에 `lenses` 추가 + 분기:
```python
            elif args.mode == "lenses":
                from ..enrich.lens_pass import run_lens_pass
                now = datetime.now(timezone.utc)
                totals = {"classified": run_lens_pass(store, now=now, cutoff=now - OPEN_WINDOW)}
```

- [ ] **Step 4: 통과** — `... pytest tests/test_lens_pass.py -v` → PASS

- [ ] **Step 5: 전체 그린** — `MSYS_NO_PATHCONV=1 docker compose run --rm test` → FAIL=0

- [ ] **Step 6: Commit** — `git commit -m "feat(enrich): lens pass (--mode lenses) classifies open stories into lenses[]"`

---

## Task 5: 계약 문서 + Stage1 커버리지 실증

**Files:** Modify `docs/firestore-contract.md`; Create `scripts/measure_lens_coverage.py`

- [ ] **Step 1: firestore-contract `lenses[]` 필드 추가** — `stories` 스키마에 `lenses[]`(string[], newsstore 렌즈 패스가 write, UI read) 한 줄 추가. 빈 배열 폴백 명시(비파괴).

- [ ] **Step 2: 커버리지 측정 스크립트** — `scripts/measure_lens_coverage.py`: 실험 데이터(`scratchpad/stories_full.json` 또는 REST 풀)의 스토리들에 Stage1을 돌려 **렌즈 배정 비율 + 평균 라벨 수 + 미배정 비율**을 출력(spec §5 "$0 실증"). 결과를 보고 asset_hint 매핑 보강 필요성 판단.

- [ ] **Step 3: 측정 실행** — `MSYS_NO_PATHCONV=1 docker compose run --rm test python scripts/measure_lens_coverage.py` → 배정률·분포 로그.

- [ ] **Step 4: Commit** — `git commit -m "docs+script: firestore-contract lenses[] + Stage1 coverage measurement"`

---

## Task 6: 골든셋 멀티라벨 불변식 (TDD)

**Files:** Create `tests/test_lens_golden.py`

- [ ] **Step 1: 골든 불변식 테스트** — fake 신호로 구성한 합성 스토리 세트(Easy/Medium/Hard)에 Stage1을 돌려: ① 같은 자산 신호→같은 렌즈 ② 직교 신호→다른 렌즈 ③ 자명해(전부 미배정·전부 한 렌즈) 격파. micro/macro 정확도가 자명해보다 높음(고정 임계 없이 불변식). 매직넘버 금지.

- [ ] **Step 2: 통과** — `... pytest tests/test_lens_golden.py -v` → PASS

- [ ] **Step 3: 전체 그린 + Commit** — `MSYS_NO_PATHCONV=1 docker compose run --rm test` → FAIL=0; `git commit -m "test(enrich): lens golden multi-label invariants (no magic numbers)"`

---

## 검증 (완료 기준)
- `MSYS_NO_PATHCONV=1 docker compose run --rm test` → **FAIL=0**(topics·classify·store·lens_pass·golden).
- `stories.lenses[]` 채워짐(에뮬레이터 실증) · 드리프트 가드(hint↔taxonomy) GREEN · asset_hint 1차 동작 · MAX_LENSES·region 변별 동작.
- Stage1 커버리지 측정값 확보(asset_hint 매핑 보강 판단 근거).

## 후속 (이 플랜 밖)
- **Stage2 조건부 LLM**(Stage1 미배정·애매분만, 요약 패스 편승) — Stage1 커버리지 측정 후 필요분만.
- 섹터 동적 top-5 *선정*(뉴스 활동량) · 워치 성장임팩트 부각(Phase 3 impact 후) · UI(Phase 4).
- 라이브 배포(`--mode lenses` Scheduler) · pricestore(미래).

<!-- spec-review: passed lenses=3 date=2026-06-29 -->
