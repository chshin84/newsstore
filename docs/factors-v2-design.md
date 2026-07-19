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

## 1.5 현재 구현 상태 (측정 2026-07-19) — 그린필드 아님, **델타**다

리뷰 + 코드·gcloud·Firestore 측정으로 확인: factors 파이프라인은 **이미 상당 부분 구현**돼 있다.
이 설계는 신규 구축이 아니라 **기존 대비 델타**(추가·변경)로 읽어야 한다.

- **기구현(`run_factors`):** constituent에서 유니버스 도출(+`index_members`·`index_changes`·`delisted`
  PIT 컬렉션) → `--cadence daily/weekly`로 컬렉션별 수집. `estimates`·`price_targets`·`grades_consensus`
  (주 1회 as-of)·`prices_eod`(배당조정 EOD 일 1회)·재무제표 등이 이미 `firestore-contract.md`에 정의·구현됨.
- **스케줄 잡 수리(2026-07-19, 완주 검증 진행 중).** `newsstore-stocks` 잡이 없는 모듈 `run_stock_prices`를
  호출해 매일 `exit(1)`로 죽어 **§2 PIT(estimates·targets·grades)가 매일 유실**되던 것을 수리 — ① args를
  `run_factors --cadence all`로 ② FMP 시크릿(`fmp-api-key` v2) 바인딩(빈 plain env가 `--set-secrets`를 가려
  제거 후 재바인딩) ③ task-timeout 300→3600s(전 종목 패스 ~37분이 5분 제한을 넘어 타임아웃 사망했음).
  재실행에서 ~600 유니버스 순회·FMP 200 OK 확인, **완주·§2 PIT 축적 검증은 진행 중**. 교훈:
  `docs/solved_problems.md` 2026-07-19. (향후 최적화: daily=EOD / weekly=fundamentals 분리로 일일 콜 축소 —
  지금은 all 단일이라 ~37분/일.)
- **TTL 정정 완료:** 실제는 60일(`_TTL=60d` 코드 + 기존 데이터 일괄 `2026-09-16` 만료 실측). stale였던
  `firestore-contract.md`·`operations.md`·`setup.md`를 60일로 갱신했다(2026-07-19).
- **유니버스 충돌:** 기구현은 ~600(constituent), 이 설계는 ~2000(screener). 후자는 constituent 기반
  생존편향 PIT 모델(`index_members`)을 바꾸므로 §12 열린 결정으로 남긴다.

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
interest_share, mapped_tickers[]}. **append-only, 60일 TTL 버퍼**(다운스트림이 매일 드레인).

핵심 가치는 **무기한 보관이 아니라 물화(materialize)**다 — 원천 content·item_vectors가 60일 TTL로 죽어도
그날의 테마 상태가 별도 테이블에 굳어 살아남고, 다운스트림(집 DB)이 매일 당겨 영구보관한다. 이렇게 하면
계약의 "컨베이어 벨트·아카이브 아님·다운스트림이 영구보관" 불변식과 공개-read 30/60일 버퍼 가정을 깨지
않는다(리뷰 반영 — 무기한 누적은 계약 위반). 이것은 FMP가 아니라 **이미 돌리는 임베딩 파이프라인**에 붙이는
일이며, 어떤 FMP 데이터보다 우선순위가 높다(모든 다운스트림 전략의 공통 전제이자 유일하게 완전 소실되는 데이터).

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
| T4 | **거시 발표(NFP·CPI·PCE·FOMC 등)** | `economic-calendar` (US·High impact 화이트리스트) | 일(발표 전 컨센 캡처) | **estimate=컨센서스**·actual·previous·impact·unit — 서프라이즈=actual−estimate |
| T4 | 리스크프리미엄 | `market-risk-premium` | 주 | 현재값만 |

**거시 발표 데이터 (실측 2026-07-19):** `economic-calendar`가 이벤트별로 `estimate`(컨센서스)·`actual`(실측)·
`previous`·`impact`(High/Medium/Low)·`unit`을 한 줄로 준다(2주 창 1,459건은 **전 국가 총량** — 수집 대상은
아래 US·High impact 화이트리스트로 좁힌다. CPI·Core CPI·Inflation Rate·PPI·Retail Sales·Michigan Sentiment
전부 est+actual 확인). NFP도 발표일에 같은 형태. **서프라이즈 =
actual − estimate**를 이 하나로 만든다. **PIT 포인트: `estimate`(컨센)는 발표 전에만 존재하고 발표 후
덮어써지므로 forward 창을 매일 스냅샷해 컨센을 캡처**한다(actual은 발표 시 채워짐). 대상은 US High impact
+ 큐레이트 이벤트 화이트리스트(NFP·CPI·Core CPI·PCE·PPI·Retail Sales·ISM·GDP·Unemployment·Jobless
Claims·FOMC 등, config SSOT). **`economic-indicators`(수정 시계열)는 안 받는다 — 실측 리비전은 노상관
(사용자 결정), 캘린더의 발표-시 actual로 충분**.

## 5. 지금 안 받는 것 — backfillable (다운스트림 on-demand)

from/to·filingDate가 붙어 FMP가 과거를 돌려주므로 지금 쌓지 않아도 잃지 않는다:
- EOD 가격(raw+adjusted)·`earnings` actual·`earnings-surprises-bulk`·`earnings-calendar`(actual)
- 재무제표 3종(income/balance/cash-flow)·`financial-growth`·`income-statement-as-reported`
- technical-indicators(OHLCV의 결정론적 함수)·`treasury-rates`(개정 없음)
- COT report(from/to — 단 "본 날짜" 스탬프 1개만 같이 저장)·트랜스크립트(FMP가 과거 전문 보관)
- 8-K/sec-filings(append-only·타임스탬프)·`grades`/`grades-historical`/`ratings-historical`
- historical-constituent(이벤트 로그)·historical sector/industry performance·PE·배당·분할 확정이력

**예외 — EOD 가격:** backfillable이지만 60일 버퍼 편의로 **매일 EOD 1바 수집(raw + 조정이벤트)**. raw가
PIT-safe(조정가는 소급 재계산이라 PIT 아님 — market-data-integrity §1). PIT 급함은 아니고 버퍼 완성용.

> **⚠ 기존 5분봉 파이프라인 폐기(현재 배포된 코드 대상):** newsstore의 목적(뉴스맵 일일 델타)에 인트라데이는
> 과하므로 가격은 **EOD 일일 1바로 전환**한다. 이에 따라 아래가 폐기·대체된다 —
> `prices.py`의 5분봉 파싱(`bars_from_fmp_intraday`·`bars_from_yahoo_intraday`), `price_bars`(바/문서 스트림)
> 컬렉션, **드롭-라스트-봉 로직(#6, prices.py:245)**, `*/15` 스케줄러(→ 미국 종가 후 일 1회), `SNAPSHOT_MAX_POINTS`
> (5분봉 60 → 최근 N일). **이 전환은 #6(5분봉 15분 폴·봉드롭)을 supersede**한다(당시엔 가격을 살리는 스톱갭).
> treasury는 이미 일봉 1바/일이라 EOD에 그대로 맞는다. 인트라데이가 다운스트림에서 필요해지면 FMP에서
> 소급 조회한다(backfillable → defer). 마이그레이션 절차는 §11에 둔다.

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
- **§3 theme_snapshots:** **60일 TTL 버퍼**(다운스트림 드레인). 핵심 가치는 무기한 보관이 아니라 **물화** —
  원천 content(60일 TTL)가 죽기 전에 테마 상태를 별도 테이블로 굳혀 다운스트림이 매일 당겨 영구보관.
  (무기한 누적은 계약의 "아카이브 아님" 불변식 위반 — 리뷰 반영.)

## 9. TipRanks — 미도입, 미래 옵션으로만 기록

- **현재:** 미도입. 현 FMP 플랜에서 402(유료 애드온, $70/월).
- **주는 것:** 애널 개별 등급·목표가 + `date` 롤백(과거 시점 컨센서스 재구성) + 애널 품질(rank·successRate).
  개별 단위라 **목표가 사분위 계산 가능**(median은 무료 `price-target-consensus.targetMedian`에 이미 있음
  §4 T1 — TipRanks가 더하는 건 **사분위·애널 개별·PIT backfill**이지 median이 아니다. 리뷰 반영).
- **backfill 깊이: 3년**(그 이전은 Enterprise). → **필요할 때 한 달만 구독**해 `tipranks-search`(애널
  개별 이벤트 raw, 3년, 5000건/요청 페이지네이션)로 벌크 수확하고 끄면 된다. **3년 안에만 재수확하면
  실이 안 끊긴다** → 상시 구독 불필요.
- **한계:** 목표가·등급뿐. **추정치(매출·EPS) VALUES는 담지 않음** → §4 T1 self-collect는 여전히 필요.
- **엔드포인트:** tipranks-search·tipranks-pit-symbol·tipranks-pit-analyst·tipranks-symbol/analyst/firm-summary·tipranks-analysts.

## 10. 확정된 사실

- **추정치 사분위(median·상/하Q): FMP 어디에도 없음** → 설계에서 제거. avg/high/low·numAnalysts가 상한.
- **등급 이력: 무료 backfill**(`grades` 2012~ 이벤트, `grades-historical` 2018~ 월별 분포) → self-collect
  대상 아님(grades-consensus 현재 스냅샷만 가볍게 적재).
- **거시 실측+컨센서스: `economic-calendar` 하나로 됨**(2026-07-19 실측) — estimate=컨센·actual=실측·
  previous·impact. **리비전 노상관(사용자 결정) → `economic-indicators` 수정 시계열 불필요**.
- **가격: EOD 일일로 확정** — 5분봉 인트라데이 파이프라인 폐기(#6 supersede). 인트라데이는 backfillable → defer.
- LTG: FMP 네이티브 없음 → forward EPS에서 파생(성숙종목만; 인플렉션은 far-year 추정치 델타·커버리지로 읽음).

## 11. 구현 단계 (착수 승인 시)

0. **theme_snapshots 물화**(keystone) — 임베딩 패스에 일별 테마 집계 append(TTL 없음).
1. 죽은 `stocks` 잡을 올바른 모듈(`run_factors`)로 정정 + FMP 시크릿 연결 + 스케줄러.
2. **가격 EOD 전환(마이그레이션)** — `prices.py`를 5분봉 인트라데이 → EOD 1바(`historical-price-eod`
   raw+조정)로 교체, `price_bars`·드롭-라스트 폐기, `*/15` → 미국 종가 후 일 1회 스케줄. 기존 `price_bars`는
   TTL로 자연 소멸(비파괴 — 삭제 안 함). 웹 스냅샷 series는 최근 N일 일봉으로.
3. 유니버스: constituent → `company-screener`(top ~2000).
4. §4 스냅샷 FactorSpec 신설(T1부터) — as-of **daily·append-only**. 엔드포인트 계약 프로브 재확인 먼저.
   컬렉션 네이밍·kind·TTL은 `docs/firestore-contract.md`와 정합 맞춰 확정(SSOT).
5. **`economic-calendar` 수집** — US·High impact + 화이트리스트, forward 창 일일 스냅샷(컨센 캡처) + 발표 후 actual 채움.
6. 지수/ETF EOD config 추가.
7. TDD(파싱·계약·PIT 불변식) → 재빌드·배포 → 스모크.

## 12. 열린 결정 (사용자 확인)

- **지금 착수 범위:** keystone(§3) + T1(§4 컨센서스)만 먼저? 아니면 T1~T4 전부(되돌릴 수 없는 표면 전체)?
  — 비용/노력 대 커버리지 트레이드오프. 권고: **keystone + T1 먼저**, T2~T4는 단계적 확장으로 문서화.
- **cadence 세부:** T1 daily 확정(비용 대 신선도). T2~T4 주별 확정?
- **지수/ETF 최종 목록:** §6 외 추가할 것.
