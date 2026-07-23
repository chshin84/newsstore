# Firestore 데이터 계약 — newsstore

이 문서는 뉴스 수집 전용 스토어의 컬렉션 스키마와 UI read 계약이다. newsstore는 **뉴스 수집(collect) 전용**이다 — 뉴스 RSS 수집(RSS + FMP 뉴스), Firestore 저장, 정적 웹 확인 UI만 있고 분석/LLM 레이어는 없다. (FMP 팩터·가격 수집은 별개 로컬 레포 `DB-news-data`(DuckDB)로 이관됐다.)

## 컬렉션 개요

| 컬렉션 | writer | reader | TTL(60일) | 비고 |
|---|---|---|---|---|
| `items` | collect Job | web UI | 있음(`expire_at`) | 뉴스 기사 원본 + 수집 시점 `kind` 분류 |
| `feed_state` | collect Job | collect Job | **없음** | etag/last_modified 폴링 커서 — 만료시키면 증분 수집이 어긋난다 |
| `meta` | collect Job | web UI | 없음 | 소스 목록·tier 발행 |
| `item_vectors` | collect Job(임베딩 패스) | 공개(다운스트림) | 있음(`expire_at` — **원본 item 미러링**) | story 기사 임베딩 벡터(768차원) — 기사와 함께 만료 |
| `job_health` | collect_all 통합 Job | web UI(대시보드) | 없음 | 잡별 최근 실행 상태(조용한 실패 감지) |

## TTL 규칙 (2개월, 비용 통제)

Firestore TTL은 문서의 타임스탬프 필드를 정책이 가리켜 만료시킨다. 이 스토어의 만료 필드명은 **`expire_at`**로 통일한다.
- **`items`**: 각 문서에 `expire_at`(저장 시각 + 60일)을 넣고, gcloud TTL 정책을 건다(프로비저닝은 `docs/setup.md`·`docs/operations.md`).
- **`feed_state`엔 `expire_at`을 절대 넣지 않는다.** ETag·커서가 만료되면 증분 수집이 매번 전량 재수집으로 어긋난다.
- **`item_vectors`는 원본 item의 `expire_at`을 그대로 미러링**한다(기사와 벡터가 함께 만료 — 고아 벡터 방지). 이 컬렉션만 호출자(임베딩 패스)가 원본에서 읽은 값을 전달하고, `embed_model`·`embedded_at`은 store가 주입한다.
- `expire_at` 주입은 store가 단일 통제점이다(`firestore_store.py`). 호출자가 안 넣어도 store가 보장한다.

## 컬렉션 스키마

### `items` (collect가 기록, 공개 read)
- **필드**: `feed_id, source, asset_hint, language, url, title, body, published_at, fetched_at, kind, expire_at`.
- 모델 SSOT는 `src/newsstore/contracts/models.py`의 `RawItem`.
- **`kind`** (story|spam|digest|sports) — 수집 시점 선분류. `_to_doc()`가 `upsert_items` 시점에 `classify_kind(title, body)`를 호출해 박는다(SSOT: `src/newsstore/contracts/classify.py`의 SPAM/SPORTS/DIGEST 키워드). web UI는 `kind === "story"`만 노출하고 나머지는 숨긴다. LLM이 아니라 순수 키워드 규칙 필터다.
- **`expire_at`** = `fetched_at + 60일`. TTL 정책이 이 필드를 보고 만료시킨다.

### `feed_state` (수집기 전용, 비공개)
폴링 캐시(`etag, last_modified, last_fetched`). **`expire_at` 없음**(위 TTL 규칙).

### `meta` (collect가 기록, 공개 read)
사이트용 소형 메타 문서(예: `sources`). 소스 목록과 **소스 tier**를 여기로 발행한다(아래 §공유 설정).

### `item_vectors` (collect Job의 임베딩 패스가 기록, 공개 read)
story 기사당 벡터 1문서. 문서 키 = item id. **분석이 아니라 수집 시점 1회 계산**이다(생성형 LLM 아님 — 스코프 예외).
- **필드**: `vector`(float×768), `embed_model`("gemini-embedding-001" — store가 SSOT 주입), `embedded_at`, `expire_at`(원본 미러링).
- **임베딩 입력 규칙(계약)**: `title + " " + body[:500]`. 모델·차원과 함께 다운스트림 계약이다 — 유사도 검색 쿼리도 같은 모델·차원·규칙으로 임베딩해야 한다. 상수 SSOT: `src/newsstore/contracts/embedding.py`.
- **모델 교체는 단방향 문**: 다운스트림이 이 계약에 의존하면 교체 시 전량 재임베딩 + 다운스트림 협응이 필요하다. `embed_model` 필드가 mismatch 감지 수단.

### `items.embed_pending` (transient 플래그)
`_to_doc`가 story에만 `embed_pending: true`를 박고, 임베딩 패스가 완료 시 `DELETE_FIELD`로 걷는다(항목 귀속 영구 실패 — 빈 입력·400 — 도 처분 시 걷는다; 좀비 재시도 방지). Firestore가 "필드 없음"을 쿼리할 수 없어 플래그 존재 = 대기를 뜻한다. **공개 read인 items에 임베딩 전까지 노출되는 백엔드 상태 필드**다 — 경미한 노출은 수용 결정(웹 파서는 미지 필드 무시).

### FMP 뉴스(2026-07-19)
- `items` 문서에 `symbol`(옵션, str) 추가 — FMP 뉴스의 티커 태깅. RSS 아이템은 "".
- `feed_state`에 `fmp:{endpoint}` 문서 — FMP 뉴스 엔드포인트별 is_due 스케줄·건강(커서 아님, 고정 lookback).
- 신규 컬렉션 없음(기존 items 재사용). TTL·kind·embed_pending 계약 동일.

### `job_health` (collect_all 통합 Job이 기록, 공개 read)
잡별 최근 실행 상태 1문서(문서 키 = 잡 key, 예: `collect_all`). 대시보드(`web/dashboard.html`)가 읽어 조용한 실패·멈춤·미실행을 표시한다(operations §G).
- **필드**: `last_status`(예: ok|running|fail), `fetched_at`(마지막 실행 기록 시각), `detail`(옵션 요약 문자열). **`expire_at` 없음**(상태 문서라 만료 불요).

## Store 표면 (`firestore_store.FirestoreStore`)
- `upsert_items(items) -> int` — `_to_doc`가 `kind` 분류 + `expire_at`을 박는다.
- `get_feed_state`, `set_feed_state`, `count`, `filter_new_ids`, `set_meta`.
- `get_pending_embed_items(limit)`, `save_vectors(entries)`, `clear_embed_pending(ids)` — 임베딩 대기 큐·벡터 저장(원자 batch + 만료 격리)·영구 실패 처분. 타입 계약은 `contracts/ports.py`의 `PendingItem`·`VectorEntry`.
- `close`/`__enter__`/`__exit__`.

## 필터 (비-LLM 규칙, 수집 경로에 배선됨)
저장 전에 원본을 버리지 않는다(비파괴). 대신 수집 시점에 분류·중복 제거만 한다.
- **dedup**: `parser.py`(link→guid→title url 기반) + `store.filter_new_ids` + `upsert_items`(이미 있으면 미덮어씀).
- **kind 분류**: `_to_doc`가 `classify_kind`로 spam/sports/digest를 라벨링 → UI가 story만 노출.
- **본문 수집**: `collect/body_fetch.py`의 `enrich_bodies`는 화이트리스트 소스의 기사 페이지를 HTTP로 fetch해 본문을 채운다(LLM 아님).

## 불변식 (계약 테스트로 강제 — FAIL-LOUD)
구두 약속이 아니라 테스트로 지킨다.
- **kind stamp** — `upsert_items` 시점에 모든 item이 `kind`를 갖는다(수집 시점 분류). web UI의 story 필터가 여기에 의존한다.
- **스키마 드리프트 가드** — web UI가 읽는 필드명(items의 `source`·`kind` 등)이 바뀌면 터지는 계약 테스트. 이름이 조용히 어긋나면 사이트가 빈 화면이 된다.
- **feed_state에 `expire_at` 부재** — TTL이 폴링 커서를 만료시키지 않음을 지킨다.

## 인프라
- **전면 공개 read 보안규칙** (`firestore.rules`, `docs/operations.md §C`): 대시보드·뉴스 리더가 **로그인 없이** 최근 데이터를 본다. `items`·`meta`·`item_vectors`·`job_health` 모두 `allow read: if true`. **write는 전면 금지**(수집기는 Admin SDK라 규칙 우회). 공개해도 노출은 **60일 버퍼**에 한정된다(깊은 아카이브는 다운스트림 로컬 DB 몫이라 Firestore 밖). `feed_state`(폴링 커서)만 기본 거부.
  - **복합 인덱스** (§D). TTL 정책 프로비저닝은 `docs/setup.md`·`docs/operations.md`.
- 비밀(`FMP_API_KEY`·`GEMINI_API_KEY`)은 백엔드 전용(SECRETS) — 클라이언트/커밋 금지.

## 공유 설정
- **`config/feeds.yaml`의 `tier` 필드** — `feeds.yaml`은 수집기 SSOT다. 수집 패스가 `meta/sources`에 `{"sources":[...], "tiers":{source: tier}}`로 발행한다. UI는 거기서 소스 등급을 읽는다. 파일을 복제하지 않는다(SSOT).
