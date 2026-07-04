# 시장 센티먼트 = 프레임 근사 — 설계 (RAS 코어, 린 v1)

성격: 프레임 패스의 준거 재정의. **프레임 = 시장 집단심리의 근사**(사용자 2026-07-04). 토대: 12방법론×5심사 연구 + 3안 라이브 시뮬레이션(승자 **안 B: 행동+분산 코어**, 발주자 42·회의론자 41). **3렌즈 spec 리뷰(2026-07-04) 반영해 "빼기"로 축소** — critical 4건이 모두 "4접목 동시투입=최소 아님, interconnectivity/attention_risk 결정론축 저-N 실명·순환"을 지적 → **v1은 RAS+구조화출력만**, 나머지는 v2로 이연. 연구: `scratchpad/senti_agg.md`.

## 1. 목표 / 본질
프레임 극(아킬레스건/기대)을 만드는 LLM 판단의 **준거를 톤에서 '비용을 치른 행동'으로 옮긴다**. 핵심 질문: *"지금 터진다면 사람들이 가장 두려워할 것"* — 브로커 목표가 상향(말)이 아니라, 메타의 잉여 컴퓨팅 매도·capex 감축 같은 **비가역 행동**(RAS)에서 아킬레스건을 뽑는다. "데이터센터 철회"는 정의상 톤이 아니라 행동 → 이 준거 이동이 직격.

**비-목표(v1)**: 판정 안 함(매수/매도 콜 없음). 가격 데이터 없음. 별도 센티먼트 잡·컬렉션·스케줄러 신설 없음. 시계열 지표 없음. IDI·interconnectivity·attention_risk·L-EPU 외부앵커는 v2(§7).

## 2. 분석 준거 — RAS (Revealed-Action)만
frame_gen 프롬프트가 극을 재심할 때 **행동을 톤 위에 가중**한다:
- **words_deeds_divergence**: 서술 톤(예: 증권가 '장기 우상향')과 developments에 담긴 **실제 행동**(메타 capex 감축·잉여 컴퓨팅 매도, 정점 증자, 감원)의 부호가 어긋나는 곳을 아킬레스건으로. 톤↑·행동↓ 상충이 숨은 공포의 시그니처.
- 근거는 **developments 원문의 행동 사실** — 스토리의 risk/frame 점수(LLM 산출)가 아니라 코퍼스 사실을 준거로 삼아 순환을 완화. *정직한 한계*: 극 생성은 여전히 단일 3.5-flash 레그(frame_gen). 완전 비순환 아님 — 외부앵커(L-EPU)는 v2에서 추가.
- **저-N 강점**: RAS는 72h 스토리 원문(developments)을 읽으므로 갓 터진 저-N 대형신호(데이터센터 철회)도 잡는다. (이것이 결정론 축을 v1에서 뺀 이유 중 하나 — 결정론 축은 저-N에서 실명. 리뷰 반영.)

## 3. 프레임 출력 형식 (구조화 — 아키타입 접합·근거 추적)
기존 극 `{id, text}`에 **최소 additive 2필드**만:
```
{ id, axis: risks|premiums|watchpoints, text,   # 기존(호환)
  achilles_kind: "words_deeds" | "structural" | null,   # v1은 이 2값만(나머지 kind는 v2)
  evidence_dev_ids: [story_id...] }              # 근거 development/story — 환각 가드
```
- `words_deeds` = RAS 행동-톤 괴리로 잡힌 극. `structural` = 근거 이벤트 없이 구조적으로 유지되는 이월 극. `null` = 기존/미분류.
- **하위호환**: 소비자(web frameChipsHtml, report `_frame_pole_ids`)는 `id`·`text`만 읽음 — 신규 필드 무시(리뷰 grounding 확인). firestore-contract에 additive 등재.
- 다음 단계(아키타입: 가상 투자자에 프레임을 심리로 배선)의 파싱 입력.

## 4. 파이프라인 (기존 frame 패스 강화 — 신규 콜 0)
`run_enrich --mode report`의 `frames.run_frame_pass`만 강화(별도 패스·별도 계산주체 없음 — 리뷰 순서모순 지적 반영: **모든 계산은 frames 안에서**):
```
렌즈별(기존 루프):
  입력 = 어제 프레임 + 렌즈의 72h 스토리(기존, developments 포함)
   ↓ frame_gen 프롬프트(3.5-flash, 기존 콜) — RAS 준거로 극 재심, 구조화 출력(§3)
   ↓ validate_frame(raw, input_story_ids) — 구조화 검증 + evidence 실재(신규/수정 극만)
   ↓ diff-grounding 리뷰(기존 콜)
저장: frames/{lens_id} (구조화 극; additive)
```
- **콜 수 불변**: 렌즈당 frame_gen 1 (+diff 있을 때 review 1) — 기존과 동일. #45 리포트 타임아웃에 **콜 추가 없음**. *단, 리뷰 정직 반영*: 구조화 출력으로 **출력 토큰·지연이 다소 증가 가능** → build_frame_prompt는 기존 '수 채우지 말고 강도로' 억제를 유지하고 지시를 최소(RAS 1축)로 얹어 과부하 회피. 지연 증가 시 report 타임아웃 여유(1800s, #45)로 흡수.

## 5. 검증 레이어 (domain-llm-runtime)
- **결정론 먼저**: 극 스키마·achilles_kind enum·text 길이 상한. **evidence_dev_ids 실재**: 신규/수정 극의 evidence가 입력 스토리 id에 존재해야(환각 드롭). **이월 구조적 극(achilles_kind=structural)은 evidence 공란 허용**(드롭 예외 — 리뷰 반영: '근거 없어도 구조적 유효 시 유지'와 충돌 회피). → `validate_frame(raw, *, input_story_ids)` 시그니처 확장 필요(현재 `validate_frame(raw)`, 리뷰 consistency 지적).
- **diff-grounding LLM 리뷰**(기존): 신규/수정 극만. 기각 시 어제 판 유지(fail-soft).
- **정직 한계**: LLM 단일 레그(frame_gen)가 극 생성. 준거를 코퍼스 행동 사실로 옮겨 순환을 줄이나 제거는 못 함. 외부 비가격 앵커(L-EPU)는 v2.

## 6. 데이터 모델 (additive·비파괴)
- `frames/{lens_id}` 극에 `achilles_kind`·`evidence_dev_ids` 추가. **validate_frame이 현재 id/text만 보존(재구성 시 여분 필드 드롭)** → 화이트리스트에 2필드 추가 필요(리뷰 grounding 지적 — 안 하면 저장 전 소실). firestore-contract frames 라인 갱신.
- 신규 컬렉션 없음. **가역성 정직 분리**: 스키마 additive는 가역, 그러나 매일 이월되는 극 **내용 계보는 준-비가역**(준거 변경 후 persist된 극은 코드 롤백해도 안 복원). 롤백 대비 준거 변경 기준일을 운영 메모(project-status)에 기록.

## 7. 단계화 (리뷰 반영 — v1 최소화)
- **v1 (이 스펙)**: frame_gen RAS 준거 + 구조화출력 2필드 + validate_frame evidence 검증. **신규 콜 0, 단일 가설(RAS)** — 품질 변화 귀인 가능.
- **v2 (후속, 각각 독립 도입해 귀인 확보)**: ① 결정론 attention_risk_divergence — **저-N 실명·count 신디케이션 편향을 소스다양성으로 보정**한 뒤 로깅-관찰로 먼저(자동 라벨 금지). ② interconnectivity — **역할(축 배치) 기반이라 결정론 아님을 인정**하고 전-렌즈 사전수집 스텝 신설 + 대형엔티티 인기도 컷오프. ③ L-EPU 외부앵커 — **취득경로(FRED USEPUINDXD 무료 일별, collect 잡 편승)·저장(meta 재사용) 명세** + fail-loud 자동가드(캘리브레이션 후). ④ IDI worst_plausible_frame + fear_gap(수치 소비 금지). ⑤ sentiment_series 시계열.
- **v3**: 투자자 아키타입(가상 포트폴리오+심리 배선) — 프레임 입력.

## 8. 테스트 (TDD)
- validate_frame 확장(py): 구조화 극 스키마·enum·additive 하위호환(기존 text-only 극 통과)·evidence 실재(신규 극 환각 dev_id 드롭)·structural 극 evidence 공란 허용.
- 프롬프트 골든(fake LLM 회귀): 시뮬레이션 스토리(메타/반도체)에서 capex 피크아웃 극이 achilles_kind=words_deeds로, evidence=메타 스토리 id로 잡히는지.
- 계약: frames additive 필드 ↔ 리포트/UI 소비 하위호환.

## 9. 에러/드리프트
- LLM None/retry = 기존 GeminiClient. 결정론 먼저. 프레임 실패=어제 판 유지(fail-soft). frames 필드명↔소비 계약 테스트로 드리프트 가드.

## 리뷰 반영 로그 (3렌즈 2026-07-04)
- **C1 entities 미노출**(grounding) → 해소: interconnectivity를 v2로 이연, v1은 entities 불요.
- **C2 신호 계산 순서 모순**(consistency) → 해소: 결정론 신호 v2 이연, v1 모든 계산은 frames 내부.
- **C3 interconnectivity 결정론 아님/노이즈**(adversarial) → 해소: v2 이연 + '결정론' 라벨 철회, 역할기반·컷오프 명시.
- **C4 저-N 결정론 실명**(adversarial) → 해소: 결정론 축 v2 이연, v1 RAS는 developments 원문 읽어 저-N 포착.
- Major: validate_frame 시그니처 확장 §5·§6 명시 / #45 '콜 불변, 지연 증가 가능'으로 정정 §4 / L-EPU v2 이연 §7 / 4접목→단일 RAS로 축소 §2·§7.
- Minor: achilles_kind enum v1 2값으로 축소 / fear_gap v2(수치 소비 금지) / evidence 이월극 공란 예외 §5 / 가역성 스키마vs계보 분리 §6 / firestore-contract·UI 하위호환 §6.

<!-- spec-review: passed -->
