# Firestore 데이터 계약 — newsstore

이 문서는 수집 전용 스토어의 컬렉션 스키마와 UI read 계약이다. newsstore는 **수집(collect) 전용**이다 — 뉴스 RSS 수집, 가격·펀더멘털 수집, Firestore 저장, 정적 웹 확인 UI만 있고 분석/LLM 레이어는 없다.

## 컬렉션 개요

| 컬렉션 | writer | reader | TTL(30일) | 비고 |
|---|---|---|---|---|
| `items` | collect Job | web UI | 있음(`expire_at`) | 뉴스 기사 원본 + 수집 시점 `kind` 분류 |
| `feed_state` | collect Job | collect Job | **없음** | etag/last_modified 폴링 커서 — 만료시키면 증분 수집이 어긋난다 |
| `meta` | collect Job | web UI | 없음 | 소스 목록·tier 발행 |
| `prices` | prices Job | web UI | 있음(`expire_at`) | 지수·환율·국채 스냅샷(FMP + Yahoo 폴백) |
| `fundamentals` | fundamentals Job | web UI | 있음(`expire_at`) | 티커별 재무제표(FMP) |

## TTL 규칙 (1개월, 비용 통제)

Firestore TTL은 문서의 타임스탬프 필드를 정책이 가리켜 만료시킨다. 이 스토어의 만료 필드명은 **`expire_at`**로 통일한다.
- **`items`·`prices`·`fundamentals`**: 각 문서에 `expire_at`(= 저장 시각 + 30일)을 넣고, 컬렉션마다 gcloud TTL 정책을 건다(프로비저닝은 `docs/setup.md`·`docs/operations.md`).
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
지수·환율·국채 스냅샷. 문서 키 = 심볼 key(예: `sp500`, `usdkrw`, `us10y`).
- **필드**: `close, change, percent_change, datetime, currency, series, label, symbol, group, order, fetched_at, source, flags, expire_at`.
- **`fetched_at`** (신선도) — 조회 시각. 스케줄러가 조용히 멈춰 낡은 값을 실시간처럼 보여주는 사고를 막는 검문소 필드.
- **`source`** (fmp|fmp_treasury|yahoo) — 이 심볼을 어디서 가져왔는지. 대부분 FMP, 국채는 FMP treasury-rates에서 도출, kosdaq·dxy·wti 3종만 Yahoo 폴백(FMP Premium 미커버).
- **`flags`** (비파괴 상식범위 플래그) — %등락이 상식 밖(지수 ±15%·환율 ±5% 가이드)이면 삭제하지 않고 여기에 표시한다. 검증은 하되 수정은 하지 않는다.
- **`expire_at`** = 저장 시각 + 30일(store 주입).

### `fundamentals` (fundamentals Job이 기록, 공개 read)
티커별 재무제표(FMP). 문서 키 = 티커 심볼(예: `AAPL`).
- **필드**: `income[], balance[], cashflow[], fetched_at, expire_at`. 각 배열은 annual·최근 5개.
- **`fetched_at`** (신선도) — 조회 시각.
- **`expire_at`** = 저장 시각 + 30일(store 주입).

## Store 표면 (`firestore_store.FirestoreStore`)
- `upsert_items(items) -> int` — `_to_doc`가 `kind` 분류 + `expire_at`을 박는다.
- `get_feed_state`, `set_feed_state`, `count`, `filter_new_ids`, `set_meta`.
- `save_price(key, data)`, `get_price(key)` — TTL(`expire_at`) 주입.
- `save_fundamental(symbol, data)`, `get_fundamental(symbol)` — TTL 주입.
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
