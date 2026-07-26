# Firestore 데이터 계약 — newsstore

이 문서는 뉴스 수집 전용 스토어의 컬렉션 스키마와 UI read 계약이다. newsstore는 **뉴스 수집(collect) 전용**이다 — 뉴스 수집(RSS + 네이버 검색 뉴스 + FMP 뉴스), Firestore 저장, 정적 웹 확인 UI만 있고 분석/LLM 레이어는 없다. (FMP 팩터·가격 수집은 별개 로컬 레포 `DB-news-data`(DuckDB)로 이관됐다.)

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
- **`item_vectors`는 원본 item의 `expire_at`을 그대로 미러링**한다(기사와 벡터가 함께 만료 — 고아 벡터 방지). 이 컬렉션만 호출자(임베딩 패스)가 원본에서 읽은 값을 전달하고, `embed_model`·`embed_task_type`·`embedded_at`은 store가 주입한다.
- `items`의 `expire_at`은 store가 단일 통제점으로 박는다(`firestore_store.py`의 `_to_doc`). 호출자가 안 넣어도 store가 보장한다. **`item_vectors`는 예외로 호출자가 넘긴 원본 값을 그대로 통과시킨다**(미러링이 목적이라 store가 새로 계산하지 않는다) — 원본에서 읽은 값을 넘기는 책임은 임베딩 패스에 있다.

## 컬렉션 스키마

### `items` (collect가 기록, 공개 read)
- **필드**: `feed_id, source, asset_hint, language, url, title, body, symbol, published_at, fetched_at, kind, expire_at`. story 문서에는 여기에 transient 플래그 `embed_pending`이 임베딩 전까지 더 붙는다(아래 별도 절).
- **문서 키**: `sha1(url)`의 hex다(URL이 없으면 guid, 그것도 없으면 title로 폴백 — `collect/feeds.py`의 `make_id`). 같은 URL은 같은 문서라 재수집해도 덮어쓰지 않는다(비파괴).
- 모델 SSOT는 `src/newsstore/contracts/models.py`의 `RawItem`.
- **`kind`** (story|spam|digest|sports) — 수집 시점 선분류. `_to_doc()`가 `upsert_items` 시점에 `classify_kind(title, body)`를 호출해 박는다(SSOT: `src/newsstore/contracts/classify.py`의 SPAM/SPORTS/DIGEST 키워드). web UI는 `kind`가 `"story"`인 기사와 **`kind` 필드가 아예 없는 기사**를 노출하고 나머지는 숨긴다(`web/index.html`의 `keepInFeed`). 분류 이전의 레거시 문서를 fail-soft로 계속 보여주려는 의도된 선택이다. LLM이 아니라 순수 키워드 규칙 필터다.
- **`expire_at`** = `fetched_at + 60일`. TTL 정책이 이 필드를 보고 만료시킨다.

### `feed_state` (수집기 전용, 비공개)
폴링 커서(`etag, last_modified, last_fetched`)와 피드 건강(`last_success, consecutive_failures, last_error, last_error_at`)을 함께 담는다. 건강 필드는 만성 죽음 판정(`entrypoints/_health.py`의 `CHRONIC_DEAD_STREAK`)에 쓰여 잡의 성공 여부를 가른다. **`expire_at` 없음**(위 TTL 규칙).

### `meta` (collect가 기록, 공개 read)
사이트용 소형 메타 문서(예: `sources`). 소스 목록과 **소스 tier**를 여기로 발행한다(아래 §공유 설정).

### `item_vectors` (collect Job의 임베딩 패스가 기록, 공개 read)
story 기사당 벡터 1문서. 문서 키는 item id와 같다(위 `items`의 문서 키 규칙을 그대로 따른다). **분석이 아니라 수집 시점 1회 계산**이다(생성형 LLM 아님 — 스코프 예외).
- **필드**: `vector`(float×768), `embed_model`("gemini-embedding-001" — store가 SSOT 주입), `embed_task_type`("RETRIEVAL_DOCUMENT" — store가 SSOT 주입), `embedded_at`, `expire_at`(원본 미러링).
- **`vector`의 저장 타입은 평범한 double 배열이다 — Firestore 네이티브 벡터 타입이 아니다(의도된 선택).** 그래서 이 컬렉션에는 `find_nearest`(KNN)를 쓸 수 없고 벡터 인덱스도 걸 수 없다. 유사도 검색은 다운스트림(`DB-news-data`)이 벡터를 당겨가 거기서 계산한다는 것이 이 저장소의 경계이며, 배열이 그쪽에서 다루기 가장 단순하기 때문이다. Firestore 안에서 KNN을 돌리기로 방침이 바뀌면 저장 타입을 네이티브 벡터로 바꾸고 벡터 인덱스를 걸어야 하는데, **이는 모델 교체와 같은 단방향 문이다** — 다운스트림 파서를 함께 고쳐야 하고 TTL이 한 바퀴 돌 때까지 두 타입이 섞인다.
- **임베딩 입력 규칙(계약)**: `title + " " + body[:500]`. 모델·차원과 함께 다운스트림 계약이다 — 유사도 검색 쿼리도 같은 모델·차원·규칙으로 임베딩해야 한다. 모델명·차원·task_type 상수의 SSOT는 `src/newsstore/contracts/embedding.py`이고, 입력 조립과 본문 절단 상수(`BODY_CAP`)는 `src/newsstore/embed/embedder.py`의 `embed_text`에 있다.
- **`task_type`은 모델·차원과 동급의 계약이다.** 같은 문장이라도 task_type이 다르면 다른 벡터가 나온다. 저장 문서는 `RETRIEVAL_DOCUMENT`로 임베딩하므로, **다운스트림은 질의를 `RETRIEVAL_QUERY`로 임베딩해야 짝이 맞는다.** 문서끼리의 중복 접기와 군집에 쓸 때는 저장된 `RETRIEVAL_DOCUMENT` 벡터를 그대로 비교하면 된다.
- **`RETRIEVAL_DOCUMENT`를 고른 근거는 실측이다**(2026-07-26, 실 저장 기사 표본). 다운스트림 용도가 중복 접기와 군집이라 이름만 보면 `SEMANTIC_SIMILARITY`나 `CLUSTERING`이 맞아 보이지만, 재보니 반대였다. 중복 쌍(다른 매체가 쓴 같은 사건)과 무관 쌍을 가르는 AUC가 `RETRIEVAL_DOCUMENT` 1.000(마진 0.256), `SEMANTIC_SIMILARITY` 1.000(마진 0.180), `CLUSTERING` 0.967(마진 0.176)로 나왔다. 뒤 둘은 유사도 값을 잘 맞추도록 훈련되어 공간이 압축되는 탓에 무관한 기사 쌍조차 0.77 언저리로 뜨고, `CLUSTERING`은 완벽 분리에 실패했다. 임계값으로 접고 가르는 용도에는 넓게 퍼진 공간이 유리하며, **과병합이 이 도메인의 알려진 실패 모드라 마진이 곧 안전 여유다.**
- **`vector`는 정규화되어 있지 않다(L2 norm 약 0.59).** 3072차원 단위 벡터를 `output_dimensionality`로 768까지 잘라내면 길이가 1보다 작아지기 때문이다. 문서 간 편차는 2% 안쪽이라 코사인 유사도는 영향을 받지 않지만, **내적을 코사인 대신 쓰거나 절대 거리 임계값을 쓰는 소비자는 직접 정규화해야 한다.**
- **모델·task_type 교체는 단방향 문**: 다운스트림이 이 계약에 의존하면 교체 시 전량 재임베딩 + 다운스트림 협응이 필요하다. `embed_model`·`embed_task_type` 두 필드가 mismatch 감지 수단이며, **전량 재임베딩 경로는 `entrypoints/run_backfill_embed`다** — 그 스크립트는 현행 계약과 어긋나는 벡터를 '없음'으로 보고 다시 마킹한다.

### `items.embed_pending` (transient 플래그)
`_to_doc`가 story에만 `embed_pending: true`를 박고, 임베딩 패스가 완료 시 `DELETE_FIELD`로 걷는다(항목 귀속 영구 실패 — 빈 입력·400 — 도 처분 시 걷는다; 좀비 재시도 방지). Firestore가 "필드 없음"을 쿼리할 수 없어 플래그 존재 = 대기를 뜻한다. **공개 read인 items에 임베딩 전까지 노출되는 백엔드 상태 필드**다 — 경미한 노출은 수용 결정(웹 파서는 미지 필드 무시).

### FMP 뉴스(2026-07-19)
- `items` 문서에 `symbol`(옵션, str) 추가 — FMP 뉴스의 티커 태깅. RSS 아이템은 "".
- `feed_state`에 `fmp:{endpoint}` 문서 — FMP 뉴스 엔드포인트별 **건강만** 기록한다(커서도 스케줄도 아니다 — 매 실행이 고정 lookback을 재스캔한다).
- 신규 컬렉션 없음(기존 items 재사용). TTL·kind·embed_pending 계약 동일.

### 네이버 검색 뉴스
- `feed_state`에 `naver:{query}` 문서 — 활성 쿼리별 건강만 기록한다. 커서가 없다(네이버 검색 API는 ETag·증분을 주지 않고, 중복 제거는 `upsert_items_batched`의 존재검사가 맡는다).
- 신규 컬렉션 없음(기존 `items` 재사용). TTL·kind·embed_pending 계약 동일하다.
- **`source`는 네이버가 아니라 실제 발행처 이름**이다 — `originallink` 도메인에서 발행처를 유도한다(`collect/naver_news.py`의 `_PUBLISHERS`). 도메인이 미등록이면 도메인 그대로, 네이버가 직접 호스팅하거나 판별 불가면 "네이버"로 저장한다.

### `job_health` (collect_all 통합 Job이 기록, 공개 read)
잡별 최근 실행 상태 1문서(문서 키 = 잡 key, 예: `collect_all`). 대시보드(`web/dashboard.html`)가 읽어 조용한 실패·멈춤·미실행을 표시한다(operations §G).
- **저장 필드**: `job`, `last_status`(예: ok|running|fail), `fetched_at`, `last_run_at`, `last_finished_at`, `last_success_at`, `detail`(옵션 요약 문자열). **대시보드가 판정에 실제로 쓰는 것**은 `last_status`·`fetched_at`·`detail` 셋이다. **`expire_at` 없음**(상태 문서라 만료 불요).

## Store 표면 (`firestore_store.FirestoreStore`)
- `upsert_items(items) -> int` — `_to_doc`가 `kind` 분류 + `expire_at`을 박는다.
- `upsert_items_batched(items) -> int` — 청크 배치 존재검사 후 신규만 커밋한다(네이버·FMP 경로가 사용하며 read를 라운드트립 수로 축소한다).
- `get_job_health(job)` / `set_job_health(job, **fields)` — job_health 문서 읽기와 부분 갱신이다(set_job_health가 내부적으로 read-modify-write한다).
- `get_feed_state`, `set_feed_state`, `count`, `filter_new_ids`, `set_meta`.
- `get_pending_embed_items(limit)`, `save_vectors(entries)`, `clear_embed_pending(ids)` — 임베딩 대기 큐·벡터 저장(원자 batch + 만료 격리)·영구 실패 처분. 타입 계약은 `contracts/ports.py`의 `PendingItem`·`VectorEntry`.
- `close`/`__enter__`/`__exit__`.

## 필터 (비-LLM 규칙, 수집 경로에 배선됨)
저장 전에 원본을 버리지 않는다(비파괴). 대신 수집 시점에 분류·중복 제거만 한다.
- **dedup**: `parser.py`(link→guid→title url 기반) + `store.filter_new_ids` + `upsert_items`(이미 있으면 미덮어씀).
- **kind 분류**: `_to_doc`가 `classify_kind`로 spam/sports/digest를 라벨링 → UI가 story만 노출.
- **본문 수집**: `collect/body_fetch.py`의 `enrich_bodies`는 화이트리스트에 등록된 소스가 있으면 본문을 채운다(LLM 아님). 현재 등록된 소스가 없어 no-op이다(사유는 `docs/data-sources.md`).

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
- **`config/feeds.yaml`의 `tier` 필드** — `feeds.yaml`은 수집기 SSOT다. 수집 패스가 `meta/sources`에 `{"sources":[...], "tiers":{source: tier}}`로 발행한다. UI는 거기서 소스 등급을 읽는다. 파일을 복제하지 않는다(SSOT). `meta/sources`는 RSS 소스만 담는다 — 네이버와 FMP로 들어온 기사는 실제 발행처 이름으로 저장되므로 이 목록에 포함되지 않는다.
