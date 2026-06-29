# 리포트 탭 — 섹터 risk/기대 프레임 합성 보고서 — 설계 (린 v1)

성격: 분석 레이어 위 응용 1차(섹터 의사결정 보조). 토대: Phase 1 렌즈 · Phase 2 델타 · Phase 3 score · stories. 결정 출처: 메모리 `report-tab-design`. 상위: `docs/analysis-design.md` · 계약: `docs/firestore-contract.md`. **이 문서는 3렌즈 리뷰 후 "빼기(SUBTRACT)"로 린하게 재작성됨 — 미결 사용자 결정은 §결정필요 참조(escalated).**

## 1. 목표 / 본질
스토리를 **섹터별 의사결정 보조 보고서**로 합성한다. 본질: 시장의 집단적 고민을 정제해 엿듣고, 사용자가 *"조정이냐 국면 전환이냐 / over·undervalue냐"*를 판단할 재료를 깐다.
- **리포트는 판정하지 않는다 — 프레임(재료)만.** 매수·매도 콜 없음. over/under는 사용자가 가격을 겹쳐서(판정 자동화는 후속 아키타입 레이어).
- **이슈 중심, 가격 데이터 불요.** 리포트는 이슈·리스크·기대·센티먼트만.

## 2. 분석 모델 — 두 극 + 뉴스 대조
토픽마다: **아킬레스건/실질 리스크**(하방) + **기대/컨센서스**(상방 — *내러티브상 기대*, 가격 미사용). 72h 뉴스를 프레임에 대조: 두려움을 트리거한 이벤트? 기대를 트리거/확인한 이슈? 인과 귀속("누가 뭐라 했고→어떤 우려/기대를 건드렸다"). "영향"=우려/기대 내러티브 영향(가격 아님).
- **델타 중심**: 힘이 모이는 곳=델타 있는 뉴스. 델타가 어디 볼지를, 실질-괴리가 판단 재료를.
- **단극 허용**: `risk`(지정학) 등 premium 극이 N/A인 렌즈는 단극 프레임(아킬레스건만).

## 3. 프레임 출처 — seed YAML (저장만, 일배치 재생성 X)
[아킬레스건/기대]는 **구조적·준정적** 값(매일 안 바뀜). 별도 컬렉션·일배치 패스를 두지 않는다(YAGNI — 리뷰 반영).
- **`config/theses.yaml`** (신규, 사용자 편집): 렌즈별 `{achilles_heel[], premium[]}`. 사람이 시드, LLM은 *오프라인 제안*(수동 검토 후 반영)만 — 런타임 자동 재생성 없음. "비-이벤트 포착"은 저장된 thesis만으로 됨.
- 섹터 어휘 = `config/topics.yaml` 렌즈(SSOT). 토픽 버튼 = **watch(개별종목) 외 모든 렌즈 type**(standing·development·sector·risk)에서 도출. thesis 없는 렌즈 → 그 토픽은 v1에서 버튼 비노출(skip).

## 4. 생성 파이프라인 — 단일 리치 콜 (다단계 체인 X)
다단계 chained 합성은 환각 전파+비용폭증이라 v1에서 **제거**(리뷰 반영). 중간 자산(클러스터·score·델타·렌즈) 재사용 — 리포트는 stories의 또 다른 렌더러(기존 per-story `article` 패스와 **별개**: 그건 스토리 1개 보고서, 이건 렌즈 레벨 합성).
```
(런당 1회) 매크로/교차자산 백드롭 — 채권·순환매·원자재·매크로를 1회 합성(cross-lens는 여기 1곳만)
토픽별(렌즈당 1 report):
  thesis(config) + 렌즈의 72h stories 중 [delta·impact 상위 K건 하드캡] + 백드롭
   ↓ LLM 1콜(구조화 출력) → {headline, lead, sections[아킬레스건 트리거 / 기대 트리거 / 미발생]}
   ↓ 검증 — 결정론(언급 티커·섹터·엔티티가 입력 출처에 존재) → LLM 리뷰 1콜(grounding+fit)
출력: reports/{lens_id} (캐시; UI 직접 read)
```
- **입력 하드캡 `REPORT_MAX_STORIES`**(예 K=15, delta·impact 상위) — 한 렌즈 클러스터가 수백 건까지 부푸는 실측(analysis-design §1) 대비 토큰 폭탄 차단. **런당 토큰/콜 예산 상한 + 초과 시 토픽 스킵**(analysis-design §11 폴백 패턴).
- 출력은 **구조화 슬롯**(자유 내러티브 최소화 — 판정 누출↓). watch-list(개별종목 나열)는 v1 제거(프레임만 일관·"개별종목 콜 금지"와 충돌 회피). delta_since_last도 v1 제거(이전 스냅샷 보관 필요 — YAGNI).
- **모델**: §결정필요 ①(실 모델 id 확정 후 단가 대입). incremental 아님 — **per-run 전량 재생성**.

## 5. 검증 레이어 (`domain-llm-runtime`)
- **결정론 먼저**: 언급 티커·섹터·엔티티가 입력 출처에 존재(없으면 드롭/재생성), 길이·섹션 상한.
- **LLM 리뷰 1콜**: `reviewer-grounding`(주장·수치가 출처 stories에 근거) + `reviewer-fit`(섹터 롤업·매수매도/개별종목 콜 금지·길이·스타일). *한계(정직)*: 동급 모델 자기검증 + 결정론은 엔티티 존재만 봄 → **가짜 인과 연결은 못 잡음**. 그래서 v1은 개방형 교차자산 인과(step2)를 빼 그 표면을 줄였다.
- **실패 거동(v1 기본 = FAIL-LOUD)**: 생성·리뷰 실패 시 **새 문서 미커밋(기존 유지), stale 노출 안 함**. 금융 도메인이라 낡은/실패 리포트를 라벨만 붙여 노출하지 않는다.

## 6. 데이터 모델 (additive·비파괴 — firestore-contract 등재 필요)
- **`config/theses.yaml`**(신규, git): 렌즈별 프레임. 컬렉션 아님.
- **`reports/{lens_id}`**(신규 컬렉션): `{topic, headline, lead, sections[], macro_backdrop, generated_at, model, review{passed,notes}}`. **public read**(UI 직접). report 패스 writer.
- stories(렌즈·risk·impact·developments·delta) 재사용 — 신규 필드 없음.
- **계약 등재(plan 작업)**: `reports` 스키마·writer/reader·**보안규칙(public read)**을 `firestore-contract.md`에 추가(드리프트 가드 대상). per-run 전량 재생성이라 *_count incremental 가드 없음(통째 덮어쓰기).

## 7. UI — 리포트 탭
- 새 탭 `리포트`. 주제 버튼 = topics.yaml에서 도출(watch 외 type 전부; §7 예시는 예시일 뿐, 도출 규칙이 SSOT). 클릭 → `reports/{lens_id}` 캐시 렌더.
- 렌더: headline → lead → 구조화 섹션(아킬레스건 트리거/기대 트리거/미발생). 생성시각·"가격 미반영(이슈 중심)" 표기. fail-soft: 리포트 없으면 "아직 생성 전" 강등. 순수함수(node): 버튼 도출(렌즈→버튼).

## 8. 스케줄 / 운영
- 새 모드 `run_enrich --mode report`(같은 processor 이미지) — 엔트리포인트는 기존 run_enrich --mode 확장(드리프트 가드).
- **v1 = 1×/일**(`Asia/Seoul`, 예 07:30). 4×/일·미국장 DST(`America/New_York`) 스케줄러는 **후속**(라이브 비용 보고 빈도 상향 — 리뷰 반영, "저빈도" 주장 철회).
- 비용: §결정필요 ②(실 모델·토큰 캡 대입해 빌드 전 수치 검증). 입력 하드캡 + 런당 예산으로 통제.

## 9. 에러처리 / 드리프트
- LLM None/retry/timeout = `GeminiClient.generate_json`. 결정론 validator 먼저. 토픽 단위 fail-soft. 실패=미커밋(§5).
- 버튼↔topics.yaml 렌즈, reports 필드명↔UI를 계약 테스트로 드리프트 가드.

## 10. 테스트 (TDD)
- report validator 단위(fake LLM): 필수키·길이상한·결정론(출처에 없는 티커 드롭)·구조화 슬롯.
- store 계약(에뮬레이터): reports roundtrip + 비파괴 + per-run 재생성(덮어쓰기).
- 파이프라인 단위(fake LLM): 입력 하드캡·예산 초과 스킵·리뷰 실패 미커밋.
- UI 순수함수(node): 버튼 도출, thesis-없는 렌즈 skip.

## 11. 단계화 (리뷰 반영 — 면적 축소)
- **v1**: config/theses.yaml + 단일콜 report(`--mode report`) + reports store/계약 + UI 탭 + 1×/일(Asia/Seoul). 입력 하드캡·실패 미커밋.
- **후속**: 다단계 chained(교차자산 인과, 결정론 게이팅 동반) · 4×/일+US DST 스케줄러 · thesis 자동 갱신 · delta_since_last · watch-list · 아키타입 레이어 · pricestore 결합.

## 🔴 결정 필요 (escalated — 사용자, 자율 구현 금지)
1. **모델 id**: 사용자 "Flash 3.5"는 **실존 식별자 아님**(Gemini Flash=1.5/2.0/2.5; 코드 실모델 `gemini-3.1-flash-lite-preview`). 어느 실 모델을 쓸지 확정 → 단가 확인.
2. **비용 예산·입력캡**: `REPORT_MAX_STORIES`(K)·런당 토큰/콜 예산·빈도(v1 1×/일 제안). ①의 단가 대입해 $3 상한 충족을 빌드 전 수치로 검증.
3. **리뷰 실패 거동**: v1 기본=미노출(FAIL-LOUD) 제안 — 확정.
4. **thesis 갱신**: 수동 시드(v1) vs 후속 LLM 자동 갱신 주기.
5. **스코프 확인**: 위 린 v1 면적 동의 여부.

<!-- spec-review: escalated -->
