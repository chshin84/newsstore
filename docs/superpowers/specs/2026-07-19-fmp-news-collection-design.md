# FMP 뉴스 수집 — 설계 (2026-07-19)

> 상태: **설계 초안**(구현 전). 브랜치 `data-only-more-feed`. 이 스펙은 **FMP 뉴스 통합 하나**로 좁힌다.
> RSS 대표/테마 피드 확장과 `tipranks.com/news`는 **후속 스펙**으로 분리한다.
> (2026-07-19 3렌즈 독립 리뷰 반영 — grounding·consistency·adversarial + REST 실측.)

## 1. 명분 (왜 수집하나)

다운스트림의 최종 목적은 **일별 뉴스맵**이다 — 매일의 뉴스를 **그래프**로 구축하고, 그 **델타(변화)**를
측정해 **세상에서 부상하는 키워드와 관련 종목**을 찾는다. newsstore는 그 그래프의 원재료(뉴스)를
Point-in-Time으로 모은다.

이 목적에서는 **폭(breadth)이 곧 신호원**이다 — 노이즈가 섞인 소스라도, 그래프의 델타 측정은 **볼륨의
변화**에서 신호를 뽑아낸다. 따라서 저신호 매체를 선별 배제하기보다 넓게 수집하고, 잡음은 비-LLM 분류와
다운스트림 임베딩 델타에 맡긴다.

FMP 뉴스 API는 우리가 RSS로 받지 않는 매체와 **종목 티커가 태깅된** 기사를 대량으로 준다. 핵심 가치는
**종목 태깅**이다(RSS는 기사에서 티커를 추론해야 하지만 FMP는 `symbol`이 박혀 나와 **티커→뉴스 링크가
공짜**). 티커 없는 매크로 뉴스(general·forex·crypto)도 그래프의 **테마·섹터 노드**로서 델타에 기여한다.

## 2. 스코프

**포함** — FMP 뉴스 API의 파이어호스를 기존 수집 파이프라인에 통합한다. **6개 엔드포인트 전부 활성**
(사용자 결정 2026-07-19 "다 해" — 뉴스맵 그래프/델타는 폭이 신호원):

| 활성 엔드포인트(REST 경로) | 레이어 | 매핑 |
|---------------------------|--------|------|
| `news/stock-latest` | 종목(티커 태깅) | 표준 |
| `news/press-releases-latest` | 1차 소스(기업 발표) | 표준 |
| `news/general-latest` | 매크로/세계 | 표준(symbol 빈 경우 많음) |
| `news/forex-latest` | FX·원자재 | 표준 |
| `news/crypto-latest` | 크립토 | 표준 |
| `fmp-articles` | FMP 자체 기사(전문 `content`) | **변형**(§5) |

- **이름 규약(계약)**: REST 경로 이름 `*-latest`를 계약으로 쓴다. (MCP 툴의 `stock-news` 등은 세션 프로빙에
  썼을 뿐 — 2026-07-19 REST 직접 실측으로 `stock-latest`가 동일 파이어호스임을 확인: 두 경로 모두 첫 항목이
  `newsfilecorp.com`류 동일 매체군.)
- **어댑터**: 표준 shape 5종 + `fmp-articles` 변형 1종, 두 매핑을 처리한다.

**제외(후속 스펙)** — RSS 대표/테마 피드 확장(~70개 + `themes.yaml`), `tipranks.com/news` 피드,
FMP TipRanks 애드온(등급·PIT 데이터 — 뉴스가 아니라 별개 유료 데이터).

## 3. 아키텍처 — 별도 수집 패스 (기존 관례 준수)

기존 `prices`·`factors`가 각각 **별도 collect 모듈 + 별도 엔트리포인트 + 별도 Cloud Run 잡**인 것과
동일하게, FMP 뉴스도 **별도 패스**로 둔다.

- **신규**: `collect/fmp_news.py`(파싱·오케스트레이션) + `entrypoints/run_fmp_news.py`(HTTP 배선).
- **재사용은 store 계약뿐**: 산출물을 `RawItem`으로 만들어 `store`에 넘긴다 → 그 뒤(kind 분류·저장·임베딩
  대기 플래그·60일 TTL)는 RSS 뉴스와 동일한 길을 탄다. **주의**: `collector.py`의 `_mark_ok`/`_mark_fail`·
  `is_due`는 그 모듈 내부 함수다. §3은 collector 불침범(SURGICAL)이므로 `fmp_news`는 이들을 **재호출하지
  않고**, `store.set_feed_state`/`store.get_feed_state`를 직접 부르는 얇은 건강 헬퍼를 **재구현**한다.
  (`is_due`의 실제 시그니처는 `is_due(state, poll_minutes, now)` — `now` 필수.)
- **불침범**: 잘 도는 RSS collector(`collect/collector.py`)를 건드리지 않는다.

근거 — FMP 뉴스의 수집 방식(REST·페이지네이션·날짜 lookback·apikey 인증)은 RSS(등장 GET·ETag·feedparser
XML)와 근본적으로 달라, 한 루프에 섞으면 `FeedConfig`(extra=forbid)와 collector가 조건분기로 지저분해진다.

### HTTP 배선(run_prices 관례 그대로)
- `BASE_FMP = "https://financialmodelingprep.com/stable/"`.
- `api_key = os.environ["FMP_API_KEY"]`(없으면 KeyError로 fail-loud).
- `httpx.Client(headers={"apikey": api_key})` — **비밀은 헤더로만**(URL·로그 미노출, SECRETS).
- 엔트리포인트가 `fetchers`(엔드포인트별 GET 함수)를 배선하고, `collect/fmp_news.run_fmp_news_pass()`가
  파싱·오케스트레이션한다.
- **콜 간 지연**: `NEWSSTORE_NEWS_DELAY_S`(env, 기본 0.2s)를 페이지 GET 사이에 둔다(run_prices의
  `NEWSSTORE_PRICE_DELAY_S` 관례 — 레이트리밋 대응).

## 4. 데이터 흐름 (엔드포인트마다) — 고정 LOOKBACK 재스캔

**이동 커서를 쓰지 않는다.** run_prices가 매 실행 무조건 최근 N일을 재스캔해 지각·역순·다운타임을 갭필하는
패턴을 따른다(그쪽 `INTRADAY_LOOKBACK_DAYS=3` 주석: "스케줄러가 잠시 멈춰도 최근 며칠 갭필").

1. `from_date = today - NEWS_LOOKBACK_DAYS`(기본 3), `to_date = today`. **매 패스 이 창을 통째 재스캔**한다.
2. `GET /stable/news/{endpoint}?from={from}&to={to}&limit=250&page=p`, `page`를 0부터 증가시키며 빈 페이지
   또는 `page` 상한(100)까지.
3. 각 JSON 로우 → `RawItem`(§5 매핑).
4. **배치 존재검사 후 신규만 write**(§9 비용) — 이미 저장된 로우는 write 0.

**왜 이동 커서를 버리나(리뷰 A1/C2)**: FMP 파이어호스는 출처별로 **지연·역순 인덱싱**이 흔하다(특히
press-releases). `from=last_fetched`로 커서를 전진시키면, 커서가 지난 뒤 뒤늦게 인덱싱된 과거 기사를
**영구히 놓친다**. 고정 lookback 재스캔은 이 갭을 원천 차단하고, 겹침은 **URL 중복제거로 무-write**다.

**cadence**: `feed_state`의 `is_due(state, poll_minutes, now)`로 트리거, 기본 **하루 1회**
(`NEWS_LOOKBACK_DAYS=3`이 하루 걸러도·다운타임도 덮는다). 더 자주 원하면 config로 조정.

**절단 방어(리뷰 A2)**: page 상한(100)에 도달했는데 마지막 페이지가 가득 차 있으면(=더 있을 개연성)
**절단으로 판정**해 `last_error="truncated at page cap"` + 건강 악화로 기록한다 → 상태 대시보드가
'절단된 엔드포인트'를 본다. (소폭 lookback(3일)에선 하루 수백~수천 건이라 25,000 상한 도달은 사실상
없지만, 조용한 유실을 막는 가드는 둔다.)

## 5. 스키마 매핑 — `RawItem` + `symbol`

`RawItem`에 **옵션 필드 `symbol: str = ""`**를 추가한다(FMP 티커 태깅 보존 — 뉴스맵 종목 노드의 핵심).
`_to_doc`가 이를 `items` 문서에 저장한다. RSS 아이템은 `symbol` 없어 기본값 `""`(하위호환).

**표준 매핑(`*-latest` 5종)** — 필드: `symbol·publishedDate·publisher·title·image·site·text·url`.
- `id = sha1(url)` · `url ← url` · `title ← title` · `body ← text` · `symbol ← symbol`(없으면 `""`) ·
  `published_at ← publishedDate`(§10 tz 확정 후) · `source ← publisher`(or site).

**변형 매핑(`fmp-articles`)** — 필드가 다르다(2026-07-19 REST 실측): `title·date·content·tickers·image·
link·author·site`.
- `url ← link` · `body ← content`(전문 HTML) · `published_at ← date` · `symbol ← tickers`의 첫 티커
  (`"NASDAQ:META"` 형태면 심볼부만) · `source ← site`(="Financial Modeling Prep").

**다중 티커 유실(리뷰 A8 — 의식적 v1 결정)**: 파이어호스는 로우당 티커 하나를 준다. 같은 URL이 여러
티커로 중복 등장하면 URL 중복제거로 한 로우만 남아 **나머지 티커 연결은 유실**되며, 파이어호스는 시간창
데이터라 **나중에 백필 불가(비가역)**다. v1은 단일 티커로 둔다(YAGNI) — 이 유실이 비가역임을 명시해
의식적 결정으로 남긴다. 다중 티커 누적이 필요해지면 `symbols` 리스트 병합으로 확장(후속).

## 6. 중복제거 — 실측 근거

2026-07-19 실측(각 100건, `sha1(url)`로 `items` 존재 검사):

| 샘플(REST `stock-latest`/`general-latest` 동일 파이어호스) | 정확-URL 겹침 | 겹친 출처 |
|------|------|------|
| stock 파이어호스 | **1%** | CNBC |
| general 파이어호스 | **6%** | CNBC |

- 이는 **정확-URL 겹침**(doc id=`sha1(url)`)이라 콘텐츠 겹침의 **하한값**이다. 같은 기사가 다른 URL로 오면
  안 잡힌다(우리 Reuters는 구글뉴스 리다이렉트 URL로 저장돼 `reuters.com` 직링크와 불일치 — 유일 매칭된
  CNBC만 양쪽 `cnbc.com` 직링크).
- 측정은 MCP `stock-news`/`general-news`로 했으나, 2026-07-19 **REST `stock-latest`/`general-latest`를
  직접 프로빙해 동일 shape·동일 매체군(newsfilecorp 등)임을 확인** — 배포 소스와 측정 소스가 같은
  파이어호스다(리뷰 G1 해소).
- 매체 구성이 거의 안 겹친다 — FMP는 Motley Fool·24/7 Wall St·SeekingAlpha·MarketWatch·Barron's·
  GlobeNewsWire/Newsfile 등 우리가 RSS로 안 받는 매체를 대거 가져온다. **FMP 뉴스는 압도적으로 새 콘텐츠**다.

**설계 함의**: URL 중복제거는 교차소스에서 거의 충돌하지 않는다(1~6%). 그 진짜 역할은 **고정 lookback
재스캔(§4)의 멱등성**이다(겹치는 창을 매 패스 재-pull해도 무-write). 교차소스 near-중복(같은 기사·다른
URL)은 URL로 못 잡으며 **다운스트림 임베딩**이 처리한다 — newsstore는 둘 다 저장하고 아래에서 병합한다
(비파괴 우선).

## 7. 분류·필터 (기존 `classify_kind` 재사용)

FMP 파이어호스에 섞인 잡음은 기존 비-LLM 분류기가 이미 처리한다.
- **집단소송 로펌 스팸**(ROSEN "lead plaintiff/class action" 등)은 `contracts/classify.py`의
  `SPAM_SIGNALS`에 **이미 등재**돼 있어 `story`에서 자동 제외된다(실측: FMP stock 파이어호스에 이 스팸 다수
  — 자동 필터됨). **새 규칙 불필요.**
- `general` 파이어호스엔 YouTube 클립(제목만)·SeekingAlpha 오피니언이 다수라 저신호가 섞인다. §1대로
  **폭을 신호원으로 삼아 저장은 하되**, 실제 파이어호스로 분류 결과를 실측해 필요하면 규칙을 보강한다
  (측정 먼저).

## 8. 유니버스 — 전부 저장

종목 뉴스를 티커 상관없이 **전부 저장**한다(추적 2000 유니버스 필터 없음).
- factors 2000 유니버스는 이 레포에 아직 없어 의존을 안 만든다.
- 저장은 60일 TTL로 통제되고, `symbol` 태그로 다운스트림이 필터하며, 생존편향도 없다.

## 9. 비용·시크릿·건강·실패

### 비용 (리뷰 A4·A6 — "멱등≠무비용")
- **배치 존재검사**: `upsert_items`는 아이템마다 `ref.get().exists`(1 read)+`set`(1 write)라, 매 패스
  lookback 창을 재-pull하면 **저장된 대다수에 대해 write 0이어도 read는 파이어호스 총량 비례**로 발생한다.
  → `fmp_news`는 store의 **배치 경로**(`get_all`로 존재검사 = `filter_new_ids` 패턴)로 신규 id만 걸러
  **배치 set(≤500)**한다(read를 아이템 수→라운드트립 수로 축소). 필요시 items용 배치-upsert 메서드를 추가
  (save_bars/save_docs와 동형).
- **임베딩 비용**: 저신호 general이 `story`로 통과하면 `embed_pending`이 붙어 임베딩까지 간다. 사용자
  목적(전 소스 델타)상 임베딩 폭은 **의도된 것**으로 수용한다. (후속 완화 여지: YouTube 등 제목-only 영상을
  별도 kind로 걸러 임베딩 제외 — §12 열린결정.)

### 시크릿·건강
- **시크릿**: `FMP_API_KEY`는 백엔드 전용(env / 클라우드는 Secret Manager). 헤더로만 실어 URL·로그 미노출.
  `prices`/`factors`와 동일 배관(SSOT).
- **feed_state 키(리뷰 C1)**: 엔드포인트마다 **자기 feed_state 문서**를 갖는다 — `feed_id = "fmp:{endpoint}"`
  (예: `"fmp:stock-latest"`). 이 키로 `last_fetched`(is_due 스케줄용)·건강 필드를 저장한다. 키를 안 나누면
  6개가 한 문서를 공유해 서로 덮어쓴다.
- **건강 추적**: 엔드포인트별 `feed_state` 건강 필드(`consecutive_failures`·`last_error`·`last_success`)를
  `store.set_feed_state`로 기록 → 상태 대시보드가 죽은/절단된 엔드포인트를 표면화.

### 실패·레이트리밋 (리뷰 A3)
- **격리**: 한 엔드포인트 실패(HTTP 5xx·402·파싱 예외)가 다른 엔드포인트를 막지 않는다(per-endpoint
  try/except, 다음 패스 재-스캔).
- **429(레이트리밋)**: 페이지 GET 사이 `NEWSSTORE_NEWS_DELAY_S` 지연 + 429 시 짧은 백오프. 페이지네이션
  **도중** 429/에러가 나면 그 엔드포인트 패스를 중단하되 **이미 upsert된 페이지는 커밋 유지**(멱등),
  `mark_fail` 기록. 다음 패스가 같은 lookback 창을 재-스캔하므로 **유실 없음**(URL 중복제거가 재-write 방지).

## 10. gotcha — `publishedDate` 타임존 (코드 불변식으로 강제)

FMP 응답의 `publishedDate`(예: `"2026-07-18 22:45:00"`)·`fmp-articles`의 `date`는 **타임존 표기가 없다**
(2026-07-19 REST 실측 확인). UTC인지 미 동부시간인지 문서·실측으로 **확정한 뒤** 스탬프한다
(market-data-integrity: 받은 시각을 의심하라).
- 확정한 tz 가정을 **상수 + 주석(SSOT)**으로 코드에 박고(예: `FMP_NEWS_TZ`), 파서가 이를 참조한다.
- §12 테스트가 **그 tz 처리 자체를 assert**한다(산문 가드가 아니라 코드 불변식 — 리뷰 A7).
- 완화 요인: `published_at`은 TTL(`expire_at=fetched_at+_TTL`)에 안 쓰여, tz 오류가 저장 만료를 오염시키진
  않는다(심각도 제한).

## 11. Firestore 계약 변화

- **신규 컬렉션 없음** — FMP 뉴스는 기존 `items` 컬렉션에 저장(같은 `RawItem` shape + `symbol`).
- `items` 문서에 **`symbol` 필드 추가**(옵션). `feed_state`에 **`fmp:{endpoint}` 문서** 신설(§9).
- `docs/firestore-contract.md`에 반영(symbol 필드·fmp feed_state 키).
- TTL·kind·embed_pending 계약은 기존 그대로.

## 12. 테스트 (TDD — 불변식, 매직넘버 금지)

- **표준 매핑**: `*-latest` 픽스처 → `symbol`·`url`(중복 basis)·`body(text)`·`published_at` 검증.
  `general`의 `symbol` 빈 값 → `""`.
- **변형 매핑**: `fmp-articles` 픽스처 → `link→url`·`content→body`·`date→published_at`·`tickers[0]→symbol`.
- **tz 불변식(A7)**: `published_at`이 확정 tz로 파싱됨을 assert(가정 자체를 테스트).
- **고정 lookback·멱등**: 겹치는 창 재-pull이 **신규 write 0**(불변식). 커서 전진 없음.
- **배치 존재검사**: 재-pull이 per-item get을 쓰지 않고 배치 경로를 탐(read 상한 성격).
- **feed_state 키**: 각 엔드포인트가 `fmp:{endpoint}` 문서에 독립 기록(서로 안 덮음).
- **분류 통합**: ROSEN 스팸 로우 → `kind==spam`.
- **절단 가드**: page 상한 + 가득 찬 마지막 페이지 → `last_error` 기록.
- **시크릿**: apikey가 로그·URL에 안 남음.
- 기대 개수를 박지 않고 **불변식**으로 검증.

**열린 결정(§12)**: YouTube 제목-only 영상을 별도 kind로 걸러 임베딩 제외할지(저신호 임베딩 비용 A6) —
v1은 story로 두고 실측 후 결정.

## 13. 배포

- **신규 Cloud Run 잡**(prices/factors와 동형): 같은 이미지, `CMD`만 `run_fmp_news`. 스케줄러로 하루 1회.
- FMP 뉴스는 추가 의존 없음(httpx·기존 store). `INSTALL_GCP=true` 이미지 그대로.

## 14. 구현 단계

1. **tz 확정**: `publishedDate`/`date` 타임존을 프로브·문서로 확정 → `FMP_NEWS_TZ` 상수(§10).
2. **스키마**: `RawItem` + `symbol`, `_to_doc` 저장(하위호환 기본값). `firestore-contract.md` 갱신.
3. **매핑**: 표준(`*-latest` ×5) + 변형(`fmp-articles`) JSON→RawItem (TDD §12).
4. **오케스트레이션**: 고정 lookback 재스캔 + 페이지네이션 + **배치 존재검사/write**(§9 비용) +
   **절단 가드**(§4) + 페이지 지연·429 백오프(§9).
5. **건강·격리·커서 키**: 엔드포인트별 `fmp:{endpoint}` feed_state에 `last_fetched`·건강 기록
   (`store.set_feed_state` 직접), per-endpoint try/except 격리(§9).
6. **엔트리포인트·config**: `run_fmp_news.py` HTTP 배선(run_prices 관례) + 활성 엔드포인트 config(§15).
7. **배포**: 신규 Cloud Run 잡 + 스케줄러(하루 1회). `docs/operations.md` 갱신(신규 잡·스케줄).
8. **스모크**: 실 파이어호스로 분류·겹침·tz·절단·비용(read 수) 실측.

## 15. 열린 결정 (사용자 확인)

- **활성 엔드포인트 config 위치**: `feeds.yaml`을 `kind`로 확장할지, 별도 `fmp_news.yaml`을 둘지(분리가
  `FeedConfig`(extra=forbid)를 안 더럽혀 유력).
- **`NEWS_LOOKBACK_DAYS` 기본값**: 3(run_prices 관례)으로 시작 — 다운타임 여유 vs read 비용.
- **비용 vs 폭(리뷰 A5 반대의견 기록)**: adversarial 렌즈는 종목 태그 없는 general·forex·crypto를 v1에서
  빼자고 지적(코어 가치 없이 볼륨·저신호↑). 사용자는 "다 해"(뉴스맵 그래프/델타엔 폭이 신호원)로 **전부
  활성**을 선택 — 비용은 §9 배치 중복제거 + 60일 TTL로 완화. 이 트레이드오프는 사용자 소유 결정으로 남긴다.

<!-- spec-review: passed -->
