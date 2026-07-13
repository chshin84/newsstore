# Firestore 데이터 계약 — newsstore

이 문서는 수집 전용 스토어의 컬렉션 스키마와 UI read 계약이다. newsstore는 **수집(collect) 전용**이다 — 뉴스 RSS 수집, 가격·펀더멘털 수집, Firestore 저장, 정적 웹 확인 UI만 있고 분석/LLM 레이어는 없다.

## 컬렉션 개요

| 컬렉션 | writer | reader | TTL(30일) | 비고 |
|---|---|---|---|---|
| `items` | collect Job | web UI | 있음(`expire_at`) | 뉴스 기사 원본 + 수집 시점 `kind` 분류 |
| `feed_state` | collect Job | collect Job | **없음** | etag/last_modified 폴링 커서 — 만료시키면 증분 수집이 어긋난다 |
| `meta` | collect Job | web UI | 없음 | 소스 목록·tier 발행 |
| `prices` | prices Job | web UI | 있음(`expire_at`) | 지수·환율·국채 **최신 스냅샷**(값+최근 시계열) — 웹 확인용 |
| `price_bars` | prices Job | 다운스트림 | 있음(`expire_at`) | **5분봉 완전 스트림**(바 1개=문서 1개). 국채는 일봉 1바/일 |
> 위는 뉴스·시세 수집 표면이다. 다운스트림 백테스트용 **팩터·펀더멘털 수집**(ratios·재무제표·배당조정가·컨센서스 스냅샷·PIT 유니버스 등 ~17개 컬렉션)은 이 문서 하단 「팩터·펀더멘털 수집 계약」 절이 SSOT이며, `entrypoints/run_factors`로 **구현돼 있다**.

## TTL 규칙 (1개월, 비용 통제)

Firestore TTL은 문서의 타임스탬프 필드를 정책이 가리켜 만료시킨다. 이 스토어의 만료 필드명은 **`expire_at`**로 통일한다.
- **`items`·`prices`·`price_bars`·`fundamentals`**: 각 문서에 `expire_at`을 넣고, 컬렉션마다 gcloud TTL 정책을 건다(프로비저닝은 `docs/setup.md`·`docs/operations.md`). `items`·`prices`·`fundamentals`는 저장 시각 + 30일, **`price_bars`는 바 날짜 + 30일**(스트림이라 바 자체의 나이 기준).
- **`feed_state`엔 `expire_at`을 절대 넣지 않는다.** ETag·커서가 만료되면 증분 수집이 매번 전량 재수집으로 어긋난다.
- `expire_at` 주입은 store가 단일 통제점이다(`firestore_store.py`). 호출자가 안 넣어도 store가 보장한다.

## 컬렉션 스키마

### `items` (collect가 기록, 공개 read)
- **필드**: `feed_id, source, asset_hint, language, url, title, body, published_at, fetched_at, kind, expire_at`.
- 모델 SSOT는 `src/newsstore/contracts/models.py`의 `RawItem`.
- **`kind`** (story|spam|digest|sports) — 수집 시점 선분류. `_to_doc()`가 `upsert_items` 시점에 `classify_kind(title, body)`를 호출해 박는다(SSOT: `src/newsstore/contracts/classify.py`의 SPAM/SPORTS/DIGEST 키워드). web UI는 `kind === "story"`만 노출하고 나머지는 숨긴다. LLM이 아니라 순수 키워드 규칙 필터다.
- **`expire_at`** = `fetched_at + 30일`. TTL 정책이 이 필드를 보고 만료시킨다.

### `feed_state` (수집기 전용, 비공개)
폴링 캐시(`etag, last_modified, last_fetched`). **`expire_at` 없음**(위 TTL 규칙).

### `meta` (collect가 기록, 공개 read)
사이트용 소형 메타 문서(예: `sources`). 소스 목록과 **소스 tier**를 여기로 발행한다(아래 §공유 설정).

### `prices` (prices Job이 기록, 공개 read)
지수·환율·국채 **최신 스냅샷**(값 + 최근 5분봉 시계열) — 웹 확인 UI가 읽는다. 매 패스 덮어쓰기. 문서 키 = 심볼 key(예: `sp500`, `usdkrw`, `us10y`).
- **필드**: `close, change, percent_change, datetime, currency, series, label, symbol, group, order, fetched_at, source, flags, expire_at`. `series`는 최근 봉(5분봉, 국채는 일봉)에서 도출한 `{t, c, v?}` 배열.
- **`fetched_at`** (신선도) — 조회 시각. 스케줄러가 조용히 멈춰 낡은 값을 실시간처럼 보여주는 사고를 막는 검문소 필드.
- **`source`** (fmp|fmp_treasury|yahoo) — 이 심볼을 어디서 가져왔는지. 대부분 FMP, 국채는 FMP treasury-rates에서 도출, kosdaq·dxy·wti 3종만 Yahoo 폴백(FMP Premium 미커버).
- **`flags`** (비파괴 상식범위 플래그) — %등락이 상식 밖(지수 ±15%·환율 ±5% 가이드)이면 삭제하지 않고 여기에 표시한다. 검증은 하되 수정은 하지 않는다.
- **`expire_at`** = 저장 시각 + 30일(store 주입).

### `price_bars` (prices Job이 기록, 다운스트림용)
5분봉 **완전 스트림** — 바 1개가 문서 1개. 다운스트림 DB가 한 달 안에 적재한다는 가정. 문서 키 = `{심볼key}__{YYYYMMDDHHMMSS}`(결정론 — 겹쳐 받아도 멱등, 중복 없음).
- **필드**: `key, symbol, label, group, order, source, datetime, close, open?, high?, low?, volume?, fetched_at, expire_at`. OHLCV는 소스가 주면 싣고, 국채는 `close`(수익률 %)만.
- **`datetime`** — 소스 타임스탬프 문자열을 보존한다(FMP 인트라데이는 거래소 로컬시각, Yahoo는 UTC ISO, 국채는 날짜). 다운스트림이 해석한다.
- **적재는 새 바만** — `run_price_pass`가 `filter_new_bar_ids`로 이미 있는 바를 걸러 5분 주기 write 비용을 묶는다.
- 미국채(`fmp_treasury`)는 5분봉이 없어 **일봉 1바/일**(id는 `{key}__{YYYYMMDD}`).
- **`expire_at`** = 바 날짜 + 30일(store 주입).

### `fundamentals` (fundamentals Job이 기록, 공개 read)
티커별 재무제표(FMP). 문서 키 = 티커 심볼(예: `AAPL`).
- **필드**: `income[], balance[], cashflow[], fetched_at, expire_at`. 각 배열은 annual·최근 5개.
- **`fetched_at`** (신선도) — 조회 시각.
- **`expire_at`** = 저장 시각 + 30일(store 주입).

## Store 표면 (`firestore_store.FirestoreStore`)
- `upsert_items(items) -> int` — `_to_doc`가 `kind` 분류 + `expire_at`을 박는다.
- `get_feed_state`, `set_feed_state`, `count`, `filter_new_ids`, `set_meta`.
- `save_price(key, data)`, `get_price(key)` — 스냅샷. TTL(`expire_at`) 주입.
- `filter_new_bar_ids(ids)`, `save_bars(bars)`, `get_bars(key)` — price_bars 스트림. `save_bars`가 바 날짜 기준 TTL 주입.
- `save_docs(collection, docs)`, `filter_new_ids_in(collection, ids)`, `save_snapshot(collection, doc_id, data)`, `get_snapshot`, `get_docs` — 팩터·펀더멘털 계약의 제네릭 적재(하단 절). `expire_at`(수집 시각+30일) 주입.
- `close`/`__enter__`/`__exit__`.

## 필터 (비-LLM 규칙, 수집 경로에 배선됨)
저장 전에 원본을 버리지 않는다(비파괴). 대신 수집 시점에 분류·중복 제거만 한다.
- **dedup**: `parser.py`(link→guid→title url 기반) + `store.filter_new_ids` + `upsert_items`(이미 있으면 미덮어씀).
- **kind 분류**: `_to_doc`가 `classify_kind`로 spam/sports/digest를 라벨링 → UI가 story만 노출.
- **본문 수집**: `collect/body_fetch.py`의 `enrich_bodies`는 화이트리스트 소스의 기사 페이지를 HTTP로 fetch해 본문을 채운다(LLM 아님).

## 불변식 (계약 테스트로 강제 — FAIL-LOUD)
구두 약속이 아니라 테스트로 지킨다.
- **kind stamp** — `upsert_items` 시점에 모든 item이 `kind`를 갖는다(수집 시점 분류). web UI의 story 필터가 여기에 의존한다.
- **스키마 드리프트 가드** — web UI가 읽는 필드명(items의 `source`·`kind`, prices의 `percent_change` 등)이 바뀌면 터지는 계약 테스트. 이름이 조용히 어긋나면 사이트가 빈 화면이 된다.
- **feed_state에 `expire_at` 부재** — TTL이 폴링 커서를 만료시키지 않음을 지킨다.

## 인프라
- Firestore 보안규칙(`items`·`prices`·`fundamentals`·`meta` 공개 read)·복합 인덱스는 newsstore가 적용한다(보안규칙 `docs/operations.md §C`, 복합 인덱스 §D). TTL 정책 프로비저닝은 `docs/setup.md`·`docs/operations.md`.
- 비밀(`FMP_API_KEY`)은 백엔드 전용(SECRETS) — 클라이언트/커밋 금지.

## 공유 설정
- **`config/feeds.yaml`의 `tier` 필드** — `feeds.yaml`은 수집기 SSOT다. 수집 패스가 `meta/sources`에 `{"sources":[...], "tiers":{source: tier}}`로 발행한다. UI는 거기서 소스 등급을 읽는다. 파일을 복제하지 않는다(SSOT).

---

# 팩터·펀더멘털 수집 계약 (Phase 0/1 — 다운스트림 백테스트 seam)

이 절은 다운스트림 팩터·백테스트 엔진이 쓸 재무·가격·컨센서스 데이터를 newsstore가 어떻게 수집·저장하는지의 계약이다. **분석은 다운스트림이 한다 — newsstore는 수집·전달만 한다.** 두 레포가 이 절을 SSOT로 공유한다. 모든 엔드포인트는 FMP `/stable/` base이며, 아래 표의 심볼·엔드포인트는 실 API로 접지(2026-07-13, Premium 티어에서 열림 확인)했다.

## 모델 — 컨베이어 벨트(30일 롤링 버퍼), 아카이브 아님

newsstore는 이 데이터를 영구 보관하지 않는다. **모든 컬렉션에 30일 TTL**을 걸고(비용 통제), 다운스트림 DB가 그 30일 안에 적재해 영구 보관한다. 30년치 백필도 예외가 아니다 — 한 번 흘려보내고 다운스트림이 받아간 뒤 만료된다. 그래서 `expire_at`은 **데이터 날짜가 아니라 수집 시각 + 30일**이다(그래야 2005년 행도 지금 수집하면 30일 살아 있다). 정상 운영에선 초기 백필 후 증분만 수집하므로 정상상태 용량은 작다.

**하드 의존성 (FAIL-LOUD — 조용히 숨기지 않는다):** 이 모델은 **다운스트림이 30일 안에 적재함**을 전제한다.
- **§2(백필 불가) 데이터** — 포워드 추정치·목표가·등급 분포 스냅샷은 FMP가 과거값을 주지 않는다(현재값만). 다운스트림 적재가 30일 넘게 밀리면 그 사이 주간 스냅샷은 **영구 유실**되고 리비전 velocity에 복구 불가능한 구멍이 난다. 다운스트림 적재 지연 모니터링이 필수다 — 여기서 30일은 안전마진이 아니라 데드라인이다.
- **§1(백필 가능) 데이터** — 재무제표·비율·조정가·PIT 유니버스는 유실돼도 재수집으로 복구된다(비용만 든다).

## 유니버스 (PIT — 생존편향 없음)

수집 대상 종목 = **S&P 500 ∪ Nasdaq-100 ∪ Dow 30**의 현재 구성종목(중복 제거, ~600). 목록을 하드코딩하지 않고 constituent 엔드포인트에서 **도출**한다(SSOT). 과거 시점의 진짜 모집단은 constituent 변경 로그 + 상장폐지 목록으로 재구성한다(생존편향을 잡는다 — 오늘 목록으로 과거를 조회하면 살아남은 종목만 남아 성과가 부풀려진다).

## 공통 필드·저장 원칙

- 모든 문서에 `fetched_at`(수집/as-of 시각)·`source: "fmp"`·`expire_at`(수집 시각 + 30일).
- **날짜가 있는 데이터는 날짜별 개별 문서**(`{symbol}__{YYYYMMDD}`, 멱등 set)로 저장한다 — 배열 무한성장과 Firestore 1MB 문서 한도를 피한다. 겹쳐 받아도 같은 id라 중복이 없다(뉴스 dedup·`price_bars`와 동일 패턴).
- 현재값 스냅샷(프로파일·현재 구성종목)은 `{symbol}`·`{index}` 한 문서에 덮어쓴다.
- 응답 필드는 FMP 스키마 그대로 저장한다(다운스트림이 해석) — newsstore가 파생 지표를 만들지 않는다.

## §1 백필 가능 — 지금 요청 (Phase 0 백테스트)

| 컬렉션 | 문서 id | FMP 엔드포인트 | 담는 것 | 주기 |
|---|---|---|---|---|
| `ratios` | `{symbol}__{date}` | `ratios?symbol=&period=annual`(+quarterly) | 시점정합 멀티플(P/E·P/S·P/B·EV/EBITDA 등) — 싼지 축의 코어 | 주 1회 |
| `income` | `{symbol}__{date}` | `income-statement?symbol=&period=annual` | 손익계산서(+분기) — 멀티플 재계산·성장 파생의 원천 | 주 1회 |
| `balance` | `{symbol}__{date}` | `balance-sheet-statement?symbol=&period=annual` | 대차대조표 | 주 1회 |
| `cashflow` | `{symbol}__{date}` | `cash-flow-statement?symbol=&period=annual` | 현금흐름표 | 주 1회 |
| `prices_eod` | `{symbol}__{date}` | `historical-price-eod/dividend-adjusted?symbol=` | **배당조정** 일봉(adjOpen/adjHigh/adjLow/adjClose·volume) — 총수익 백테스트(가격만 쓰면 배당만큼 왜곡) | 일 1회(증분) |
| `market_cap` | `{symbol}__{date}` | `historical-market-capitalization?symbol=` | 일별 시가총액 — 사이즈 팩터·바스켓 가중 | 주 1회 |
| `grades_history` | `{symbol}__{date}` | `grades-historical?symbol=` | 날짜별 애널리스트 등급 카운트(strongBuy/buy/hold/sell/strongSell) — 리비전 방향, PIT | 주 1회 |
| `profiles` | `{symbol}` | `profile?symbol=` | 섹터·산업·시총·설명문(현재값, 덮어쓰기) — 섹터중립 랭크·유니버스 필터·테마 판정 | 주 1회 |

## §2 백필 불가 — 지금부터 축적 (가장 시급)

FMP는 이 값들의 "과거 어느 날의 값"을 주지 않는다. **오늘부터 주 1회 as-of 스냅샷**을 찍지 않으면 리비전 velocity를 영영 못 만든다.

| 컬렉션 | 문서 id | FMP 엔드포인트 | 담는 것 | 주기 |
|---|---|---|---|---|
| `estimates` | `{symbol}__{YYYYMMDD}` | `analyst-estimates?symbol=&period=annual` | 포워드 FY 컨센 추정(매출·EPS avg/high/low, 분석가 수)의 as-of 캡처 | 주 1회 |
| `price_targets` | `{symbol}__{YYYYMMDD}` | `price-target-consensus?symbol=` | 목표주가 컨센(high/low/median/consensus) | 주 1회 |
| `grades_consensus` | `{symbol}__{YYYYMMDD}` | `grades-consensus?symbol=` | 등급 컨센 분포(strong buy…sell 카운트) 스냅샷 — `grades_history`로도 재구성 가능한 싼 보험 | 주 1회 |

## PIT 유니버스 (생존편향 보정)

| 컬렉션 | 문서 id | FMP 엔드포인트 | 담는 것 | 주기 |
|---|---|---|---|---|
| `index_members` | `{index}` (sp500·nasdaq·dow) | `sp500-constituent`·`nasdaq-constituent`·`dowjones-constituent` | 현재 구성종목(symbol·name·sector) — **유니버스 도출 SSOT** | 주 1회 덮어쓰기 |
| `index_changes` | `{index}__{date}` | `historical-sp500-constituent`(+nasdaq·dowjones) | 편입·편출 이벤트(dateAdded·addedSecurity·removedTicker) — PIT 모집단 재구성 | 주 1회 |
| `delisted` | `{symbol}` | `delisted-companies` | 상장폐지 종목(companyName·exchange·delistedDate) | 주 1회 |

## §3 나중 (verify Phase 2+ — 지금은 안 함, 계약만 예약)

`revenue-product-segmentation`·`revenue-geographic-segmentation`(테마 매출 근접) · `historical-sector-pe`·`historical-industry-pe`(섹터 상대 리레이팅) · `discounted-cash-flow`(내재가치 교차검증) · `sec-filings-search`(어닝 콜 전화록 대체 — 전화록은 Ultimate 전용) · `earnings`(어닝 서프라이즈). 필요해질 때 위와 같은 원칙(날짜별 개별 문서·30일 TTL·FMP 스키마 그대로)으로 추가한다.

## 티어 경계 (§0 — Premium이 못 주는 것)

- **Bulk/Batch 전송은 Ultimate 전용.** 그래서 심볼별로 수집한다. 각 엔드포인트가 심볼당 full history를 한 콜에 주고 Premium이 750콜/분이라, 전 유니버스 백필도 수 분~십수 분이다 — 콜 폭증이 아니며 Bulk는 편의지 필수가 아니다. **지금 업그레이드 불요.**
- **어닝 콜 전화록은 Ultimate 전용.** verify는 Phase 2+라 먼 얘기고, 그때 Ultimate로 올리거나 Premium이 주는 SEC 필링(10-K JSON, `sec-filings-search`)으로 대체한다.

## 조인 키 — 티커 (gotcha #3, 별도 소과제)

다운스트림은 뉴스와 팩터를 **티커로 조인**한다. 그러려면 newsstore 뉴스 `items`가 티커로 해석 가능해야 하는데, 현재는 `asset_hint`만 있고 해석된 티커가 없다. 티커 태깅은 무-LLM 규칙(alias 사전 매칭)으로 되살릴 수 있다 — 이번 수집-전용 전환에서 삭제한 `watchlist.yaml`(티커+alias)이 바로 그 어휘였다. **별도 소과제로 남긴다**: `items`에 `tickers[]` 필드 추가 + 티커-alias SSOT 복원. 이 계약(팩터 데이터)과 독립적으로 진행 가능하다.

## 구현 (Phase 1 — 완료)

이 계약은 `entrypoints/run_factors`로 구현돼 있다.
- **유니버스 도출**: `collect/universe.py`가 `config/factors.yaml`의 인덱스(sp500·nasdaq·dowjones) 현재 구성종목에서 티커를 도출하고(하드코딩 없음), `index_members`·`index_changes`·`delisted`를 적재한다.
- **수집 엔진**: `collect/factors.py`의 선언적 `SPECS`(계약의 per-symbol 컬렉션 SSOT) + 제네릭 엔진이 universe × 스펙을 돌며 shape별(history/asof/snapshot)로 적재한다. 응답은 FMP 스키마 그대로 저장한다.
- **주기**: `run_factors --cadence daily|weekly|all`. `daily`=배당조정 EOD, `weekly`=나머지(재무제표·비율·시총·프로파일·§2 as-of 스냅샷)+유니버스 갱신.
- **store**: 제네릭 `save_docs`/`filter_new_ids_in`(history dedup)·`save_snapshot`이 `expire_at`(수집 시각+30일) TTL을 주입한다.
- 실 FMP + 에뮬레이터 엔드투엔드로 11개 컬렉터 전부 검증(2856 문서/2종목, 오류 0).
