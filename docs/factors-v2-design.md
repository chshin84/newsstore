# factors 파이프라인 v2 — 개별종목 + 시장 PIT 수집 설계 (2026-07-19)

> 상태: **설계 초안**(구현 전 — 사용자 지시: "아직 시작 말고 기록만"). newsstore = 수집·PIT 보존만.
> 분석·백테스트·전략은 전부 다운스트림(별개 레포 → 집 DB)에서 한다. 이 문서는 "무엇을 받아올지"만 정한다.

## 1. 명분 (왜 수집하나)

newsstore는 다운스트림 **뉴스맵의 "확정 레이어"** 를 **Point-in-Time(PIT)** 으로 보존한다.
뉴스맵은 섹터·테마·종목의 변화를 임베딩 델타로 **선행(lead)** 발견하고, 이 파이프라인이 모으는
정량 데이터가 그 발견을 **후행(confirm)** 확정·사이징한다. 알파는 선행 신호와 후행 확정 사이의
리드타임에 있다 — 정량 데이터는 *발견*이 아니라 *확정* 도구다.

이 설계는 시니어 트레이더 20인(fable) 패널이 각자 다른 FMP 렌즈 + 뉴스맵으로 "나스닥 +10% 아웃퍼폼"
전략을 발상하고 각 데이터의 PIT 필요성을 판정한 결과(`scratchpad` 워크플로 산출)에 접지되어 있다.

## 2. 설계 원리 — 20-렌즈가 그은 선 (수집 여부를 계약이 결정한다)

20개 전략은 제각각이지만 PIT 판정의 **이유**는 한 곳으로 수렴했다. 이것이 수집 범위를 정한다:

- **지금 받아야 함(되돌릴 수 없음)** = ① FMP가 **덮어쓰는 스냅샷형** 엔드포인트(from/to 없이 현재값만
  반환) + ② **뉴스맵의 그날 상태**(경로의존적 파생물).
- **지금 안 받아도 됨(소급 가능)** = **from/to·filingDate**가 붙어 FMP가 과거를 돌려주는 것
  → 다운스트림이 필요할 때 당겨온다.

즉 "무엇을 지금 받을까"는 취향이 아니라 **엔드포인트 계약**이 결정한다. 되감기는 미루고(YAGNI),
덮어써지는 것만 지금 스냅샷한다(사용자의 "되돌릴 수 없는 건 미리"와 정합).

> **구현 전 검증(MEASURE-FIRST):** 아래 "스냅샷형/backfillable" 분류는 20인이 문서로 읽은 것 + 일부
> 실측(analyst-estimates·price-target-consensus·grades-consensus 등)에서 나왔다. 각 엔드포인트를
> 빌드 직전 프로브로 재확인한다(from/to 지원·응답 shape·정정 덮어쓰기 여부).

## 3. Keystone — 뉴스맵 일별 테마 스냅샷 (FMP보다 우선)

20개 `pit_reason` **전부**가 같은 것을 지목했다: **뉴스맵의 그날 테마 지형**. 임베딩·클러스터는
경로의존적이라 나중에 다시 돌려도 그날 값이 안 나오고, 결정적으로 **현재 content·item_vectors에
걸린 60일 TTL이 이 이력을 증발시킨다.**

→ TTL에 안 지워지는 **별도 일별 집계 테이블**로 물화(materialize)한다:
`theme_snapshots/{date}__{theme_id}` = {date, theme_id, centroid_vec, article_count,
interest_share, mapped_tickers[]}. **append-only, TTL 없음.**

이것은 FMP가 아니라 **이미 돌리는 임베딩 파이프라인**에 붙이는 일이며, 어떤 FMP 데이터보다 우선순위가
높다(모든 다운스트림 전략의 공통 전제이자 유일하게 완전 소실되는 데이터).

## 4. 지금 받을 것 — 덮어써지는 스냅샷형 (tier)

### per-symbol (유니버스 ~2000), append-only as-of 스냅샷
| tier | 데이터 | FMP 엔드포인트 | cadence | 키/필드 |
|------|--------|---------------|---------|---------|
| T1 | forward 추정치 | `analyst-estimates` | **일** | eps·rev·ebitda·netIncome Low/High/Avg + numAnalysts (FY0~+5) |
| T1 | 목표가 컨센서스 | `price-target-consensus` | **일** | targetHigh·Low·Consensus·**Median** |
| T1 | 등급 분포 | `grades-consensus` | **일** | strongBuy·buy·hold·sell·strongSell |
| T2 | 밸류·퀄리티 | `key-metrics(-ttm)`·`ratios(-ttm)` | 주 | ROIC·EV/EBITDA·incomeQuality·FCF yield 등 |
| T2 | 부실 스코어 | `financial-scores` | 주 | Altman Z·Piotroski (이력 조회 불가) |
| T2 | 내재가치 | `dcf-bulk`(+`levered-discounted-cash-flow`)·`owner-earnings` | 주 | DCF-가격 괴리(오늘 스냅샷만) |
| T2 | ESG | `esg-ratings` | 주 | ESGRiskRating·industryRank |
| T2 | 유통주식 | `shares-float` | 주 | outstandingShares (자사주 집행 추적) |

### 포지셔닝 (per-symbol 또는 bulk)
| tier | 데이터 | FMP 엔드포인트 | cadence | 비고 |
|------|--------|---------------|---------|------|
| T3 | 내부자 통계 | `insider-trading/statistics` + `insider-trading/latest`(일별 append) | 주+일 | statistics는 정정으로 덮어써짐 |
| T3 | 기관 브레드스 | `institutional-ownership/symbol-positions-summary`·`holder-performance-summary` | 분기(13F 윈도우) | 엘리트펀드 랭킹은 재계산값 → 윈도우별 저장 |
| T3 | ETF 플로우·보유 | `etf/info`(AUM·NAV, 일)·`etf/holdings`(주)·`etf/asset-exposure`(주) | 일/주 | 플로우 직접 엔드포인트 없음 → ΔAUM−NAV수익 잔차 |

### market-state (전역, per-symbol 아님)
| tier | 데이터 | FMP 엔드포인트 | cadence | 비고 |
|------|--------|---------------|---------|------|
| T4 | 무버 리스트 | `biggest-gainers`·`biggest-losers`·`most-actives` | 일 | historical 버전 없음 → 매일 스냅샷 |
| T4 | 구성종목·분류 | `nasdaq/sp500/dowjones-constituent` (+ sector/subSector) | 주 | 분류 변경 버전관리 안 됨(조용히 바뀜) |
| T4 | forward 캘린더 | `dividends-calendar`·`splits-calendar` | 일/주 | 취소·수정으로 덮어써짐(취소분 포함 캡처) |
| T4 | 거시 | `economic-indicators`(빈티지)·`economic-calendar`(estimate) | 발표 시 | 개정 전 값·발표 전 컨센서스 캡처 |
| T4 | 리스크프리미엄 | `market-risk-premium` | 주 | 현재값만 |

## 5. 지금 안 받는 것 — backfillable (다운스트림 on-demand)

from/to·filingDate가 붙어 FMP가 과거를 돌려주므로 지금 쌓지 않아도 잃지 않는다:
- EOD 가격(raw+adjusted)·`earnings` actual·`earnings-surprises-bulk`·`earnings-calendar`(actual)
- 재무제표 3종(income/balance/cash-flow)·`financial-growth`·`income-statement-as-reported`
- technical-indicators(OHLCV의 결정론적 함수)·`treasury-rates`(개정 없음)
- COT report(from/to — 단 "본 날짜" 스탬프 1개만 같이 저장)·트랜스크립트(FMP가 과거 전문 보관)
- 8-K/sec-filings(append-only·타임스탬프)·`grades`/`grades-historical`/`ratings-historical`
- historical-constituent(이벤트 로그)·historical sector/industry performance·PE·배당·분할 확정이력

**예외 — EOD 가격:** backfillable이지만 60일 버퍼 편의로 **매일 수집(raw + 조정이벤트)**. raw가
PIT-safe(조정가는 소급 재계산이라 PIT 아님 — market-data-integrity §1). PIT 급함은 아니고 버퍼 완성용.

## 6. 유니버스 & 지수

- **유니버스 ~2000:** `company-screener`(미국 상장·isEtf=false·시총 상위 ~2000)로 도출(SSOT).
  러셀 구성종목은 FMP에 없음(404). 편입·편출은 스냅샷 시점 명단으로 PIT 보존(생존편향 회피).
- **지수(EOD):** GICS L1(11섹터)·L2(25 산업그룹, 반도체 포함) + Nasdaq·S&P500·Dow + 소형성장·대형성장·밸류 + QQQ·SOXX 등 섹터 ETF.
- **매크로(EOD):** 금리·원자재·환율·변동성 기존 12개 — 5분봉 아님 EOD로.

## 7. PIT 구현 방식 (타입마다 다르다)

**PIT = "그 날 알려져 있던 값을, 그 날 스탬프로, 덮어쓰지 않고 쌓는다."**

| 타입 | 구현 | gotcha |
|------|------|--------|
| 스냅샷형(§4 전부) | **as-of 스냅샷 + append-only**(수집일자 키, 덮어쓰기 금지) | 현행 `asof`가 weekly → T1은 daily로 |
| 실적(reported, 소급수집) | 보고일자(filingDate)로 스탬프, as-first-reported 보존 | 재작성이 최초값을 덮지 않게 |
| EOD OHLC | 원주가(raw) + 조정이벤트 저장 | 수정주가는 소급 재계산 → PIT 아님 |
| 뉴스맵(§3) | 일별 테마 집계 물화, TTL 없음 | 60일 TTL이 원천 증발시킴 |

## 8. TTL 결정

- content(뉴스·item_vectors): 60일 유지.
- **§4 스냅샷 PIT 시계열:** 60일이면 자체 델타 관측 창이 60일뿐. 다운스트림(집 DB)이 매일 당겨가면
  60일로 충분 — **60일 유지, 다운스트림이 장기 보존 책임**. (사용자 결정: PIT 60일 균일.)
- **§3 theme_snapshots:** **TTL 없음**(keystone — 소실 시 복원 불가).

## 9. TipRanks — 미도입, 미래 옵션으로만 기록

- **현재:** 미도입. 현 FMP 플랜에서 402(유료 애드온, $70/월).
- **주는 것:** 애널 개별 등급·목표가 + `date` 롤백(과거 시점 컨센서스 재구성) + 애널 품질(rank·successRate).
  개별 단위라 **목표가 median·사분위 계산 가능**(무료 consensus엔 없음).
- **backfill 깊이: 3년**(그 이전은 Enterprise). → **필요할 때 한 달만 구독**해 `tipranks-search`(애널
  개별 이벤트 raw, 3년, 5000건/요청 페이지네이션)로 벌크 수확하고 끄면 된다. **3년 안에만 재수확하면
  실이 안 끊긴다** → 상시 구독 불필요.
- **한계:** 목표가·등급뿐. **추정치(매출·EPS) VALUES는 담지 않음** → §4 T1 self-collect는 여전히 필요.
- **엔드포인트:** tipranks-search·tipranks-pit-symbol·tipranks-pit-analyst·tipranks-symbol/analyst/firm-summary·tipranks-analysts.

## 10. 확정된 사실

- **추정치 사분위(median·상/하Q): FMP 어디에도 없음** → 설계에서 제거. avg/high/low·numAnalysts가 상한.
- **등급 이력: 무료 backfill**(`grades` 2012~ 이벤트, `grades-historical` 2018~ 월별 분포) → self-collect
  대상 아님(grades-consensus 현재 스냅샷만 가볍게 적재).
- LTG: FMP 네이티브 없음 → forward EPS에서 파생(성숙종목만; 인플렉션은 far-year 추정치 델타·커버리지로 읽음).

## 11. 구현 단계 (착수 승인 시)

0. **theme_snapshots 물화**(keystone) — 임베딩 패스에 일별 테마 집계 append(TTL 없음).
1. 죽은 `stocks` 잡을 올바른 모듈(`run_factors`)로 정정 + FMP 시크릿 연결 + 스케줄러.
2. 유니버스: constituent → `company-screener`(top ~2000).
3. §4 스냅샷 FactorSpec 신설(T1부터) — as-of **daily·append-only**. 엔드포인트 계약 프로브 재확인 먼저.
   컬렉션 네이밍·kind·TTL은 `docs/firestore-contract.md`와 정합 맞춰 확정(SSOT).
4. 지수/ETF/매크로 EOD config 추가.
5. TDD(파싱·계약·PIT 불변식) → 재빌드·배포 → 스모크.

## 12. 열린 결정 (사용자 확인)

- **지금 착수 범위:** keystone(§3) + T1(§4 컨센서스)만 먼저? 아니면 T1~T4 전부(되돌릴 수 없는 표면 전체)?
  — 비용/노력 대 커버리지 트레이드오프. 권고: **keystone + T1 먼저**, T2~T4는 단계적 확장으로 문서화.
- **cadence 세부:** T1 daily 확정(비용 대 신선도). T2~T4 주별 확정?
- **지수/ETF 최종 목록:** §6 외 추가할 것.
