# Phase 1 — 하이브리드 토픽 렌즈 + 멀티라벨 분류 — 설계

_작성: 2026-06-29 · 상태: 설계(검토중) · 성격: 분석 레이어 Phase 1(토대). 상위 설계: `docs/analysis-design.md` · 작업 순서: `docs/roadmap.md` · 계약: `docs/firestore-contract.md`_

## 1. 목표 / 범위
스토리(사건 클러스터)를 **큐레이션 토픽 렌즈에 멀티라벨로 분류**해, 파편화를 구조적으로 막고 다운스트림(델타·score·UI)이 *무엇이 어느 렌즈에 속하나*를 알게 한다. **Phase 1은 렌즈 토대만** — 분류까지. 노출/score/UI는 후속 Phase.

- **포함**: `config/topics.yaml`(렌즈 SSOT) + 멀티라벨 분류 파이프라인(결정론 hint + 조건부 LLM) + `items/stories.lenses[]` 필드 + 골든셋·계약 테스트.
- **제외(후속 Phase)**: 동적 섹터 *노출* top-5 렌더, 워치종목 성장임팩트 *부각* 렌더(둘 다 Phase 4 UI), dual score 게이트(Phase 3), 델타(Phase 2). Phase 1은 *분류 라벨 부여*까지.

## 2. 핵심 제약 — **뉴스-온리(정직)** + pricestore(미래)
우리는 **가격·시장 데이터 피드가 없다**($0, 무료 RSS + Gemini만). 그래서:
- 금융자산 렌즈의 "시황"은 **가격 레벨/델타가 아니라 *뉴스에서 도출한 자산별 진행 상태*** (최신 전개 + 기사가 언급한 주목 변동). WebSocket 호가·캔들 같은 건 범위 밖.
- 섹터 동적 top-5는 **가격 모멘텀이 아니라 *뉴스 활동량*(섹터별 스토리 수 증감)** 으로 선정.
- 워치종목 "성장임팩트 부각"은 가격이 아니라 **score(Phase 3)의 impact** 기반 → Phase 1은 *분류*만, 부각은 후속.
- **standing 렌즈의 정직한 한계(UI 계약)**: "상시 노출"은 *가격 티커처럼 항상 살아있다*는 뜻이 아니라, **해당 자산의 최신 뉴스 상태를 항상 자리(슬롯)로 둔다**는 뜻. 그 자산 뉴스가 없는 기간엔 "최근 전개 없음"으로 *정직하게 비운다*(가짜 실시간 금지). UI는 `published_at` 기준(실시간 아님)임을 표기.
- **pricestore(미래 트랙, 사용자 방향 2026-06-29)**: 별도 가격 저장소로 가격 데이터를 정확히 수집 → standing 렌즈가 *뉴스 시각 + 시장 반응*을 결합. 본 Phase는 뉴스-온리로 가되, 렌즈 구조를 **price 결합이 가능한 형태**(자산별 슬롯)로 둔다(미래 무파괴 확장). 범위 밖.

## 3. 렌즈 모델 — 하이브리드 3-tier × 시간성(type)
렌즈는 `type`으로 **행동(노출·게이트)이 도출**된다(다운스트림 분기의 SSOT).

| type | 렌즈 | 시간성 | 다운스트림 행동(후속) |
|---|---|---|---|
| **standing** | 금융자산(채권·FX·유가·귀금속·원자재·부동산·KR/US 주식·크립토) | 상시 | 게이트 없음, 항상 노출(뉴스 시황 readout) |
| **development** | 경제·정책(KR/US) | 전개 누적 | materiality 게이트, 전개 타임라인 |
| **sector** | GICS 섹터(동적 top-5) | 준상시 rollup | 스토리·종목을 섹터로 집계 |
| **watch** | 워치종목(≤10) | 개별 상시 | impact 상위 동적 부각(Phase 3) |
| **risk** | 지정학·시스템 리스크 | emergent | 동적 컨테이너, impact 노출 |
| (없음) | 순수 emergent(1·2 미해당) | event | impact 임계 노출(Tier3) |

**id→type 해석(계약)**: 스토리의 `lenses[]`엔 모든 블록(macro 렌즈·sector·watch)의 id가 섞여 들어간다. **type은 `topics.yaml`에서 id로 역참조**: macro 렌즈는 자기 `type` 필드, `sectors.vocab`의 id는 `sector`, `watch[].id`는 `watch`로 도출. 다운스트림은 `lens_type(id)` 헬퍼로 분기(별도 type 필드를 stories에 중복 저장 안 함 — SSOT는 topics.yaml).

**멀티라벨 + 변별 가드**: 한 스토리가 여러 렌즈 동시 소속(SK하이닉스 메모리 뉴스 → `kr_equity`·`sector_tech`·`watch_skhynix`). 단 **무분별 폭발 방지**:
- **region 변별**: `kr_equity`/`us_equity`처럼 지역 쌍은 둘 다 자동부여 금지 — 기사 `language`·`source`·`asset_hint`(kr_*/us_*)로 한쪽 결정, 모호하면 LLM.
- **상한**: 스토리당 `MAX_LENSES`(기본 4) — 초과 시 confidence 상위만(시황 옴니버스가 10개 렌즈 먹는 것 차단).

## 4. `config/topics.yaml` — 베이스 택소노미 (SSOT)
스키마: 렌즈마다 `id·label{ko,en}·type·hints`(결정론 prior) + 버전. **`taxonomy.yaml`(어휘)을 *참조*만**(중복정의 금지).

```yaml
version: 2026-06-29           # 드리프트 추적(변경 시 갱신 + changelog)
lenses:
  # ── A. 금융자산 (standing) — 10 ──
  - { id: kr_rates,  type: standing, label: {ko: 한국 금리·채권, en: KR Rates},
      hints: {asset_hint: [kr_bond, kr_macro], entities: [한국은행], topics: [rates, bonds, central_bank]} }
  - { id: us_rates,  type: standing, label: {ko: 미국 금리·채권, en: US Rates},
      hints: {entities: [Fed, Treasury], topics: [rates, bonds, central_bank]} }
  - { id: fx,        type: standing, label: {ko: 환율(원달러 중심), en: FX}, hints: {asset_hint: [fx, kr_fx], topics: [fx]} }
  - { id: oil_energy, type: standing, label: {ko: 유가·에너지, en: Oil/Energy}, hints: {asset_hint: [energy], entities: [OPEC], topics: [energy]} }
  - { id: precious_metals, type: standing, label: {ko: 귀금속, en: Precious Metals}, hints: {keywords: [금값, 은값, gold, silver], topics: [commodities]} }
  - { id: commodities, type: standing, label: {ko: 기타 원자재, en: Commodities}, hints: {asset_hint: [commodity], topics: [commodities]} }
  - { id: kr_realestate, type: standing, label: {ko: 한국 부동산, en: KR Real Estate}, hints: {asset_hint: [kr_realestate], topics: [housing]} }
  - { id: kr_equity, type: standing, label: {ko: 한국 주식, en: KR Equities}, hints: {asset_hint: [kr_market, kr_corp], topics: [equities]} }
  - { id: us_equity, type: standing, label: {ko: 미국 주식, en: US Equities}, hints: {asset_hint: [equity, us_stock], topics: [equities]} }
  - { id: crypto,    type: standing, label: {ko: 크립토, en: Crypto}, hints: {asset_hint: [crypto], topics: [crypto]} }
  # ── B. 경제·정책 (development) — 4 ──
  - { id: kr_econ,   type: development, label: {ko: 한국 경제, en: KR Economy}, hints: {asset_hint: [kr_macro], topics: [inflation, jobs, recession]} }
  - { id: us_econ,   type: development, label: {ko: 미국 경제, en: US Economy}, hints: {asset_hint: [global_macro], topics: [inflation, jobs, recession]} }
  - { id: kr_policy, type: development, label: {ko: 한국 정책, en: KR Policy}, hints: {asset_hint: [kr_policy, kr_politics], topics: [regulation, trade]} }
  - { id: us_policy, type: development, label: {ko: 미국 정책, en: US Policy}, hints: {asset_hint: [policy, trump, global_policy], topics: [regulation, trade]} }
  # ── E. 리스크 (risk) — 1 ──
  - { id: risk,      type: risk, label: {ko: 지정학·시스템 리스크, en: Risk}, hints: {topics: [geopolitics]} }
# ── C. 섹터 (sector) — GICS vocab, 동적 top-5 노출(후속) ──
sectors:
  vocab: [tech, financials, energy, materials, industrials, healthcare,
          consumer_disc, consumer_staples, comm_services, utilities, real_estate]   # GICS 11
  surface_top_n: 5            # 활성 상위 N 노출(후속). 활성 = 뉴스 활동량(가격 아님)
# ── D. 워치종목 (watch) — ≤10, 고정+성장부각(후속) ──
watch:
  - { id: watch_samsung, ticker: "005930", keywords: [삼성전자, Samsung Electronics] }
  - { id: watch_skhynix, ticker: "000660", keywords: [SK하이닉스, SK Hynix] }
  - { id: watch_nvidia,  ticker: NVDA, keywords: [엔비디아, NVIDIA] }
  - { id: watch_apple,   ticker: AAPL, keywords: [애플, Apple] }
  - { id: watch_tesla,   ticker: TSLA, keywords: [테슬라, Tesla] }
  - { id: watch_msft,    ticker: MSFT, keywords: [마이크로소프트, Microsoft] }
  - { id: watch_alphabet, ticker: GOOGL, keywords: [알파벳, 구글, Alphabet, Google] }
  - { id: watch_tsmc,    ticker: TSM, keywords: [TSMC, 대만 반도체] }
  - { id: watch_micron,  ticker: MU, keywords: [마이크론, Micron] }
  - { id: watch_amazon,  ticker: AMZN, keywords: [아마존, Amazon] }
```
- **GICS 섹터 채택**(시장지향·글로벌 표준 — ICB는 생산지향이라 뉴스 의미와 덜 맞음, 스카웃1). KR·US 동일 vocab, *노출 top-5는 시장 무관 합산*(v1 단순화; 시장별 분리는 후속).
- 베이스 합계: standing 10 + development 4 + risk 1 = **15 macro 렌즈** + sector vocab(11, top-5 노출) + watch 10. 섹터 ≤5·종목 ≤10 규칙 준수.

## 5. 분류 파이프라인 — **LLM 1차 분류 + asset_hint 무료 prior** (결정 2026-06-29)
측정상 결정론 Stage1만으론 **28% 커버리지**(키워드는 패러프레이즈·맥락을 못 잡음). 비용은 한도 내(**전 스토리 LLM ~$0.3/일, flash-lite**)라 **LLM을 1차 분류기**로 둔다(사용자 결정 — "중요한 힌트 놓침" 방지).
```
스토리(멤버 집계: asset_hint[항상 존재], language, 제목/요약 텍스트, 태그[있으면])
  ↓ 무료 prior — asset_hint 결정론 매칭 → 후보 렌즈 + region 변별(kr/us)         (LLM 0콜)
  ↓ LLM 1차 분류 — 프롬프트(렌즈 id+정의[prefix 캐시] + 스토리 제목/요약 + asset_hint 후보)
        → 멀티라벨 lens id 배열(JSON). flash-lite, 스토리 배치로 콜수↓.
  ↓ 결정론 validator(FAIL-LOUD) — id ∈ topics.yaml만, MAX_LENSES 상한, 중복 제거
출력: stories.lenses[]
```
- **무료 prior = asset_hint**(항상 존재)로 후보를 좁혀 LLM 프롬프트 힌트로 주고 토큰↓. **LLM이 의미로 최종 결정** → 키워드가 놓치는 표현·맥락 포착.
- **결정론 우선 검증(domain-llm-runtime)**: LLM 출력을 **결정론 validator**가 먼저 거른다 — 렌즈 id가 `topics.yaml`에 없으면 드롭(환각 차단), MAX_LENSES 초과 잘림. *형식 적합은 코드로*(리뷰어 콜 없이 비용↓), *의미 품질은 골든셋*(§8)으로 측정. 분류는 저위험이라 per-call 런타임 리뷰어는 안 씀(YAGNI·비용).
- **fail-soft**: LLM 장애·키 없음 → asset_hint prior 결과로 폴백(신호 보존, 패스 안 죽음).
- **비기능(advisor)**: `GeminiClient.generate_json`의 retry/None가드/timeout/structured error 재사용. flash-lite + 배치로 $0 기조($3/일 한도 내 ~$0.3/일).

## 6. Firestore 계약 (additive·비파괴)
- `stories.lenses[]` (string[]) — 확정 렌즈 id. `items.lenses[]`는 선택(스토리 집계가 1차). UI가 렌즈 필터·정렬에 읽음.
- 레거시 스토리: `lenses` 없으면 빈 배열로 폴백(UI 안 깨짐). `firestore-contract.md`에 필드 추가.
- 드리프트 가드: `topics.yaml version` ↔ 분류 결과 ↔ UI 필터 어긋남을 계약 테스트로 폭발(생성 설정 원칙).

## 7. 에러처리 / 드리프트 (FAIL-LOUD)
- LLM None 가드/retry는 기존 `llm` 래퍼. 멀티라벨 JSON은 결정론 validator(렌즈 id ∈ topics.yaml, 범위) 먼저 → 실패 재시도 → critical 스킵+로그(해당 스토리만 보류).
- **vocab 드리프트**: 렌즈 id가 `topics.yaml`에 없으면 분류 출력에서 폭발(조용히 무시 금지). `version`+changelog로 변경 추적.
- hint가 `taxonomy.yaml`/`asset_hint` 어휘에 없으면 빌드/테스트가 터짐(SSOT 참조 무결성).

## 8. 테스트 (TDD)
- **택소노미 무결성**: topics.yaml의 모든 hint(asset_hint/topics/entities)가 실제 어휘(`taxonomy.yaml`·`feeds.yaml`)에 존재 — 드리프트 가드.
- **분류 단위**: 결정론 Stage1(직접매칭→확정 렌즈), 멀티라벨(한 스토리 다중 렌즈), watch ticker 정확매칭, 빈 태그→미배정(fail-safe). fake LLM로 Stage2.
- **골든셋 멀티라벨**: 실데이터 스토리 ~50건에 정답 렌즈 라벨(Easy/Medium/Hard 계층) → micro/macro F1 측정. **매직넘버 금지 — 불변식으로 검증**: 분류기 F1이 두 자명해를 모두 이긴다 — ① 전부 미배정(recall 0) ② 가장 흔한 렌즈만 항상(낮은 macro F1). 둘 다보다 micro·macro F1이 높아야 통과(고정 임계 박지 않음). + **per-story 라벨 수 분포** 점검(평균·max — 폭발 가드 MAX_LENSES 준수 확인). 실 Gemini eval은 키 있을 때만(CI는 결정론 불변식 + Stage1 단위).
- 실행: `MSYS_NO_PATHCONV=1 docker compose run --rm test`.

## 9. 범위 밖 / 후속 (Phase 표시)
- **Phase 1.x(선택)**: 섹터 동적 top-5 *선정*(뉴스 활동량 랭킹 — 가격 아님). 노출은 Phase 4.
- **Phase 2**: 델타(2-타임스탬프·milestone).
- **Phase 3**: dual score(risk/impact) + type-aware 게이트(standing=상시 / development·risk·emergent=게이트, score-트리거 실험 findings 적용) + 워치 성장임팩트 부각.
- **Phase 4**: UI(렌즈별 standing readout vs development timeline, Now Brief).
- **pricestore(미래 트랙)**: 별도 가격 저장소 → standing 렌즈에 가격 결합(뉴스 시각 + 시장 반응). 렌즈를 자산별 슬롯 구조로 둬 무파괴 확장(§2).
- 시장별 섹터 top-5 분리 · 임베딩 Stage3(골든셋으로 효과 실증 후) · `items.lenses[]` 상시화.

## 10. 참고 문헌
- 섹터: [GICS Methodology(MSCI)](https://www.msci.com/our-solutions/indexes/gics) · [Fidelity: 섹터 분류 한계](https://www.fidelity.com/learning-center/trading-investing/markets-sectors/limitations-sector-classification-systems) · [섹터 로테이션/모멘텀](https://trendspider.com/blog/sector-rotation-how-to-track-where-the-money-is-moving/)
- 멀티라벨 분류: [Cost-Aware Model Selection(2602.06370)](https://arxiv.org/html/2602.06370) · [PoliPrompt(2409.01466)](https://arxiv.org/pdf/2409.01466) · [Controlled Vocabularies 드리프트(Talisman)](https://jessicatalisman.substack.com/p/controlled-vocabularies-part-ii) · [Zero-shot 금융 LLM(2305.16633)](https://arxiv.org/pdf/2305.16633)
- 상시/이벤트 표현: [Event-Driven Architecture in Finance(Confluent)](https://www.confluent.io/blog/event-driven-architecture-powers-finance-and-banking/) · [Market Wrap(Goldman Weekly)](https://am.gs.com/en-be/advisors/insights/article/market-monitor-weekly)

<!-- spec-review: passed lenses=3 date=2026-06-29 -->
