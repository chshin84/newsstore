# 로드맵 — 작업 순서 (work order SSOT)

> **이 문서가 "무엇을 언제 하는가"의 단일 출처(SSOT)다.** 순서를 어기지 말 것(예: score는 Phase 3 — Phase 1 렌즈 토대 위에 얹힌다). 설계/방법론 상세는 `docs/analysis-design.md`, 스키마는 `docs/firestore-contract.md`. 결제는 **$0 유지**(무료 RSS + Gemini Flash 무료 한도).

newsstore = **수집·저장·호스팅 + 분석을 통합 개발**(전략: 메모리 `integration-strategy`, 인터페이스 안정 시 재분리 보류).

```
[기반 완료] ── [분석 레이어: 지금] ── [응용 레이어: 이후]
 수집·저장·UI    렌즈→클러스터→델타→score→UI    아키타입·시나리오·국면
```

## A. 기반 (✅ 완료·라이브)
| | 내용 | 상태 |
|---|---|---|
| 수집 | 무료 RSS 5분 수집 → Firestore 중복제거 저장 | ✅ 라이브 |
| 호스팅/UI | 피드\|스토리 탭, 소스 필터, 스토리 타임라인 | ✅ 라이브 |
| 태깅·임베딩·클러스터 | Gemini 태깅/임베딩 + **gray-band 클러스터(`enrich/clustering.py` 이식 완료)** | ✅ 라이브(Job#2/#3) |

## B. 분석 레이어 — 지금 (설계 SSOT: `docs/analysis-design.md` §3~§8)
하이브리드 3-tier 렌즈 토대 위에 델타·score·UI를 올린다. **순서 의존이 있으니 아래 순서대로.**

> **✅ 상태(2026-06-29): Phase 1~4 전부 코드완료 + 라이브 배포.** 남은 건 캘리브레이션(P3 🔴)·실측 검증뿐(`unsolved_problems.md` Phase 4 후속). 다음 작업 = **응용 레이어(리포트 탭 → 아키타입, 아래 C)**.

| Phase | 내용 | 의존 | 상태 |
|---|---|---|---|
| **0 피드 볼륨업** | 소스 확장(델타가 보일 밀도) | — | ✅ 대부분 완료(feed-source-expansion) |
| **1 하이브리드 렌즈 + 개체-aware 클러스터** | Tier1 큐레이션 거시렌즈(채권·FX·유가·귀금속·원자재·부동산·정책·중앙은행·산업·리스크) + Tier2 워치종목 + Tier3 emergent. `config/topics.yaml`(렌즈 SSOT, type=standing/development/sector/watch/risk) + 멀티라벨 분류 | 0 | ✅ **코드완료 + 배포**(149 green): 클러스터 이식 + **렌즈 LLM 1차 분류**(asset_hint prior + LLM + 결정론 validator + fail-soft, `--mode lenses`, flash-lite). 라이브(스케줄러 lens-10min). **남음: 실측 커버리지 검증.** spec: `2026-06-29-phase1-topic-lenses-design` |
| **2 델타** | 2-타임스탬프(published_at·delta_time) + milestone 판정(recap 비생성) | 1 | ✅ **코드완료 + 배포**: `milestone.py`(delta_time 배정·`is_new`) — 요약 콜에 편승(별도 Job 없음). 커밋 `372bce3`. **남음: 라이브 실측.** |
| **3 dual score** | risk(렌즈 정렬) + impact(스토리 정렬) LLM 1콜 + 결정론 가드. **임계 이하 노출만 숨김(비파괴)** | 1(·2) | ✅ **코드 완료**(169 green): type-aware 게이트(standing/watch=상시 / 그 외·emergent·unknown=멤버수≥MIN) + dual score LLM 1콜(`{risk,impact,reason}` 0~3, 결정론 validator·fail-soft) + incremental(`count>scored_count`) + `--mode score`. 라이브(스케줄러 score-10min). **남음: 스케일 캘리브레이션(🔴 사용자 결정 — 0~3 스케일 의미·게이트 임계 MIN=2, `unsolved_problems.md` Phase 4 후속).** 설계: `analysis-design.md §7` |
| **4 UI (스토리 리포트 리더)** | per-story 보고서(headline/lead/bullet `article`) + 2-타임스탬프 단일 타임라인(보도/발생순 토글) + 전일대비 ▲▼·NEW·번역 토글 (원안 Now Brief는 per-story `lead`로 대체) | 1·2·3 | ✅ **코드완료 + 배포**(2026-06-29): `article.py` `--mode article` + `web/index.html` + event_time(요약 단독). 라이브(스케줄러 article-10min, 프로덕션 article 검증). spec: `2026-06-29-phase4-story-report-ui-design`. **남음: 캘리브레이션(unsolved Phase 4 후속).** |

> **score 트리거 실험 교훈(2026-06-29):** emergent-only 구조 신호(소스확증·노벨티·velocity)는 material recall **~35–48% 천장**, 놓치는 ~60%가 단일소스 스쿠프 → **렌즈 멤버십(Phase 1)이 그 신호**다. ⇒ **Phase 1 렌즈 먼저, 그 다음 score.** velocity는 게이트로 부적합(와이어 옴니버스가 최고속도). 메모리 `hybrid-topic-lens-model`.

## C. 응용 레이어 — 이후 (분석 레이어 위에 얹힘)
아키타입이 *분석된(렌즈·score된) 뉴스*를 소비해 시장 뷰를 낸다. **분석 레이어가 받쳐야 의미 있음.**
| Step | 내용 | 상태 |
|---|---|---|
| 아키타입 시장 뷰 | 아키타입 정의(예 `장기·롱·현금50%`) → 같은 렌즈뉴스로 시장 뷰 1~100 → lowest/highest/median 집계 | ⬜ |
| 기대/우려 추출 | 뉴스로부터 각 아키타입의 기대·염려 | ⬜ |
| 이벤트 시나리오 대응 | upcoming 이벤트 N시나리오(예 PPI 5단계) × 아키타입 대응 | ⬜ |
| 국면 대응 시뮬 | 섹터/시장 국면(초강세~초약세)별 대응 | ⬜ |

> ✅ **재확인됨(2026-06-29):** 사용자가 응용 레이어 진행을 확정 — **리포트 탭**(섹터별 아킬레스건/기대 프레임으로 72h 뉴스 평가 → 사용자가 과대/과소반응·over/undervalue 판단)을 먼저, **아키타입**은 그 위 후속 층. 설계: 메모리 `report-tab-design` + 작성 예정 spec.

## ultracode(다중 에이전트 Workflow) 적합 지점
- **응용 레이어(아키타입·시나리오)**: 서로 독립이라 병렬 팬아웃 최적(아키타입 N=에이전트 N → 집계).
- **분석 Phase 1 렌즈 분류·골든셋 평가**: 능력별 독립이라 worktree 병렬 가능(단 설계는 통합).

## 연결
- 분석 설계/방법론: `docs/analysis-design.md` · 스키마 계약: `docs/firestore-contract.md`
- 현재 상태·환경: `README.md` · 운영·재배포: `docs/operations.md`
