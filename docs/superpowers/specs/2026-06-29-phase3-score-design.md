# Phase 3 — Dual Score (risk / impact) — 설계

_작성: 2026-06-29 · 상태: 설계(검토중) · 성격: 분석 레이어 Phase 3. 상위 설계: `docs/analysis-design.md` §7 · 작업 순서: `docs/roadmap.md` · 계약: `docs/firestore-contract.md` · 토대: Phase 1 렌즈(`enrich/topics.py`·`lens_pass.py`)_

## 1. 목표 / 범위
스토리(사건 클러스터)에 **dual score** — `risk`(렌즈/내러티브 정렬, GPR·EPU 계보) + `impact`(스토리·종목 정렬, 이벤트스터디 계보) — 를 **LLM 1콜로 동시 산출**하고 비파괴로 저장한다. **type-aware 게이트**로 비용·잡음을 통제한다(금융자산은 상시 채점, 전개·리스크·emergent는 materiality 게이트).

- **포함**: ① type-aware 게이트(`lenses[]`→`lens_type`로 분기) ② dual score LLM 1콜 + 결정론 validator(범위 0~3·필수키) + fail-soft ③ `stories.{risk, impact, risk_reason, impact_reason, scored_count}` additive·merge·incremental 저장 ④ `run_enrich --mode score` 패스 + store 메서드(`get_stories_for_scoring`/`save_story_score`) ⑤ `firestore-contract.md` 필드 추가.
- **제외(후속 Phase)**: impact 임계 *노출 숨김*·emergent *노출 게이트* 렌더(Phase 4 UI — 저장은 비파괴, UI가 소비) · 렌즈 risk 집계 정렬 렌더(Phase 4) · Now Brief 합성(Phase 4) · 회귀 βₖ 캘리브레이션(후속) · 스포츠 마킹(`classify_kind` `sports` kind — 별도 분류 작업, 본 Phase는 score만).

## 2. 핵심 제약 — 뉴스-온리 + advisory 점수(정직)
- **가격 데이터 없음**($0, 무료 RSS + Gemini). 따라서 risk/impact는 *가격·수익률 측정이 아니라* **뉴스 텍스트에서 LLM이 판정한 advisory 점수**다. 이벤트스터디·GPR은 *계보(개념 정렬)*일 뿐, 본 Phase는 그 정량 측정을 구현하지 않는다.
- **advisory → 하드 드롭 금지**(analysis-design §7): 점수 *값*의 진실성은 결정론 validator로 못 보증한다. 그래서 단일 점수로 스토리를 *삭제·미수집* 하지 않는다 — 저장은 항상(비파괴), 임계 이하 *노출* 숨김은 Phase 4 UI가 결정한다. 본 Phase는 **점수를 매겨 저장**까지.
- **결정론 우선 검증**(domain-llm-runtime): LLM 출력을 **결정론 validator가 먼저** 거른다(범위 0~3·필수키 risk/impact). 형식 적합은 코드로(per-call 런타임 리뷰어 없이 — 저위험·비용↓), 점수 품질은 후속 캘리브레이션(§13)으로. 환각 reason은 advisory(저장하되 비신뢰).
- **비용**: 결제 **$0 유지가 목표**(roadmap §1 — 무료 RSS + Gemini Flash 무료 한도). `$3/일`은 *상한(안전망)*일 뿐 목표 비용이 아니다(analysis-design §2 한도 ≠ roadmap 목표 — grounding 리뷰 반영). flash-lite 1콜/스토리, type-aware 게이트가 콜 수를 줄인다(emergent·전개는 materiality 넘은 것만).

## 3. Dual Score 모델 (analysis-design §7 도출)
| | **Risk** | **Impact** |
|---|---|---|
| 측정 | 악재·불확실성(하방·꼬리) 빈도×강도 | 시장 이동 크기(방향 무관) |
| 정렬축 | 렌즈(내러티브) | 스토리·델타·워치종목 |
| 계보 | GPR·EPU(뉴스 빈도·강도 범주형) | 이벤트스터디·토픽회귀 |
| 구조 | `risk` 0~3 + `risk_reason` 1줄 | `impact` 0~3 + `impact_reason` 1줄 (**단일 필드** — boost 예약 안 함) |

**스케일 의미(0~3) — 🔴 사용자 결정 필요(기본값 제시)**: 점수의 절대 의미는 캘리브레이션 전까지 LLM 자가판정이다. v1 기본 루브릭(프롬프트에 명시):
- **risk**: 0=리스크 무관, 1=경미(국지적 불확실성), 2=주목할 악재·불확실성(하방 가능), 3=심각(시스템·지정학·꼬리 리스크).
- **impact**: 0=시장영향 없음, 1=특정 종목/섹터 국지, 2=시장 일부 유의미 이동, 3=광범위 큰 이동.
- 이 루브릭의 단계 의미·임계는 후속 캘리브레이션(§13)으로 검증. **사용자 확정 필요**(단계 라벨·예시 조정).
- **루브릭 변경 시 재채점(adversarial 리뷰 반영)**: 저장된 점수는 *현 루브릭 기준 raw 정수*다. 루브릭을 바꾸면 옛 점수가 의미상 비교 불가 → **전체 재채점으로 일관성 회복**(운영: `scored_count`를 리셋하면 incremental이 모든 스토리를 다시 채점). `rubric_version` 필드는 **예약 안 함**(YAGNI — 재채점이 싸고, 버전 분기 복잡도 불필요). v1 루브릭은 *provisional 기본값*임을 명시.

**산출 단위(멀티라벨 집계, analysis-design §7)**: risk/impact는 **스토리 단위로 1쌍**. 한 기사가 여러 렌즈에 들어도 채점은 스토리에 1번. **렌즈의 risk = 그 렌즈 소속 (열린) 스토리들의 risk 집계**는 Phase 4 렌더가 도출(본 Phase는 스토리 점수까지, 중복 채점 없음).

## 4. type-aware 게이트 (핵심)
스토리의 `lenses[]`를 `topics.lens_type(id)`로 풀어 **채점 자격**을 분기한다(SSOT=topics.yaml, 별도 type 저장 안 함).

| lens type | 시간성 | 게이트 |
|---|---|---|
| **standing** (금융자산: 채권·FX·유가·귀금속·원자재·부동산·KR/US 주식·크립토) | 상시 | **게이트 없음 — 상시 채점**(새 활동 있으면 재채점) |
| **watch** (워치종목 — 개별 금융자산) | 개별 상시 | **게이트 없음 — 상시 채점**(standing과 동급 금융자산) |
| **development**(경제·정책) / **risk**(지정학) / **sector**(rollup) | 전개·이벤트 | **materiality 게이트** |
| (없음) 순수 **emergent** / topics.yaml에 없는 **unknown id** | event | **materiality 게이트**(보수) |

**구현 확정(consistency 리뷰 반영 — 모호 제거)**: `ALWAYS_SCORE_TYPES = {standing, watch}`. 이 둘만 게이트 면제. **development·risk·sector·emergent(무렌즈)·unknown-id는 전부 materiality 게이트** 적용. sector는 rollup이라 *개별 금융자산이 아님* → 게이트 대상으로 **확정**(섹터-only 스토리는 보통 watch/standing도 함께 달려 통과하므로 손실 미미). unknown-id(topics.yaml에 없는 렌즈)는 KeyError로 안 터뜨리고 **emergent로 강등**(보수 — standing/watch로 승격 금지).

- **materiality 게이트(1차 단순화) — 단일소스 스쿠프와의 관계(adversarial 리뷰 반영)**: roadmap 교훈은 "emergent-only *구조신호*(velocity·노벨티)는 단일소스 스쿠프를 ~60% 놓친다 → **렌즈 멤버십이 그 신호**"다. 본 게이트가 그 교훈을 *어기지 않음*을 명확히:
  - **단일소스 스쿠프가 standing/watch 렌즈에 들어가면 멤버 1건도 즉시 채점**(게이트 면제). 교훈이 말한 "놓치던 스쿠프"가 바로 이 경로로 *잡힌다* — 렌즈 멤버십이 신호다.
  - **렌즈가 전혀 안 붙은 순수 emergent의 단일소스(멤버 1)** 만 보류한다. 이는 *모순이 아니라 의도된 보수적 트레이드오프*다: 렌즈 신호가 없는 1건은 잡음/단발 가능성이 높아 LLM 콜을 아끼고, **후속 멤버(소스확증)가 붙으면 채점**(비파괴 — 데이터는 안 버림). velocity는 함정이라 안 씀.
  - 멤버수 ≥ `MATERIALITY_MIN_MEMBERS`(기본 2)가 소스확증 프록시.
  - "LLM ERL 판정"은 1차에선 **dual-score 콜 자체**가 수행(risk/impact=0이면 사실상 immaterial로 저장). 별도 사전 LLM 게이트 콜은 비용·복잡도라 1차 제외(YAGNI).
- **incremental(비용) — "새 활동"의 정의(adversarial 리뷰 반영)**: "새 활동" = **오직 `count > scored_count`(새 멤버가 붙음)**. 렌즈 재분류·요약 갱신 같은 다른 신호 변화는 트리거 *아님*(standing이 매 런 재채점되는 비용 폭주 차단). 렌즈 패스 `lensed_count`·요약 패스 `summary_count`와 **동일한 per-pass 카운트 컨벤션**(scored_count). 변화 없으면 스킵.
- **게이트 임계 — 🔴 사용자 결정 필요**: `MATERIALITY_MIN_MEMBERS=2`(소스확증 최소), `ALWAYS_SCORE_TYPES={standing, watch}`. 라이브 데이터로 캘리브레이션. (확정 기본값은 위 "구현 확정"; 사용자는 임계 2→1 완화·watch 분리 여부만 후속 조정.)

## 5. 파이프라인
```
스토리(get_stories_for_scoring: open·last_seen>=cutoff·count>scored_count)
  ↓ type-aware 게이트(lenses[]→lens_type) — standing/watch=통과, 그 외=멤버수≥MIN     (LLM 0콜)
  ↓ 입력 구성 — 제목 + 요약/developments(요약 패스 산출 재사용) · 없으면 멤버 제목 폴백 (grounding)
  ↓ dual-score LLM 1콜 — {risk, impact, risk_reason, impact_reason} JSON, flash-lite
  ↓ 결정론 validator — risk/impact ∈ [0,3] 정수(아니면 None=드롭/스킵), reason은 advisory(선택)
출력: stories.{risk, impact, risk_reason, impact_reason, scored_count, scored_at}  (merge·비파괴)
```
- **입력 grounding + 폴백 순서(adversarial·consistency 리뷰 반영)**: `summary` 또는 `developments[].text` 있으면 그것을 1차 입력(이미 전개 단위 distill, 토큰↓). **둘 다 없으면 → `get_story_members()` 제목 폴백. 그것도 비면(멤버 0) → 빈 입력 → `score_story`가 None 반환(스킵, 크래시 금지).** 점수 패스는 요약 패스 *이후* 실행(스케줄 순서).
- **reason 선택성(consistency 리뷰 반영)**: 필수키 = **risk·impact 둘뿐**(0~3 정수). `risk_reason`/`impact_reason`은 **advisory(선택)** — LLM이 빠뜨리거나 비-str이면 **빈 문자열로 강등**(드롭 아님). 즉 risk/impact만 유효하면 reason 결측이어도 점수 저장. reason 길이는 `MAX_REASON` 상한으로 정제.
- **fail-soft**: LLM 장애·빈 결과·validator 실패(risk/impact 무효) → 그 스토리만 스킵(저장 안 함, 다음 런 재시도), 패스 안 죽임. LLMError·예기치 못한 예외 모두 로그(코드 버그는 traceback — FAIL-LOUD).

## 6. Firestore 계약 (additive·비파괴)
`stories`에 추가(merge only, raw·cluster·summary·lenses 필드 보존):
- `risk` (int 0~3) · `impact` (int 0~3) — dual score. 없으면 UI 미표시(폴백).
- `risk_reason` (str) · `impact_reason` (str) — advisory 근거 1줄.
- `scored_count` (int) — 이 멤버수까지 채점함(incremental 가드, `lensed_count`·`summary_count` 패턴).
- `scored_at` (datetime) — 채점 시각.
- **비파괴 by construction(adversarial 리뷰 반영)**: `save_story_score`는 *자기 점수 필드만* 단일 `set(..., merge=True)`로 쓴다 — **read 없음, summary/lenses/cluster 필드와 cross-field batch 없음**. 따라서 부분 실패가 기존 필드를 고아·소실시킬 경로가 *구조적으로 없다*(요약 패스 `save_story_summary`와 동일 패턴). 비파괴 계약 테스트(§9)로 강제.
- 드리프트 가드: 필드명 ↔ UI read 계약. `firestore-contract.md` §stories에 추가.

## 7. Store 계약 (store 추상화 준수 — store.db 직접접근 금지, get_all 배치)
- `get_stories_for_scoring(cutoff) -> list[dict]`: `status=open`·`last_seen>=cutoff`·`count>scored_count`(incremental) 스토리. 반환 `{id, title, count, lenses, summary, developments}`(게이트·입력 구성에 필요한 필드 — 추가 읽기 0). `get_stories_for_lensing` 미러.
- `save_story_score(story_id, *, risk, impact, risk_reason, impact_reason, count, now) -> None`: 점수 필드 + `scored_count=count` + `scored_at=now` merge(비파괴). `save_story_lenses`·`save_story_summary` 미러.
- 멤버 폴백 입력은 기존 `get_story_members`(요약 패스가 쓰는 계약) 재사용 — 신규 멤버 읽기 메서드 안 만듦(SSOT).
- `ports.py` `Store` Protocol에 두 메서드 시그니처 추가.

## 8. 에러처리 / 드리프트 (FAIL-LOUD)
- LLM None 가드/retry/timeout = 기존 `GeminiClient.generate_json` 재사용. dual-score JSON은 **결정론 validator 먼저**(risk/impact 범위·정수) → 실패면 그 스토리 스킵+로그.
- **범위 밖 점수 드롭**: validator가 0~3 정수 아닌 risk/impact를 None으로(환각·형식오류 차단). 매직넘버 금지 — 범위는 `SCORE_MIN`/`SCORE_MAX` 상수.
- **type 드리프트**: `lenses[]`에 topics.yaml에 없는 id가 있으면 게이트가 무시(KeyError 안 터뜨리고 unknown=비금융자산 취급, 보수적). 알 수 없는 id는 게이트에서 standing/watch로 *승격되지 않음*(보수 — emergent 취급).
- **incremental 멱등**: 같은 스토리 두 번 돌려도 `count>scored_count` 가드로 두 번째는 스킵(중복 채점·비용 차단). 렌즈 패스와 동일.

## 9. 테스트 (TDD)
- **validator 단위**(fake/직접): risk/impact 범위 밖·결측·비정수 → None(드롭). 정상 → 0~3 보존, reason 정제(결측→빈문자열, 길이 상한). 매직넘버 금지(`SCORE_MIN`/`SCORE_MAX` 불변식).
- **게이트 단위**: standing/watch 렌즈 스토리 → 멤버 1건도 통과. development/risk/sector/emergent → 멤버 1건 게이트 차단, ≥MIN 통과. 혼합(standing+development, sector+watch) → 통과(금융자산 우선). unknown id(topics.yaml에 없음) → emergent로 강등(보수적 차단, KeyError 안 남).
- **score_story 단위**(fake LLM): 입력 구성 폴백 경로 — ① summary 우선 ② summary/dev 없으면 멤버 제목 폴백(get_story_members 호출) ③ 멤버도 0이면 None(스킵, 크래시 금지) + validator 통과/실패 경로. LLM 장애 → None(fail-soft).
- **run_score_pass 통합(에뮬레이터, store fixture)**: ① standing 스토리 상시 채점(저장 확인) ② 비금융자산 단일멤버 게이트 → 미채점 ③ incremental: 두 번째 런 스킵, 새 멤버 후 재채점 ④ fail-soft(LLM 장애 스토리만 스킵).
- **store 계약(에뮬레이터)**: `save_story_score`→`get_stories_for_scoring` 라운드트립 + 비파괴(merge가 summary/lenses 보존) + incremental 필터.
- **골든 불변식**: 모든 저장 점수가 [0,3] 정수(validator 불변식, 자명해 격파 — 음수·4·"high" 입력이 드롭됨).
- 실행: `MSYS_NO_PATHCONV=1 docker compose run --rm test` → FAIL=0.

## 10. 범위 밖 / 후속 (Phase 표시)
- **Phase 4 UI**: impact 임계 노출 숨김 · emergent 노출 게이트 · 렌즈 risk 집계 정렬 · Now Brief.
- **스포츠 마킹**: `classify_kind`에 `sports` kind(별도 분류 작업).
- **캘리브레이션(§13)**: 회귀 βₖ로 LLM impact 검증·보정(데이터 축적 후). 스케일 의미 확정.
- **LLM ERL 사전 게이트**(materiality를 별도 LLM 콜로) — 1차는 결정론 멤버수 게이트, 필요 실증 후.
- **소스 tier prior**(§7·§9): 1차/분석 소스 impact prior↑ — feeds.yaml tier `meta` 발행 배선 후(현재 미배선, firestore-contract §공유설정). 결정론 prior 보조는 후속.

## 11. 참고 문헌
- Risk: [GPR Index](https://www.policyuncertainty.com/gpr.html) · [Measuring Geopolitical Risk, AER 2022](https://www.matteoiacoviello.com/gpr_files/GPR_PAPER.pdf) · EPU(Baker-Bloom-Davis)
- Impact: [News Topics Drive Stock Movement, arXiv 2510.06864](https://arxiv.org/abs/2510.06864)
- 게이트 교훈: roadmap.md "score 트리거 실험 교훈(2026-06-29)" · 메모리 `hybrid-topic-lens-model`

## 12. 3렌즈 리뷰 반영 (2026-06-29)
독립 리뷰어(grounding·consistency·adversarial) 디스패치 → 반영 요약:
- **[grounding, major]** 비용 $3/일 주장이 roadmap $0 목표와 충돌 → §2 "$0 목표, $3/일은 상한" 정정.
- **[adversarial, critical]** materiality 게이트가 "단일소스 스쿠프" 교훈과 모순처럼 보임 → §4 명확화: 스쿠프는 standing/watch 렌즈로 *잡힘*(면제), 무렌즈 단일소스만 의도적 보수 보류(비파괴, 후속 멤버로 채점). 모순 아님.
- **[consistency, major]** sector 게이트 처리 모호(표는 게이트, 본문은 "확정 필요") → §4 "구현 확정"으로 commit(sector=게이트, ALWAYS_SCORE_TYPES={standing,watch}).
- **[consistency, major]** reason 필수/선택 모호 → §5 명확화: 필수키=risk·impact만, reason은 advisory(결측→빈문자열).
- **[consistency, major]** scored_count vs lensed_count 드리프트 우려 → 실제론 per-pass 카운트 컨벤션(lensed_count·summary_count·scored_count) — §4에 명시.
- **[consistency, critical]** get_stories_for_scoring·save_story_score가 코드에 없음 → *오독*(이 spec이 생성할 신규 메서드, plan Task에서 구현). 결함 아님.
- **[adversarial, major]** merge 원자성/부분쓰기 우려 → §6 "비파괴 by construction"(자기 필드만 단일 merge, cross-field batch 없음) + 계약 테스트.
- **[adversarial, major]** 멤버 0 + 요약 없음 엣지 → §5 폴백 순서에 "빈 입력→None(스킵, 크래시 금지)" 명시 + §9 테스트.
- **[adversarial, major]** 루브릭 하드코딩이 의미 고정 → §3 "변경 시 scored_count 리셋 재채점, rubric_version YAGNI" 명시.
- **[adversarial/consistency, minor]** dual reason YAGNI 의심 → *유지*(task 요구사항이자 risk/impact 차원 분리 — 사용자 명료성). "새 활동" 모호 → §4 "count>scored_count only"로 정의.

decision: **accept** — critical 2건 중 1건 오독, 1건은 §4 문구 정정으로 해소. 설계 폐기 없음, 타깃 수정 반영 완료.

<!-- spec-review: passed lenses=3 date=2026-06-29 -->
