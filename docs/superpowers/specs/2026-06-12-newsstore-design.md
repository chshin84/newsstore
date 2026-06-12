# newsstore — 설계 문서 (MVP)

작성일: 2026-06-12
상태: 설계 확정 대기 (검토 후 구현계획으로 진행)

---

## 1. 목표와 범위

자산운용(개인, 외부 프로젝트) 목적의 **24/7 금융뉴스 수집·태깅 파이프라인**.

- **수집**: 한·미 주식, 크립토, FX, 한·미 채권 + 원자재·매크로·정책, 그리고 트럼프 원문·루머·경제지표를 무료 소스로 폭넓게 수집.
- **처리**: 매시간 직전 수집분을 Gemini(Flash)로 **중요도 평가 + 태깅**.
- **저장**: 쿼리 가능한 저장소(Firestore)에 적재.

**MVP 정의**: 수집 → 태깅 → 저장(쿼리 가능)까지. 알림·대시보드·리포트·BigQuery 분석은 범위 밖.

### 비목표 (MVP 제외)
- 중요도 알림(푸시), 대시보드/UI, 정기 다이제스트, BigQuery 분석
- 유료 데이터 피드, Google News 본문 디코딩, 피드가 안 주는 기사 본문의 무리한 스크래핑

---

## 2. 아키텍처

GCP 매니지드 서버리스. **수집과 처리를 분리**(핵심 내결함성 원리: RSS는 백필 불가 → 받자마자 raw에 저장해 durable buffer로 삼고, 무거운 LLM 처리는 별도).

```
Cloud Scheduler ─(5분)─> Collector (Cloud Run)
                           · 피드별 next_due 체크 → 받을 것만 조건부 GET(ETag)
                           · 파싱 → id(url해시)로 raw upsert (중복 스킵)
                           · 실패 시 백오프, 폴링 예의 준수
                           ↓
                         Firestore: raw  (durable buffer)
                           ↓
Cloud Scheduler ─(1시간)─> Processor (Cloud Run)
                           · raw where processed=false 배치 조회
                           · 근접중복 클러스터링
                           · Gemini Flash 구조화 태깅(JSON)
                           ↓
                         Firestore: news  (쿼리 대상)
```

별도 커넥터:
- **경제캘린더 Collector** (Cloud Run, 30분): TradingView 공개 엔드포인트 → `econ_events` 컬렉션 upsert.

### 런타임 / 인프라
- 컨테이너: Python 3.12.
- **환경 분리 `APP_ENV=office|home`** (`.env`로 지정 — 모든 infra가 이 값을 따른다):
  - `office`(회사·ePrism 프록시): 루트 CA `ePrism-SSL-ROOT-CA.crt`를 이미지에 주입(update-ca-certificates → `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE`/`CURL_CA_BUNDLE`), HTTP `verify=`그 경로.
  - `home`(집·프록시 없음): 인증서 불필요, `verify=True`(기본 CA 번들).
  - `infra/Dockerfile`은 **인증서 파일이 있을 때만 설치**하도록 조건부 처리 → office/home 동일 이미지로 빌드(집엔 .crt 없음). `utils/ssl_config.py`가 `APP_ENV` 기준으로 분기.
  - `ePrism-SSL-ROOT-CA.crt`·`.env`는 **git 제외**(`.gitignore`). GCP 배포(서울 리전)는 프록시 밖이라 `office`가 아닌 기본 검증으로 동작.
- 배포 리전: **asia-northeast3 (서울)** 우선 — 한국 IP가 인포맥스 등 한국 소스 접근에 유리(§7 미해결 항목 참조).
- Cloud Scheduler가 Collector/Processor 트리거. Firestore 동일 리전.
- 시크릿(Gemini API key 등): Secret Manager.
- HTTP: 브라우저 User-Agent, timeout 60~90s(사내 프록시 첫 연결 지연 대비).

### 예산
~$200/월. 실제 지출은 Gemini Flash(수십 달러)+Firestore(거의 무료) 정도. 데이터는 전부 무료 RSS/공개 엔드포인트라 $0.

---

## 3. 소스 레지스트리

각 피드 = 설정 항목: `feed_id, url, source, asset_hint, language, poll_interval, body_mode`.
`body_mode`: `full`(피드에 전문) / `summary`(피드 요약으로 충분) / `headline`(제목만) / `calendar`(구조화 데이터).
폴링주기는 측정된 **시간깊이** 기반(고볼륨일수록 짧게). 미국 장중(KST 22:30~05:00) 재측정으로 튜닝.

### 한국 — 연합인포맥스 (lang: ko, body: summary ~270–300자; 필요시 `#article-view-content-div` 스크래핑)
| feed_id | url | asset_hint | poll |
|---|---|---|---|
| infomax_bond_fx | /rss/S1N16.xml | kr_bond, kr_fx | 60m |
| infomax_stock | /rss/S1N2.xml | kr_stock | 60m |
| infomax_overseas | /rss/S1N21.xml | us_stock(ko) | 60m |
| infomax_intl | /rss/S1N23.xml | global, macro | 60m |
| infomax_policy | /rss/S1N15.xml | kr_macro, policy | 60m |

(베이스 URL `https://news.einfomax.co.kr`. 카테고리 피드가 전체피드보다 깊어 60분 안전.)

### 미국 주식·크립토·원자재 — Benzinga (lang: en, body: summary 600–3200자, 스크래핑 불필요. /feed는 안티봇 영향 없음)
| feed_id | path | asset_hint | poll |
|---|---|---|---|
| bz_news | /news/feed | us_stock | 5m |
| bz_markets | /markets/feed | us_market | 5m |
| bz_movers | /movers/feed | us_stock | 5m |
| bz_crypto | /markets/cryptocurrency/feed | crypto | 60m |
| bz_commodities | /markets/commodities/feed | commodity | 60m |
| bz_bonds | /markets/bonds/feed | us_bond | 60m (저볼륨) |
| bz_futures | /markets/futures/feed | futures | 60m |
| bz_earnings | /news/earnings/feed | us_stock, earnings | 60m |
| bz_ma | /news/m-a/feed | m&a | 60m |
| bz_ipos | /news/ipos/feed | ipo | 60m |
| bz_insider | /news/insider-trades/feed | insider | 60m |
| bz_ai | /topic/ai/feed | theme_ai | 60m |

(베이스 `https://www.benzinga.com`. 모든 Benzinga 피드 15개 캡 → 고볼륨(news/markets/movers)은 5분.)

### 크립토 전용 (lang: en, body: summary, 기사 스크래핑 가능)
| feed_id | url | poll |
|---|---|---|
| coindesk | https://www.coindesk.com/arc/outboundfeeds/rss/ | 60m |
| cointelegraph | https://cointelegraph.com/rss | 60m |

### FX · 금리/중앙은행 (lang: en)
| feed_id | url | asset_hint | body | poll |
|---|---|---|---|---|
| forexlive | https://www.forexlive.com/feed/news | fx | full(3600자) | 60m |
| forexlive_cb | https://www.forexlive.com/feed/centralbank | rates, central_bank | full(2800자) | 60m |
| fxstreet | https://www.fxstreet.com/rss/news | fx | summary | 30m (고볼륨) |
| investing_fx | https://www.investing.com/rss/news_1.rss | fx | summary | 60m |

### 미국 채권·매크로·정책 (lang: en)
| feed_id | url | asset_hint | body | poll |
|---|---|---|---|---|
| fed | https://www.federalreserve.gov/feeds/press_all.xml | us_policy | summary | 60m |
| ecb | https://www.ecb.europa.eu/rss/press.html | eu_policy | summary | 60m |
| investing_bonds | https://www.investing.com/rss/bonds.rss | us_bond | summary, **타임스탬프 없음** | 60m |
| gnews_macro_reuters | news.google.com/rss/search?q=site:reuters.com+(inflation OR economy OR Fed)+when:12h | macro | headline | 30m |
| gnews_macro_ap | news.google.com/rss/search?q=site:apnews.com+(economy OR inflation OR Fed)+when:12h | macro | headline | 30m |
| gnews_bonds | news.google.com/rss/search?q="treasury yields" OR "bond market"+when:12h | us_bond | headline | 30m |

### 특수 소스
| feed_id | url/endpoint | asset_hint | body | poll | 비고 |
|---|---|---|---|---|---|
| trump_truth | https://trumpstruth.org/feed | trump, policy | full(원문) | 5–15m | 3rd-party·노이즈 큼 → LLM 관련성 필터 |
| axios | https://www.axios.com/feeds/feed.rss | policy, scoop | summary | 60m | 정치 비중↑ → LLM 필터 |
| gnews_rumor | news.google.com/rss/search?q=(reportedly OR "in talks" OR considering OR "sources say")+(stock OR merger OR acquisition OR raise)+when:12h | rumor | headline | 30m | "카더라"·M&A 스쿱 |
| tv_calendar | https://economic-calendar.tradingview.com/events?from=..&to=..&countries=US | econ_data | calendar(forecast/actual/previous) | 30m | 비공식 위젯 API, Origin/Referer 헤더 필요 |

(Google News 쿼리의 hl/gl/ceid=en-US 파라미터 생략 표기. 실제 URL은 구현 시 완성.)

---

## 4. 수집 설계 (Collector)

- **트리거**: Cloud Scheduler 5분. 각 feed의 `next_due`(= last_fetched + poll_interval) 도래분만 GET.
- **조건부 GET**: 저장된 ETag/Last-Modified로 `If-None-Match`/`If-Modified-Since` → 304면 스킵(예의·비용절감).
- **dedup**: 문서 id = `sha1(정규화된 url 또는 guid)`. raw에 이미 있으면 스킵(upsert, 덮어쓰지 않음).
- **타임스탬프**: 전부 **UTC**로 정규화 저장. `published_at` 없으면(예: investing_bonds) null → `fetched_at`으로 대체, dedup은 url 기준.
- **빈 피드/0건**: 정상 흐름으로 처리(에러 아님).
- **백오프**: 4xx/5xx·타임아웃 시 지수 백오프, 연속 실패 임계 초과하면 헬스 알림.
- **고볼륨 캡 대응**: Benzinga 등 15개 캡 피드는 5분 폴링 + dedup으로 누락 최소화(극단적 속보장의 잔여 누락은 무료 RSS 구조적 한계로 수용).

### 경제캘린더 커넥터
- TradingView 엔드포인트를 30분마다 호출(헤더: Origin/Referer = tradingview.com).
- 이벤트 id = `sha1(country+indicator+period)`. `econ_events`에 upsert(actual/forecast 갱신 반영 위해 덮어쓰기 허용).

---

## 5. 처리·태깅 (Processor) — 런타임에서 Gemini 적극 활용

Gemini를 런타임 핵심 엔진으로 **두 단계**로 쓴다.

### (A) 개별 태깅 — 매시간, 소배치
- **트리거**: Cloud Scheduler 1시간. **입력**: `raw where processed=false`.
- **근접중복 제거**: 제목 정규화·유사도(토큰 자카드/심해시)로 클러스터링 → 대표 1건만 LLM 투입. 군집 멤버는 대표에 연결.
- **소배치(10~50건)** 단위로 Gemini Flash 호출, **구조화 출력(JSON 강제)**. 다국어(ko/en) 그대로.
  - *대량 컨텍스트에 한꺼번에 안 넣는 이유*: 정확도(중간 항목 누락 'lost-in-the-middle')와 구조화출력 안정성. 새 항목만 태깅하므로 큰 컨텍스트가 애초에 불필요.
- **출력**: `news`(카드) + `news_body`(본문)에 기록, 원본 raw `processed=true`.

### (B) 집계 리뷰 — 카드만으로, 필요 시
- "오늘 top 20", "테마 클러스터", "이 루머가 여러 소스에서 교차 확인되나" 같은 **횡단 분석**은 본문이 아닌 **압축 카드**만 모아 Gemini에 투입.
- 1만 카드(~1M 토큰)를 한 컨텍스트에 넣는 건 Gemini Flash 큰 컨텍스트로 *가능은 하나 한계선*. **기본 전략 = `importance`로 선필터 + 계층적(map-reduce) 요약**(배치별 요약→종합). §6 카드/본문 분리가 이를 가능케 함.

### 태깅 스키마 (JSON)
```json
{
  "importance": 1,                // 1~5 (5=시장 강한 영향)
  "asset_class": "us_stock",      // kr_stock|us_stock|crypto|fx|kr_bond|us_bond|commodity|macro|policy|rumor|other
  "topics": ["fed", "inflation"], // 자유 토픽 태그
  "tickers": ["AAPL"],            // 추출된 티커(없으면 [])
  "region": "US",                 // KR|US|Global
  "event_type": "data_release",   // earnings|m&a|rate_decision|data_release|geopolitical|rumor|guidance|other
  "language": "en",               // ko|en
  "market_relevant": true         // 노이즈(trump_truth/axios 정치잡담) 필터용
}
```

---

## 6. 데이터 모델 (Firestore)

**컬렉션 `raw`** — doc id = url해시
```
source, feed_id, asset_hint, url, title, body, published_at(UTC|null),
fetched_at(UTC), language, etag?, processed(bool), dup_of?(대표 id)
```

뉴스는 **[카드] + [본문] 분리** 저장. 카드는 가볍게 유지해 수천~만 건을 Gemini 컨텍스트에 넣을 수 있게 하고, 본문은 별도 컬렉션에 두어 카드 조회가 무겁지 않게 한다(Firestore는 문서 단위 읽기 → 본문을 같은 문서에 두면 카드 쿼리마다 본문까지 끌려옴).

**컬렉션 `news`** (카드, 압축) — doc id = url해시 (raw와 동일 id)
```
headline, summary_short(≤200자), asset_class, topics[], tickers[], region,
event_type, importance(1~5), market_relevant, language,
source, published_at(UTC), tz_original, fetched_at, tagged_at, model, has_body
```

**컬렉션 `news_body`** (본문) — doc id = url해시 (동일)
```
url, body(전문/요약 원문), raw_html?
```

**컬렉션 `econ_events`** — doc id = country+indicator+period 해시
```
country, indicator, period, actual, forecast, previous, release_time(UTC),
surprise(=actual-forecast, 계산), fetched_at
```

**주요 쿼리(예)**: `asset_class == 'us_bond' AND importance >= 4 AND tagged_at >= T`,
`tickers array-contains 'AAPL'`, `event_type == 'rate_decision'`.
필요한 복합 쿼리는 Firestore 복합 인덱스 정의.

---

## 7. 미해결 항목 / 리스크

1. **(중요) GCP egress IP ↔ 한국 소스**: 오늘 모든 검증은 *사내망 한국 IP* 기준. 인포맥스는 자동 fetcher(WebFetch)를 차단한 전력이 있음. **배포 전 GCP 서울 리전 egress에서 인포맥스 GET이 되는지 반드시 검증.** 막히면 대안: 사내망/한국 VM 러너, 한국 IP 프록시.
2. **Google News = 제목만**: 본문 디코딩 비현실적(protobuf+batchexecute 취약, 게다가 소스가 직접 접근 차단). 매크로 본문은 ForexLive/Fed/ECB로 충족 → Google News는 헤드라인 breadth 레이어로만 사용.
3. **investing_bonds 타임스탬프 없음**: url dedup + fetched_at 대체.
4. **3rd-party/비공식 소스 수명**: `trumpstruth.org`, TradingView 엔드포인트는 예고 없이 변경/중단 가능 → 각 소스를 **커넥터 인터페이스 뒤로 격리** + 헬스 알림으로 조기 감지.
5. **Benzinga 15건 캡 + 장중 볼륨**: 고볼륨 피드 5분 폴링. 장중 재측정으로 폴링주기 튜닝.
6. **예의**: 조건부 GET/ETag·백오프·합리적 주기로 피드 차단 예방.

---

## 8. 검증 근거 (스파이크)

`scripts/`의 일회용 검증 스크립트로 본 설계의 모든 가정을 실측(2026-06-12, 한국 IP·Docker):
`crawl_test`(인포맥스 본문/ePrism), `rss_probe`·`depth2`(피드 작동·시간깊이), `benzinga_*`(카테고리 전수·볼륨·본문), `coverage_test*`(FX/채권/매크로 헤드라인), `sample_harvest`(버킷별 실제 본문), `gnews_decode`(디코딩 불가 확인), `trump_coverage`(트럼프·trumpstruth.org), `extra_coverage`(Axios·루머), `econ_calendar`(TradingView 무료 확인). 검증 후 삭제 가능.

---

## 9. 향후(범위 밖, 참고)
중요도 알림(텔레그램/메일), 대시보드, 조간 다이제스트, BigQuery 분석 내보내기, 유료 피드(Benzinga API 등) 보강.
