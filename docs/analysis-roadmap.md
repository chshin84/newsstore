# 분석 레이어 로드맵 — newsstore 인리치 (통합 개발)

_출처: news-analytics 설계(`2026-06-28-news-analytics-design.md`, @249aa3d)에서 이관·재서술(2026-06-29). 통합 전략(통합 우선, 안정 시 1회 분리) 하에 newsstore 내부에서 개발한다. 관련: 메모리 `integration-strategy`._

## 1. 배경 / 목표
newsstore의 자동 스토리 생성이 **파편화 + 과병합**으로 실패했다(같은 사건이 여러 카드로, 한 카드가 수백 건의 다른 사건을 흡수). 원인은 임베딩이 아니라 알고리즘 — 단일 임계값 최근접엔 "같은 사건인가?" 판정이 없었다. 해법은 **애널리스트·트레이더 실무 방법론을 코드로 형상화한 분석 능력**을 newsstore 인리치에 단계적으로 더하는 것. 능력마다 **방법론(어떻게) + I/O 계약 + 골든셋(얼마나 잘)** 을 갖춰 *측정되고 개선되는 부품*으로 만든다.

## 2. 능력 단계 (각 red→green 골든셋)
| # | 능력 | 상태 | 핵심 |
|---|---|---|---|
| 1 | **clusterer** (gray-band) | ✅ **이식 완료**(`enrich/clustering.py`) | 결정론 ±gray-band LLM. B³ F1 0.719→0.821. |
| 2 | **score** (impact·risk) | 백로그 | 서프라이즈 impact + 시나리오·차수효과 risk. |
| 3 | **extract_delta** (what-changed) | 백로그 | 컨센서스 대비 변화. herding·recap은 델타 비생성. |
| 4 | **classify_lenses** | 백로그 | ERL 게이트 + 촉매 분류. |
| 5 | **brief** | 백로그 | 요약 합성(사람 루브릭 eval). |

각 단계: 골든셋 먼저(red) → 구현 → green. 잠정 계약은 그 단계에서 확정(4개 I/O를 선구현 추측으로 고정하지 않음 — YAGNI).

## 3. 프로 방법론 템플릿 (각 능력의 내부 정의 — 출처 기반)
- **마스터 ERL 게이트**: "이 뉴스가 Expectations·Risk·Liquidity 중 하나를 바꾸나?" 아니면 노이즈.
- **촉매 분류**: 예정(어닝·FOMC·CPI) vs 비예정(M&A·소송·지정학). 예정=컨센서스 서프라이즈, 비예정=충격×범위.
- **what-changed 델타**: "이전/컨센서스 대비 무엇이 바뀜". Bold(컨센서스서 멀어짐=새정보) > Herding(수렴=잡음).
- **서프라이즈 impact**: `기대변화 × 범위 × 지속성`, **헤드라인 크기 아님**. priced-in이면 무반응.
- **시나리오·차수효과 risk**: 0/1/**2차** 효과 + `likelihood × severity` + 하방·꼬리 + GPR 범주.
- **한계(정직)**: 서프라이즈/priced-in 정확 측정엔 라이브 컨센서스·가격 필요하나 없음 → LLM 정성 근사 + βₖ 후속 캘리브레이션. '정확한 척' 금지(FAIL-LOUD).

## 4. build → adopt (바퀴 재발명 금지)
| 능력 | 채택 | 자작(얇은 층) |
|---|---|---|
| 클러스터 | (현재 gemini 임베딩 + gray-band LLM) — BERTopic/River는 미사용(측정상 품질 미개선) | gray-band 판정·개체 병합 가드 |
| 임베딩 | Gemini(`gemini-embedding-001`/768) | — |
| 감성·방향 | FinBERT/FinGPT(영어; KR은 Gemini 1차) | — |
| 매크로 위험 컨텍스트 | GPR·EPU 공개 데이터 | per-story risk 판정 |
| 글로벌 이벤트·톤 | GDELT(무료, 선택) | — |

- **에이전트 스프롤 금지**(SIMPLE) — 런타임은 검증 붙은 단일 LLM 콜.
- **채택 비용(정직)**: 무거운 모델(BERTopic/sentence-transformers)은 다운로드·콜드스타트 동반 — 도입 시 이미지 무게·메모리 측정해 선언. SIMPLE은 *우리 코드가 얇다*는 뜻.
- **한국어**: FinBERT/GDELT 한국 커버리지 미검증 → 한국 기사는 Gemini 1차, 나머지는 검증 통과 후 보조(미검증 채로 load-bearing 금지).

## 5. 설계 원칙 (통합 후에도 유지 — 미래 재분리 용이)
- **순수 로직 + DI** — 임베더·LLM을 생성자/주입, I/O·저장 없음(`clustering.py`는 이미 이 형태). 유닛=fake(결정론, CI), eval=실 Gemini(오프라인).
- **능력 = 계약 + 골든셋** — 측정 가능 → 지속 개선.
- **클러스터 배정 = 후보 top-k → gray-band만 LLM** — 임계 의존↓·비용 통제, 예산 초과 시 결정론 폴백.

## 6. 테스트 / eval
- 2-tier: 유닛(FakeLLM, 결정론, CI — `tests/test_clustering*.py`) + eval(실 Gemini, baseline 대비 개선 추적 — **오프라인/키 필요, news-analytics origin의 eval 하네스**).
- B-cubed 메트릭(`tests/clustering_metrics.py`) + '자명해(전부병합·전부분리) 격파' 불변식(매직넘버 X).
- 실 F1=0.821은 이란+코스피 골든셋·`gemini-embedding-001`로 측정(오프라인). gray-band 임계값(0.55,0.75)은 newsstore 코퍼스 재캘리브레이션이 후속.

## 7. 참고 문헌
- 클러스터링: [Real-time News Story ID, 2508.08272](https://arxiv.org/abs/2508.08272) · [Entity-aware clustering, 2101.11059](https://arxiv.org/abs/2101.11059)
- 델타/증분: [Moments to Milestones, ACL 2024](https://aclanthology.org/2024.acl-long.390/)
- Risk: [GPR](https://www.policyuncertainty.com/gpr.html) · BlackRock MDS · BRIDGES
- Impact: [News Topics→Stock, 2510.06864](https://arxiv.org/abs/2510.06864) · [Janus-Q, 2602.19919](https://arxiv.org/html/2602.19919v1)
- 금융 NLP: [FinBERT](https://github.com/ProsusAI/finBERT) · [FinGPT](https://arxiv.org/html/2306.06031v2) · [GDELT](https://gdelt.github.io/)

## 8. 범위 밖 / 후속
- 진짜 역사적 이벤트 날짜 추출, βₖ 회귀 캘리브레이션, GDELT 한국 금융 커버리지 실측.
- 미래 재분리(인터페이스 안정·MCP/agent 목표 구체화 시 — `clustering.py`의 DI 경계가 추출 단위).
