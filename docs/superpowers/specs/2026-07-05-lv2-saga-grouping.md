# Spec — lv2 사가 그룹핑 (리포트-타임, 표시 전용·비파괴)

작성: 2026-07-05 · 근거 = `scripts/saga_split_audit.py` 라이브 측정 + 고코사인 쌍 근본 조사.
구간 소유권 = `src/newsstore/enrich/report.py`(계산) + `web/index.html`(렌더) + `config/models.yaml` + 관련 테스트.

## 왜 이 설계인가 (측정·조사 결론)
라이브 측정: 같은 사가가 갈린 후보 478쌍(sector_tech·oil_energy·us_rates 등). 고코사인(0.80+) 쌍을 열어보니:
- "호르무즈 통제" ↔ "유가 과잉"(cos 0.94)은 **같은 이란/유가 사가의 다른 각도** — lv1(클러스터)에서 강제 병합하면 [[solved_problems]]의 **치명적 과병합** 재현.
- "FOMC 주목 증시"(3기사) ↔ "FOMC 방향성"(2기사)는 언더-머지지만, 이것도 lv1 강제 병합은 위험.
→ **처방: lv1(클러스터) 불변. lv2에서 리포트-타임에 관련 스토리를 '사가'로 묶어 사람에게만 표시.**
lv2는 **표시 전용·비파괴**(클러스터·스토리 문서 불변)라, 과병합해도 데이터 손상이 아니라 화면 이슈(가역) — 리뷰가 경고한 위험이 lv1 재캘보다 훨씬 작다.

## 배경/맥락 (서브에이전트 주입)
- 코드 원칙·gotchas: `docs/coding-principles.md`, `docs/solved_problems.md`(과병합=치명적; 매직넘버=불변식; datetime 직렬화; mock↔실 None `x or []`). Docker 전용 테스트(`MSYS_NO_PATHCONV=1 docker compose run --rm test pytest -q`), 로컬 python 없음.
- 이미 배포(불변): 리포트=자산only, divergence 배지·conviction, 기사출처 접이식·사이드바(B). report.py에 `run_report_pass`(price_by_lens·context_lens_ids), `select_top_k`. 스토리 문서에 `centroid_sum`(768)·`entities`·`developments`·`last_seen`.
- 측정 스크립트가 후보 축소(개체+시간+코사인)·768 fail-loud·centroid_sum 재사용 로직을 이미 구현 — **재사용/이식**(scripts/saga_split_audit.py).
- 모델 SSOT: models.yaml→model_for. 신규 usage는 **①models.yaml ②model_config USAGES frozenset ③콜사이트 셋 다** 갱신(하나만 하면 기동 크래시).

## 📜 스키마 계약
`reports/{lens}` 문서에 **추가**(기존 divergence·conviction·sections 등 불변):
```
sagas?: [ { title: string, story_ids: [string], arc: string } ]   # 없으면 필드 생략(그룹 없음)
```
`story_ids`는 이 리포트가 인용/포함한 스토리만. `arc`=시간순 한 줄("호르무즈 통제→종전→유가 과잉").

## 작업 (TDD)

### 1. 백엔드 — 리포트-타임 사가 그룹핑 (report.py, 비파괴)
- **범위 = 이 리포트의 스토리만**(측정의 전역 478쌍이 아니라 렌즈 top-K ~10~15개 — 후보 공간 작음=싸고 안전).
- **후보 축소(결정론)**: 스토리 쌍 중 (지배 개체 공유 entities) ∧ (시간 근접 last_seen/developments) ∧ (**코사인 ≥ 0.80** = hi 임계, centroid_sum 재사용·`len==768` fail-loud). **0.80 미만은 LLM에 아예 안 보냄**(먼 쌍 과병합 원천 차단).
- **LLM 확인(보수적, 1콜)**: 고코사인 후보 그룹만 LLM에 주고 "명백히 같은 사가(한 사건의 연속 국면)인 것만 묶어라. 애매하면 DIFFERENT. arc는 시간순 한 줄." 기본=안 묶음.
- **검증(결정론)**: story_ids는 리포트 입력에 실재(환각 드롭), 단일 스토리 그룹은 사가 아님(드롭), 한 스토리가 두 사가에 중복 금지.
- **저장**: `sagas` 필드. 실패(콜/검증)=필드 생략(fail-soft, 리포트 자체 정상).
- **모델**: 신규 usage `report_saga`=3.5-flash → models.yaml + USAGES + 콜사이트 셋 다.
- 테스트: 후보 축소(개체·시간·코사인 임계·768 단언), LLM 주입 fake로 그룹 검증(환각·단일·중복 드롭), 실패 시 필드 생략. **임계·개수는 불변식/경계앵커로**(매직넘버 금지).

### 2. 프론트 — 사가 표시 (web/index.html)
- `sagas` 있으면 리포트에 **"관련 사가" 블록**: title + arc(시간순 한 줄) + 묶인 스토리로의 링크/앵커. 렌즈 섹션 위 또는 해당 스토리들 근처.
- 없으면 조용히 생략(graceful, 옛 문서). 순수 로직(그룹 매칭)은 REPORT-LOGIC 마커 안, 렌더는 밖.
- 기존 기사출처 접이식·divergence·conviction과 시각 충돌 없게. 사가는 "이 스토리들이 한 사건"임을 얇게 표시(카드 복원 X).

## 통합/배포 (오케스트레이터가 머지 후)
- 전체 pytest + node 웹테스트 GREEN. processor 재빌드→report 실행(sagas 라이브)→Hosting 배포→Playwright(이란/유가·FOMC 쌍이 사가로 묶이나) 검증.

## 범위 밖
- 클러스터링(lv1) 코드/데이터 변경. 임베딩 재생성. 전역 사가(리포트 밖). 클러스터 재캘(측정이 lv2로 처방).

## 리스크/방어
- 과병합: 후보를 코사인 0.80+ ∧ 개체공유로 제한(먼 쌍 차단) + LLM 보수(기본 안 묶음) + **표시 전용이라 최악=화면 이슈(가역)**.
- 비결정론(LLM 그룹)은 결정론 테스트가 후보축소·검증만 커버 — LLM 판정 품질은 표시 전용이라 리스크 수용 가능(라이브 스팟체크로 확인).
- model_for 3곳 갱신 누락 시 기동 크래시 — 셋 다 반드시.

<!-- 3렌즈 리뷰: adversarial critical 2(arc 근거검증 0·0.80 미캘 게이트), YAGNI(순이득 미측정), consistency(Spec A 게이트와 상충). 설계 정당성 자체에 의문 → 사용자 판단으로 escalate. -->
<!-- spec-review: escalated -->
<!-- 권고: 지금 사가 lv2 구현하지 말 것. 아래 오케스트레이터 통보 참조. -->
<!-- spec-review: escalated -->

- **YAGNI (실이득 미측정)**: divergence·conviction·스토리 링크가 이미 있음. 사가 순증 이득은 미측정, 비용(리포트×렌즈 LLM콜)만 확정. audit의 prescribe 게이트가 오히려 cluster_recal/불필요를 낼 수도 있는데 스펙이 실제 판정값을 인용 안 함.

## 결론 — 사가 lv2, 지금 짓지 말자 (내 판단도 동일)

리뷰어와 audit이 한 방향입니다: **사가는 지금 가장 정당성이 약한 항목입니다.** 그래서 escalate하고, 제 권고는 **드롭**입니다.

## 지금까지 한 것 — before/after + "진짜 필요했나" 객관 평가

리포트에 쌓은 것을 정직하게 등급 매깁니다:

| 항목 | before → after | 진짜 필요? | 근거 |
|---|---|---|---|
| 리포트=자산만 + fold-in | 전 렌즈 나열 → 자산 6그룹, 비자산 뉴스는 녹임 | ✅ 필수 | 사용자 직접 방향 |
| 시간적 인과(최신 우선) | "A후B후C 나열" → "B로 C(현재), A는 무효화" | ✅ 필수 | FX 1550→1520 라이브 검증 |
| 가격 교차검증 | 뉴스만(지연) → 가격 앵커로 현재상태 보정 | ✅ 필수 | "모델 동질성 극복"의 실지렛대 |
| 리뷰어 입력 수정(#1) | 정당한 극을 날조로 오탐 → 10/10 통과 | ✅ 필수 | 실제 오탐 제거 |
| UI 재구성(기사출처·사이드바·렌즈라벨) | 스토리카드 자리낭비 → 밀도·네비 | ✅ 필요 | 사용자 요청 |
| **divergence 배지** | 없음 → over_fear 재료칩 | 🟡 한계적 | lean=개수 프록시 약함(리뷰 지적). **이미 배포·fail-soft라 유지는 하되 더 투자 X** |
| **conviction 등급** | 없음 → high/med/low | 🟡 한계적 | 신뢰도 지표(유용하나 소비 동작 약함). 유지·투자 X |
| **사가 lv2** | 갈린 스토리 → LLM이 묶음 | ❌ **하지 말자** | 리뷰 만장일치 회의·arc 근거0·이득 미측정 |

**정직한 자기비판**: 코어(위 5개)는 견고하고 필요했습니다. 그런데 그 위에 divergence·conviction·사가를 얹으며 **점점 정당성이 약해졌습니다** — 전형적 gold-plating 신호입니다. divergence·conviction은 이미 배포됐고 무해(배지·fail-soft)라 그냥 두되, **사가는 짓기 전에 멈추는 게 맞습니다.**

## 왜 사가가 특히 문제인가 (리뷰 핵심)
1. **arc = 검증 0인 LLM 인과 서사**: "호르무즈 통제→유가 과잉"은 cos 0.94지만 **방향이 반대인 서사**(공급위협 vs 공급과잉). LLM이 묶어 arc를 지어내면 **틀린 인과를 권위있게 표시** — "표시 전용이라 안전"은 데이터 리스크만 낮추지, 사용자가 믿는 틀린 서사는 못 막습니다.
2. **0.80 게이트가 미캘 매직넘버**: audit 스크립트 스스로 "centroid-to-centroid는 임계보다 체계적으로 낮음, 방향 지표일 뿐"이라 경고 — 그걸 안전 게이트로 승격한 게 근거 없음.
3. **audit이 오히려 처방을 안 준 것**: 제가 "llm_saga"라 했지만, 게이트는 cluster_recal/불필요도 낼 수 있고 실제 median(0.477) vs 임계 수치가 애매합니다. 즉 **측정이 "사가 하라"를 확정해주지 않았는데** 제가 밀어붙였습니다.

## 대안 (사가 대신)
관련 스토리를 **사람이** 잇는 건 이미 됩니다 — 사이드바 네비 + 렌즈 그룹 + 기사출처. 굳이 LLM이 인과 arc를 지어내지 않아도 사용자가 문맥을 봅니다. **사가는 이득이 측정되면 그때.**

**결정 요청**: 사가 lv2 **드롭**(제 권고)할까요, 아니면 위 리스크를 감수하고 갈까요? 그리고 이참에 divergence·conviction도 **되돌릴지**(gold-plating이라 보시면) — 아니면 배포된 채 두고 다음 진짜 필요한 것(가격정합 v2·종목테이블·비대칭 등)으로 넘어갈지 말씀 주세요.



<!-- spec-review: escalated -->
