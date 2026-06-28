# 로드맵 (Step 1~7)

뉴스 → 태깅 → 아키타입 시장 뷰 → 시나리오/국면 대응으로 이어지는 단계. 결제는 **$0 유지**(무료 RSS + Gemini Flash 무료 한도).

> ⚠️ **분할 안내 (2026-06-28):** 이 로드맵은 단일 repo를 전제로 쓰였다. 분할 후 소유는 **newsstore = Step 1(수집)·Step 3(웹 게재/UI)**, **news-analytics = Step 2(태깅)·Step 4~7(아키타입/시나리오/국면)**. 두 repo는 Firestore 스키마로만 만난다 — 경계·계약은 `docs/firestore-contract.md`. 아래 표의 각 Step은 이 분할을 따른다.

| Step | 내용 | 상태 |
|------|------|------|
| **1. Raw RSS 수집·저장** | 무료 RSS 5분마다 수집 → Firestore 중복제거 저장 (LLM 없음) | ✅ 완료·라이브 |
| **2. LLM 태깅** | `items WHERE processed=false`를 **Gemini Flash**로 태깅 → `mark_processed`. 아이템별 독립이라 대량 pipeline 가능 | 🚧 **로직 완료, 배포 대기** — Plan 1~4 코드·테스트 ✅(enrich·Store·tagger/embedder·processor). 남은 건 라이브 배포(Cloud Run Job#2 + `GEMINI_API_KEY`, `docs/operations.md §E`)·requirements.lock 재생성. 상세는 `docs/unsolved_problems.md` |
| **3. 웹 게재** | 태그 드롭다운 + 최근 N개 뉴스 | ✅ 사이트 라이브. **소스 필터는 동작**, 태그 드롭다운은 Step-2가 태그 채우면 자동 활성 |
| **4. 아키타입 시장 뷰** | 아키타입 정의 — 예 `(장기·롱·현금50%)`, `(단기·숏·현금50%)` + 손실 상황. 각 아키타입이 같은 태그뉴스를 보고 **시장 뷰 1~100** 산출 → **lowest/highest/median** 집계 | ⬜ (원래 이번 주 목표) |
| **5. 기대/우려 추출** | 뉴스로부터 각 아키타입의 기대·걱정·염려 파악 | ⬜ |
| **6. 이벤트 시나리오 대응** | upcoming 이벤트에 N개 시나리오(예 PPI 매우높음/높음/중립/낮음/매우낮음) → 각 아키타입 "어떻게 대응?" → 시장 뷰 추측 | ⬜ |
| **7. 국면 대응 시뮬** | 섹터/시장 국면(초강세/강세/중립/약세/초약세)별 "어떻게 대응?" | ⬜ |

## ultracode(다중 에이전트 Workflow) 적합 지점
- **Step 4~7**: 아키타입·시나리오가 서로 **독립**이라 병렬 팬아웃에 최적.
  - 아키타입 N개 = 에이전트 N개 → 각자 뷰 산출 → 집계(lowest/highest/median).
  - Step 6·7은 **시나리오 × 아키타입 격자** 팬아웃.
- **Step 2**: 아이템별 독립 → 대량 pipeline로 태깅.

## 연결
- 현재 상태·환경: `README.md`
- 운영·재배포: `docs/operations.md`
- 설계 근거(소스 선택 등): `docs/handoff/2026-06-12-session-handoff.md` §4~6
