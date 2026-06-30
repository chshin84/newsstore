# newsstore 분석 레이어 설계 — 하이브리드 토픽 렌즈 (파편화 해소 + risk/impact 큐레이션 + 델타 타임라인)

_분석 레이어 마스터 설계 (newsstore 소유)._

> **이 문서의 위치:** 통합-우선 전략 하에 분석은 **newsstore 내에서 개발**한다. 본 문서가 **하이브리드 3-tier 렌즈·개체-aware 클러스터·델타·dual score·UI의 설계/방법론 SSOT**다.
> - 본 문서는 *무엇을·왜·어떻게*의 설계 SSOT. 진행 상태는 메모리 `project-status`.
> - 피드/소스 확장은 `docs/superpowers/specs/2026-06-28-feed-source-expansion-design.md`가 별도 SSOT. 스키마 계약은 `docs/firestore-contract.md`.
> - 사건 클러스터(gray-band)는 `src/newsstore/enrich/clustering.py`로 이식.

## 1. 배경 / 문제 (왜 바꾸나)
라이브 사이트(https://daily-recap-498506.web.app/) 스토리 탭 실측 결과, 자동 토픽 생성이 **두 방향으로 동시에 실패**한다:
- **과병합**: 한 스토리가 443건·360건·213건까지 부풀어 느슨하게만 관련된 기사를 빨아들임(centroid가 generic 중력우물).
- **파편화**: 그런데도 같은 실세계 토픽이 평행 카드로 갈라짐 — 한국 반도체/증시가 3개 카드(443·360·…), 미국 AI가 2개(204·213), 이란 정세가 2개(10·192).

근본 원인은 임베딩이 아니라 **클러스터링 알고리즘**: 탐욕적 단일패스 온라인 centroid 클러스터링(`enrich/processor.py` + `enrich/vector_index.py`)은 ① 도착 순서 의존, ② centroid drift로 평행 대형 클러스터 발생, ③ 한번 배정 후 재고 없음, ④ 임베딩만 사용(개체 무시)이라는 결함을 가진다.

**목표:** 파편화·과병합을 구조적으로 해소하고, 토픽을 **위험(risk)·임팩트(impact) 기준으로 큐레이션**하며, 스토리를 dedup 덩어리가 아니라 **시간순 델타 타임라인**으로 보여주고, 피드 **볼륨업**으로 델타가 드러날 밀도를 확보한다.

## 2. 확정된 결정 (대화로) — 문헌 앵커 포함
1. **토픽 모델 = 하이브리드 3-tier** (순수 emergent도, 순수 큐레이션도 아님). **게이트는 토픽 *생성*이 아니라 *노출(surfacing)*에 건다** — 클러스터는 항상 형성(비파괴), impact가 노출만 결정. §4.
2. **표현 = 임베딩 ⊕ 개체명(NER)** + **병합 패스(micro→macro, 개체 기반)**. 같은 사건은 개체로 묶고, 다른 사건은 개체로 가른다. 근거: 실시간 뉴스 스토리 클러스터링 연구가 개체 기반 병합을 임베딩-중심보다 우수하다고 보고 — [arXiv 2508.08272](https://arxiv.org/abs/2508.08272), [arXiv 2101.11059](https://arxiv.org/abs/2101.11059). (인용 수치는 출처값·**방향 근거**일 뿐, 설계가 특정 숫자에 의존하지 않음.) **사건 배정 = 임베딩+개체로 후보 top-k만 좁히고 *애매한 경계(gray-band)만 LLM이 최종 판정***(pseudo-oracle) — 임계 의존↓·교차언어↑, 비용은 경계에서만. §5.
3. **델타 = wire 개정 비-접기.** 같은 기사의 수정·재발행을 하나로 *접지(collapse)* 않고 개정도 타임라인 포인트로. **단 순수 recap은 새 델타로 안 만듦**(milestone 판정). 기존 요약 패스의 표시-dedup과 충돌 아님 — §6에서 두 dedup 레벨 구분. LLM 증분 milestone — [ACL 2024](https://aclanthology.org/2024.acl-long.390/). §6.
4. **점수 = dual metric (risk + impact).** 차원이 다름 — risk=악재·불확실성(뉴스 빈도·강도, [GPR](https://www.policyuncertainty.com/gpr.html)·[GPR AER 2022](https://www.matteoiacoviello.com/gpr_files/GPR_PAPER.pdf)·EPU 계보), impact=시장 이동 크기(이벤트스터디·토픽회귀, [arXiv 2510.06864](https://arxiv.org/abs/2510.06864)). **LLM 자가채점은 advisory** — 결정론 가드 + 후속 캘리브레이션(§7·§13). §7.
5. **impact는 주 지표 + 임계 이하 숨김**(비파괴: 저장은 하되 UI에서 접기, 하드 삭제 아님). risk는 렌즈 정렬축.
6. **스포츠 제외**: `classify_kind`의 **`sports` kind 단일 메커니즘**(렌즈 hidden 플래그 안 씀)으로 마킹 후 기본 숨김(비파괴).
7. **UI: 좌 이벤트 타임라인(메인) / 우 기사시간 tracker(보조)** + **상단 Now Brief(지금 중요한 것 — impact/risk 상위 합성)**, 행 정렬 대신 인터랙션 하이라이트로 연결. 기존 피드 탭은 raw track으로 유지. §8.
8. **(미래) risk-candidate reader**가 impact를 조정 → **지금은 `impact` 단일 필드만** 두고 별도 `boost` 스키마는 예약하지 않음(YAGNI — reader 구현 시 impact 재계산). §7.
9. **피드 볼륨업 = 별도 병렬 워크스트림(Phase 0)** — 인포맥스/한경/매경/Bloomberg/Benzinga 픽 확정, 나머지·리서치는 Phase 0 카탈로그 프로빙. §9.
10. **소스 tier 가중**: 가격은 별도 루트 → 뉴스 소스를 **1차/분석/wire-헤드라인 tier**로 가중(`feeds.yaml` SSOT, `body_mode` 풍부도 신호 승격). impact 결정론 prior + 랭킹 타이브레이크 + 클러스터 신뢰도. §7·§9.

## 3. 아키텍처 (한 장)
```
기사 → [분류] kind(story/spam/digest/sports) + 토픽 렌즈(멀티라벨, config SSOT) + emergent 클러스터(노출만 impact 게이트)
     → [표현] 임베딩 ⊕ 개체명(NER)
     → [사건 클러스터] 렌즈 안에서 개체-aware 최근접 + 병합 패스(micro→macro)
     → [델타] LLM milestone 판정 → 새 전개만 타임라인 적재 (dedup 안 함), 2-타임스탬프
     → [점수] LLM 1콜 = risk(렌즈 정렬) + impact(스토리/종목 정렬, 임계 숨김, emergent 노출 게이트)
화면: 렌즈 risk순 → 각 렌즈 안 델타 타임라인 impact순 (스포츠 숨김)
       좌 이벤트 타임라인(메인) | 우 기사시간 tracker(보조) ← 인터랙션 연결
```
**2층 구조**: 상위(안정) = 토픽 렌즈, 하위(동적) = 렌즈 안 사건 클러스터/델타. 상위가 고정이라 파편화가 구조적으로 차단되고, 하위는 개체-aware 병합으로 과병합/쪼개짐을 막는다.

## 4. 토픽 렌즈 모델 — 하이브리드 3-tier
| Tier | 무엇 | 출처 | 안정성 |
|---|---|---|---|
| **1. 큐레이션 거시 렌즈** | 지역×도메인(국내/미국 채권·경제·정치·산업구조) · **원자재·FX(원화 FX·유가/에너지·귀금속·기타 원자재)** · 정책(금융/비금융) · 분석렌즈(리스크/위험신호·현재 main 산업·현재 밈) | `config/topics.yaml` SSOT | 고정·상시 |
| **2. 큐레이션 워치 종목** | SK하이닉스·삼성전자 등 **개별 종목 = 각자 렌즈** | `config/topics.yaml` SSOT | 고정 |
| **3. emergent 토픽 (임팩트 *노출* 게이트)** | 1·2에 안 맞는 기사도 개체-aware 클러스터를 **항상 형성**(저장·비파괴). **impact 임계 넘은 클러스터만** 토픽 카드로 *노출* — 생성이 아니라 *노출*을 게이팅 | 자동 발생 | 동적 |

- **멀티라벨**: 한 기사가 여러 렌즈 동시 소속(예: SK하이닉스 → 한국 경제 + 산업구조 + 워치종목). 단일 클러스터의 "이거냐 저거냐" 문제 소멸.
- **분류 인프라 재사용**: 기존 `contracts/classify.py`(kind, collect/store/enrich 공유) + `enrich/tagger.py`(LLM 태그)를 확장. 렌즈 라벨링은 LLM 멀티라벨 분류로.
- **emergent = 노출 게이트(핵심 수정·리뷰 반영)**: 순수 emergent(모든 기사가 씨앗)가 파편화 원인이었음. 그렇다고 클러스터 *생성*을 impact로 막으면 인과가 거꾸로(impact는 멤버가 모인 뒤 산출). 그래서 **클러스터는 항상 싸게 형성**(Phase 1, 비파괴)하되 **impact 임계를 넘은 클러스터만 토픽 카드로 *노출***(Phase 3). 스포츠·필러는 노출 안 됨(피드 잔류) → 443-파편 차단. 신규 엔티티도 안 막힘(클러스터는 형성, *노출*만 impact로 획득) → 순환의존 해소.
- **SSOT (topics.yaml vs taxonomy.yaml)**: **렌즈 리스트 = 신규 `config/topics.yaml` 한 곳**(UI 필터·LLM 분류·정렬이 전부 도출). 기존 `config/taxonomy.yaml`은 **kind·티커/엔티티 어휘(vocab)** 역할 유지 — 렌즈는 taxonomy vocab을 *참조*(중복 정의 금지). 경계: topics.yaml=무엇을 묶는 렌즈, taxonomy.yaml=무엇을 인식하는 어휘.
- **스포츠**: `classify_kind`에 **`sports` kind 단일 추가**(렌즈 hidden 플래그 안 씀 — 메커니즘 1개), 기본 숨김(비파괴 마킹).

## 5. 클러스터링 — 개체-aware + 병합 패스
- **표현**: 기존 `embedder`(gemini-embedding-001, 768dim) 임베딩에 **개체명(인물·기관·지역·티커)을 결합**. 개체는 이미 `tagger`가 뽑는 entities/tickers 재사용 → 별도 NER 모델 없이 LLM 태그를 개체 시그널로.
- **사건 배정(하이브리드 LLM-판정, 신규)**: 렌즈 내 `vector_index.InMemoryVectorIndex` 최근접으로 **후보 top-k만 좁힘**(임베딩+개체). 그다음 **gray-band 게이팅** — 최상위 후보 유사도가 (a) 높은-명확대면 자동 합류, (b) 낮은-명확대면 자동 신규, (c) **중간 애매대만 LLM이 '후보 X 합류 / 신규'를 최종 판정**(pseudo-oracle, [ACL 2024](https://aclanthology.org/2024.acl-long.390/)). 대부분 LLM 없이, 애매한 소수만 호출 → 임계 의존↓·교차언어 정확도↑. 합류 시에도 **변별 개체 겹침**을 추가 가드로(과병합 차단).
- **개체 빈약 fail-safe(리뷰 반영)**: 태그가 비면 임베딩-only로 *느슨하게 풀지 말고* **보수적으로**(합류·병합 보류 → standalone). 빈 개체가 과병합으로 퇴행하지 않게. 빈 태그 비율을 로그로 노출(Fail-Loud).
- **병합 패스(신규)**: 단일패스 후 **micro→macro 병합** — centroid 근접 **+ 변별 개체 겹침** 스토리 병합. **generic 개체(예 'Fed'·'코스피') 단독 겹침으로는 병합 금지** — 변별 개체 ≥2 또는 개체 IDF 가중(흔한 개체 저가중)으로 오병합 차단(리뷰 반영). 개체 기반이 임베딩-중심보다 우수(문헌). **경계 병합 후보도 gray-band면 LLM 판정**(사건 배정과 동일 게이팅).
- **시간창/페이딩**: **48h 기본 유지.** 창을 늘릴 땐 **반드시 fading(오래된 멤버 감쇠) 동반** — decay 없이 창만 늘리면 centroid drift 누적 → 더 큰 메가클러스터(리뷰 반영). 확장은 골든셋(§12) 통과 시에만, 값은 실데이터 캘리브레이션(`cluster.py` DEFAULT_THRESHOLD 주석 방식).
- **임계 튜닝**: `NEWSSTORE_CLUSTER_THRESHOLD` env 유지. 골든셋 회귀로 파편화/과병합 동시 측정.

## 6. 델타 모델 — 2-타임스탬프 + milestone 판정
- **2-타임스탬프**(항목/델타마다):
  | 필드 | 의미 |
  |---|---|
  | `published_at` | 기사 발행시각(이미 있음) — "언제 나온 기사인가" |
  | `delta_time` | 새 전개로 편입된 시각 — "언제 새 일이 됐나" |
- **두 dedup 레벨 구분(리뷰 반영)**: ① **wire 개정 비-접기** — 같은 기사의 수정·재발행을 하나로 *접지* 않고 개정도 타임라인 포인트로(과거 표시-dedup이 개정을 삼키던 것 폐기). ② **recap 비-생성** — 순수 배경/재탕은 새 델타로 *만들지* 않음(milestone 판정). '개정은 보존, recap은 비생성' — 2026-06-15 요약 패스의 표시-dedup과 충돌 아님. (`NON-DESTRUCTIVE`)
- **milestone 판정(LLM pseudo-oracle)**: 새 기사가 기존 스토리의 알려진 델타 대비 **새 전개인가 / 중복·배경 recap인가**를 LLM이 판정. recap이면 새 델타 안 만들고 기존에 귀속(피드엔 잔류). "기사가 옛날 이야기 꺼낼 때"가 바로 이 케이스 — 발행시각만 믿으면 옛 사건이 새 일처럼 올라오므로 델타 판정이 *필요*하다.
- **실용판 `delta_time`**: *우리 스토어에 새 정보로 처음 편입된 시각*. **진짜 역사적 이벤트 날짜를 본문에서 추출**하는 것은 LLM 환각 위험이 커 **후순위 옵션**(§13). 조용한 오류보다 보수적 기본값(`FAIL-LOUD` 정신).
- **마이그레이션(additive·비파괴, 리뷰 반영)**: `delta_time`는 추가 필드. 레거시 스토리는 **백필 기본값 = development의 `time`(첫 기사 published_at)**으로 도출. UI는 `delta_time` 없으면 `time`으로 폴백 → 구 데이터 안 깨짐.
- **기존 요약 패스 재활용 + 용어 통일(리뷰 반영)**: `run_enrich --mode summary`(2026-06-15)가 이미 `developments`(전개 단위 묶기 + first_idx)를 산출 → **델타 = milestone 게이트를 통과한 development**(별도 구조 신설 X). 저장형은 기존 `developments[{text, time, source_count}]` + `delta_time` 추가(LLM은 first_idx만, 코드가 time/delta_time 도출 — 2026-06-15 §5 방식 유지).

## 7. Dual 점수 — risk / impact
| | **Risk** | **Impact** |
|---|---|---|
| 측정 | 악재·불확실성 빈도×강도(하방·꼬리) | 시장 이동 크기(방향 무관) |
| 정렬축 | **렌즈(내러티브)** 정렬 | **스토리·델타·워치종목** 정렬 |
| 계보 | GPR·EPU 계보(뉴스 빈도·강도 기반 범주형) | 이벤트스터디·토픽회귀 계보(토픽→수익률 영향 크기) |
| 구조 | `risk` 0~3 + 근거 1줄 | `impact` 0~3 + 근거 1줄 (**단일 필드** — boost 스키마 예약 안 함) |
- **산출**: 요약/델타 패스의 **LLM 1콜에서 두 필드 동시 출력**(비용 마진 미미).
- **LLM 자가채점 = advisory(리뷰 반영)**: 결정론 validator는 범위·필수키만 보장(점수 *값*의 진실성은 못 보증). 그래서 **단일 점수로 하드 드롭 금지** — 임계 미달은 *피드엔 잔류*하고 토픽 노출/타임라인 강조에서만 빠짐(히스테리시스). 후속 캘리브레이션(§13, 회귀 βₖ)으로 검증. **소스 tier(§9)·규모(멤버수) 신호를 결정론 prior로 보조** — 1차/분석 소스는 impact prior↑, wire-헤드라인은 낮춤.
- **멀티라벨 집계(리뷰 반영)**: risk/impact는 **스토리(사건) 단위로 1쌍** 산출. **렌즈의 risk = 그 렌즈 소속 (열린) 스토리들의 risk 집계**(최신성 가중 max). 한 기사가 여러 렌즈에 들어도 채점은 스토리에 1번, 렌즈는 집계로 도출(중복 채점 없음).
- **임계 숨김**: `impact < 임계` 델타/스토리는 UI에서 접기(저장 유지 — 비파괴).
- **risk 정렬**: 렌즈 카드 묶음을 risk 내림차순 배치(요구 "내러티브 위험도 배열").
- **미래 reader**: risk-candidate reader는 매칭 시 **impact를 재계산**(별도 boost 필드 없이 impact 자체 갱신).

## 8. UI — Now Brief + 좌 이벤트 / 우 기사시간

> **설계 변경(UI):** 글로벌 Now Brief는 **per-story 리드(`lead`)로 대체**(스토리=보고서 철학 — 가로 셀렉터에서 스토리 선택 → 보고서: headline + lead + bullet `article`). 좌/우 2-컬럼 타임라인은 **발생/보도 2-타임스탬프 단일 타임라인 + 보도순/발생순 토글**로 단순화(지연막대 폐기). 전일대비 ▲▼·NEW·번역/원문 토글 추가. 팔레트 Warm Light. 스펙: `docs/superpowers/specs/2026-06-29-phase4-story-report-ui-design.md` · 목업: `docs/superpowers/specs/assets/phase4-report-mockup.html`. 아래 원안은 설계 근거 히스토리로 보존(비파괴).

- **탭 유지**: `피드 | 스토리`. **피드 탭 = raw track**(순수 발행시간순) 그대로.
- **상단 Now Brief(브리핑 우선, 신규)**: 스토리 탭 최상단에 **"지금 중요한 것"** — 열린 스토리 중 **impact/risk 상위 N개를 1회 LLM 합성**으로 묶은 브리핑(렌즈 가로지름). *결론 먼저*, 클릭하면 해당 렌즈/타임라인으로 drill-down. 요약 스케줄러에 편승해 주기 합성, 상위 N만이라 비용 작음. 합성 실패 시 브리핑만 생략(나머지 뷰 정상 — Fail-soft).
- **스토리 뷰**: 렌즈를 **risk순**으로, 각 렌즈 안 스토리를 펼치면:
  - **좌(메인) = 이벤트 시계열**: 델타 milestone들, event/delta-time 순(위=최신). impact순 강조/숨김.
  - **우(보조, 슬림) = 기사 시간 tracker**: 델타를 낳은 원본 기사들, `published_at` 순.
  - **연결 = 인터랙션**(행 정렬 ❌, 두 시계가 달라 정렬하면 어긋남): 좌 델타 호버/클릭 → 우 출처 기사 하이라이트, 역방향도. 기존 story-timeline-ui(2026-06-15)의 "전개↔기사 버킷팅" 매핑 규칙 재사용.
- **스포츠 숨김**, impact 임계 이하 접기.

## 9. Phase 0 — 피드 볼륨업 (병렬 워크스트림)
SSOT는 `config/feeds.yaml`. 피드 변경은 이미지 COPY → **재빌드 + Job 갱신** 필요(`docs/operations.md`).

**인포맥스 (확정)** — 기존 5개(S1N2·S1N15·S1N16·S1N21·S1N23) 유지 + 추가:
| 코드 | 섹션 | asset_hint |
|---|---|---|
| S1N7 | IB/기업 | `kr_corp,ib` |
| S1N13 | 기획기사 | `kr_market`(심층) |
| S1N9 | 칼럼/이슈 | `opinion` |
| S1N12 / S1N19 | 외부기고 / 기고 | `research` |
| S1N17 | 부동산 | `kr_realestate`(선택) |
| S1N25 | 보도자료 | `kr_corp`(선택) |

상속: `source: 인포맥스, language: ko, poll_minutes: 60, body_mode: summary, tz_offset: 9`.
스킵(잡음/무본문): S1N10 시사용어·S1N11 인물동정·S1N14 임시메인·S1N22 ad·S1N24 영상·clickTop·allArticle.

**한국경제 (확정)** — 기존 finance(증권) 유지 + 추가: economy(경제)·realestate(부동산)·it(IT)·international(국제)·society(사회). URL `https://www.hankyung.com/feed/{section}`. 상속: `source: 한국경제, body_mode: headline`(per-item 본문 없음).

**매일경제 (확정)** — 기존 mk_stock(증권 50200011) 유지 + 추가: 경제 30100041(`kr_macro`)·정치 30200030(`kr_politics`)·사회 50400012(`kr_social`)·국제 30300018(`global`)·기업·경영 50100032(`kr_corp`)·부동산 50300009(`kr_realestate`). URL `https://www.mk.co.kr/rss/{code}/`. 상속: `source: 매일경제, language: ko, body_mode: summary`. 스킵: 헤드라인/전체뉴스(중복)·문화연예·스포츠·게임·영문·MBA 등.

**Bloomberg (확정 추가)** — 기존 9개(markets·technology·economics·korea·business·politics·bview·crypto·wealth) + 추가: industries(`https://feeds.bloomberg.com/industries/news.rss`, `industries`)·green(`https://feeds.bloomberg.com/green/news.rss`, `esg,energy`). **카탈로그 SSOT**: `https://www.bloomberg.com/robots.txt` 하단 12개 `.xml` URL을 Phase 0에서 프로빙해 누락 섹션 확정(gadfly는 폐지됨, bview에 흡수). 대부분 headline이라 `body_mode`는 description 유무로 프로빙 결정.

**Benzinga (확정 추가)** — 기존 5개(news·markets·movers·crypto·commodities) + 사용자 제공 카탈로그 추가: large-cap(`/news/large-cap/feed`)·small-cap(`/topic/small-cap/feed`)·insider-trades(`/news/insider-trades/feed`)·tech(`/tech/feed`)·AI(`/topic/ai/feed`)·ETFs(`/etfs/feed`)·rumors(`/news/rumors/feed`)·offerings(`/news/offerings/feed`)·trading-ideas(`/trading-ideas/feed`)·stock-of-the-day(`/topic/stock-of-the-day/feed`)·after-hours(`/after-hours-center/feed`)·bonds(`/markets/bonds/feed`). 상속: `source: Benzinga, body_mode: summary`. asset_hint 매핑(rumors→rumor·ai/tech→tech·bonds→us_bond·commodities→commodity). 원자재/FX 렌즈는 Benzinga commodities/bonds + Investing bonds/fx + InvestingLive로 공급.

**나머지 소스 (Phase 0 프로빙)**: Reuters 미추가 섹션 카탈로그 + **무료 리서치** 후보(NY Fed Liberty Street Economics, NBER, BIS, IMF Blog, VoxEU/CEPR, Atlanta/St.Louis Fed, BoE Bank Underground, Damodaran, Calculated Risk; 한국 BOK·KDI·KIEP·KCMI·KIET는 RSS 여부 확인). 각 후보는 HTTP 200·본문 유무 프로빙 후 `feeds.yaml`에 등재(기존 검증 관례 따라).

**소스 tier 가중(신규)**: `feeds.yaml`에 **`tier`** 필드 추가(SSOT) — `primary`(중앙은행·공시·1차) / `analysis`(리서치·심층기획) / `wire`(헤드라인). `body_mode` 풍부도와 함께 — impact 결정론 prior(§7)·랭킹 타이브레이크·클러스터 신뢰도 가중에 사용. 기존 피드는 기본 `tier=wire`로 백필(비파괴), 리서치·중앙은행은 `primary`/`analysis`로 지정.

## 11. 에러처리 / Fail-loud
- **LLM None 가드**: 기존 `llm` 래퍼(timeout/retry/None가드) 유지. milestone/점수 JSON은 결정론 validator 먼저(파싱·필수키·범위), 실패 재시도, critical은 스킵+로그(다음 런 재시도) — 해당 스토리만 보류, 전체 패스 안 죽임.
- **임베딩 dim 가드**: 768dim 가드(기존) 유지. 개체 결합 표현도 차원 계약 테스트.
- **드리프트**: 렌즈 리스트(config) ↔ UI 필터 ↔ 분류 라벨 어긋남을 테스트로 터뜨림(생성·계약 가드, CLAUDE.md 원칙3·4). 모델명 상수 드리프트는 라이브 스모크가 잡음.
- **LLM 호출 예산(하이브리드 반영)**: 하이브리드 배정·Now Brief는 추가 LLM 콜 — **gray-band(애매한 소수)·상위 N**만 호출로 통제. 콜수/비용 로깅 + 런당 상한, 초과 시 **결정론 폴백**(임계 기반 배정)으로 강등(Fail-soft, 패스 안 죽임).

## 12. 테스트 전략 (TDD)
- **에뮬레이터 계약 테스트**: 신규 Store 계약(델타 2-타임스탬프 저장/조회, 점수 필드, 렌즈 멀티라벨) — `MSYS_NO_PATHCONV=1 docker compose run --rm test`.
- **클러스터/병합 단위테스트**: 개체-aware 합류·병합 패스의 입출력(`test_cluster.py`·`test_vector_index.py` 확장).
- **파편화 회귀 골든셋**: 라이브에서 본 "한국 반도체 3분할·미국 AI 2분할·이란 2분할" 케이스를 **고정 입력 골든셋**으로 만들어, 재설계 후 **1토픽으로 수렴**하는지 불변식으로 검증(매직넘버 금지 — 개수가 아니라 "같은 핵심 개체 집합은 1스토리" 불변식).
- **라이브 스모크**: 배포 후 스토리 탭 실측 재확인(curl/스크린샷, 증거 후 주장).

## 13. 범위 밖 / 후속
- **Phase 5 risk-candidate reader**(미래) — impact boost 소스.
- **진짜 역사적 이벤트 날짜 추출**(`delta_time` 정밀화) — LLM 환각 위험, 신뢰도 확보 후.
- **회귀 기반 impact 보정**(βₖ 학습) — 데이터 축적 후 LLM impact를 검증/캘리브레이션.
- 모바일 전용 레이아웃 정밀화(반응형 기본만).

## 14. 참고 문헌
- 클러스터링/파편화: [Real-time News Story Identification, arXiv 2508.08272](https://arxiv.org/abs/2508.08272) · [Event-Driven News Stream Clustering (entity-aware), arXiv 2101.11059](https://arxiv.org/abs/2101.11059)
- 델타/증분 요약: [From Moments to Milestones, ACL 2024](https://aclanthology.org/2024.acl-long.390/)
- Risk 지수: [GPR Index](https://www.policyuncertainty.com/gpr.html) · [Measuring Geopolitical Risk, AER 2022](https://www.matteoiacoviello.com/gpr_files/GPR_PAPER.pdf) · EPU(Baker-Bloom-Davis)
- Impact 측정: [A Framework for Measuring How News Topics Drive Stock Movement, arXiv 2510.06864](https://arxiv.org/abs/2510.06864)
