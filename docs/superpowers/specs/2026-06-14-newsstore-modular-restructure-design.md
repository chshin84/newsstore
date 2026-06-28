# newsstore 모듈러 리스트럭처 + 벡터검색 포트화 — 설계

> ⚠️ **부분 분할 (2026-06-28):** 이 문서의 **`enrich/` 모듈·VectorIndex·인리치 store 포트는 `news-analytics` 소유**로 이전 대상이다(경계·계약: **`docs/firestore-contract.md`**). **`collect`/`store`(수집)/`contracts` 구조만 newsstore에 유효.**

_작성: 2026-06-14 · 상태: 설계(검토중) · 동기: 코드 깔끔함/관심사 분리, 벡터검색 정식화, 서버사이드 인리치_

## 1. 목표 / 범위
작동 중인 newsstore(수집 라이브, 스토리 1034개 백필 완료)를 **깨끗한 모듈 경계**로 재구성하고, 벡터검색을 **포트/어댑터**로 정식화하며, 인리치를 **서버사이드(Cloud Run)** 로 옮겨 over-internet 병목을 없앤다.

**범위 안:** 모듈 재구성 · 벡터검색 포트(in-memory + Firestore find_nearest) · 테스트 전략(에뮬레이터 + functional core) · 인리치 Cloud Run 배포 + 자동화.
**범위 밖(별도 spec):** ① 스토리 타임라인 **UI**(Phase 2) ② Postgres 마이그레이션(검토 후 **기각** — Firestore find_nearest로 충분, $0).

## 2. 확정된 결정
- **DB = Firestore 유지**(마이그레이션 X). 무료 1GiB·쓰기 2만/일 → 우리 규모 $0. 벡터검색은 네이티브 `find_nearest`.
- **레포 = 모듈러 모노레포**(폴리레포 X — 동기가 '깔끔함'뿐이라 드리프트·조율 비용이 정당화 안 됨).
- **store = Firestore 단일 구현**(sqlite 백엔드 **제거**). 로컬/테스트는 **Firestore 에뮬레이터**(Docker)로 실엔진 충실도. → 이중 백엔드 드리프트(감사 지적) 소멸.
- **벡터검색 = 포트**: `InMemoryVectorIndex`(현 규모·로컬·테스트) + `FirestoreVectorIndex`(find_nearest, 대규모 시). 같은 인터페이스.
- **인리치 = Cloud Run에서 서버사이드 실행**(병목 해결의 본질 — 로컬↔클라우드 왕복 제거). **주기 10분**(뉴스 스토리는 10분 늦어도 무방, 깨우는 횟수↓로 비용↓). 수집은 5분 유지.

## 3. 타깃 모듈 구조
```
src/newsstore/
  contracts/            # SSOT — 다른 newsstore 모듈에 의존 0
    models.py           # RawItem · Story · Enrichment (dataclass)
    ports.py            # Protocol: Store · VectorIndex · LLMClient
  collect/              # RSS → items
    fetcher.py parser.py collector.py ssl_config.py feeds.py(=현 config.py)
  enrich/               # items → 태그·임베딩·스토리 (순수 판단 + 오케스트레이션)
    classify.py cluster.py tagger.py embedder.py processor.py
    gemini.py           # LLMClient 실구현(현 llm.py) — contracts.ports.LLMClient 구현
  store/                # Firestore 어댑터 (contracts.ports 구현)
    firestore_store.py  # Store 구현(문서 CRUD)
    vector_index.py     # InMemoryVectorIndex + FirestoreVectorIndex
  entrypoints/
    run_collect.py      # 현 run.py
    run_enrich.py       # 현 process.py
config/ web/ infra/ tests/
```
**의존 규칙:** collect·enrich·store는 `contracts`에만 의존하고 서로 import 안 함. 엔트리포인트가 구현체를 조립(주입). serve = `web/`(정적 사이트, Firestore 직접 읽기) 그대로.

## 4. contracts (포트 정의)
```python
# models.py — 저장 형태와 도메인 형태를 구분한다
@dataclass RawItem:    id, feed_id, source, url, title, body, fetched_at, lang, ...
@dataclass Enrichment: kind, tags(list), embedding(list|None), story_id(str|None)   # items에 얹는 필드
@dataclass Story:      id, title, centroid_sum(list), count(int), member_ids, entities,
                       first_seen, last_seen, status, tags(list)   # centroid = centroid_sum/count (파생)

# ports.py
class Store(Protocol):           # 문서 CRUD (벡터검색 제외)
    upsert_items / get_unprocessed / mark_processed / save_enrichment
    create_story / append_to_story / close_stale_stories / get_open_stories   # ← 시드/마감 소스
    get_untagged_stories / set_story_tags                                      # ← Pass 2(스토리 태깅)
    set_meta / get_feed_state / set_feed_state / count
class VectorIndex(Protocol):     # "열린 스토리 중 가장 가까운 것"
    @classmethod from_open_stories(cls, store, cutoff) -> "VectorIndex"        # 생성/시드
    def nearest(self, vec, *, threshold) -> str | None
    def add(self, story_id, *, centroid_sum, count) -> None                    # 새 스토리
    def update(self, story_id, *, centroid_sum, count) -> None                 # append 후 갱신
class LLMClient(Protocol):
    def generate_json(self, prompt, *, timeout) -> dict
    def embed(self, text, *, timeout) -> list[float]
```

## 5. 벡터검색 포트 설계
- **InMemoryVectorIndex**: `from_open_stories(store, cutoff)`로 centroid 1회 로드 → `best_match`(브루트포스). create/append 시 `add/update`로 **메모리** 갱신. **현 규모·로컬·테스트의 기본.** Cloud Run에서 Firestore 옆이면 over-internet 없어 충분히 빠름.
- **FirestoreVectorIndex**(미래/대규모): 스토리 doc에 **top-level `centroid` 벡터 필드(=sum/count)** 유지 + **복합 벡터 인덱스**(프리필터 `status` 먼저 + 벡터 last; 단일 벡터 인덱스로는 status==open 필터 불가) + `find_nearest(centroid, query=vec, limit=1, COSINE, distance_result_field, distance_threshold)`.
  - **임계값 = 거리**: Firestore COSINE distance = `1 − 유사도`. "코사인 ≥ 0.72"는 **`distance_threshold = 0.28`**(`distance <= 0.28`). 부호 반대로 쓰면 필터 역전 — 주의.
  - `add/update`는 **no-op 아님** — centroid 벡터 필드 갱신(append마다 mean 재계산). **비용 주의**: 벡터 필드 쓰기 = 색인 2 write-unit/append → **디바운스(K append/T초마다 재색인, 클러스터는 약간 stale centroid 허용)**. 핫 스토리는 ~1 write/s/doc 소프트리밋.
  - centroid 필드는 **top-level**(중첩 벡터는 에뮬레이터에서 무음 미동작 — firebase-tools #8077). 라이브러리 **`google-cloud-firestore >= 2.18.0`**(`distance_threshold`).
  - find_nearest는 **exact** brute-force KNN(블로그 출처, 문서 보장 아님). 과금: K 반환 doc read + 스캔 index entry(대시보드 비표시) → 프리필터 좁게.
- **클러스터 결정(threshold·assign)은 순수**, 저장/검색만 어댑터. centroid는 양쪽 `sum/count` 동일(SSOT `enrich.cluster.centroid`). **un-normalized sum 저장, 비교/색인 시 정규화**(cosine은 노름으로 나누므로 매그니튜드 무관 — 단 dot-product 가정 금지).
- **InMemory 성능**: `best_match` 순수 파이썬 루프는 ~1k centroid에서 OK지만 1만+에선 느림(100~1000×). 스케일 시 **numpy `(N,768)` float32 행렬 × 쿼리(gemv)** 로 벡터화 → sub-ms~2ms. 현 규모(1k)는 현행 유지, 벡터화는 필요 시.

## 5b. 인리치 파이프라인 (2-패스 — 이미 구현, 유지)
사용자 요청대로 **클러스터와 태깅을 분리**한다(클러스터는 빠르게, 태깅은 스토리당 1회).
- **Pass 1 — cluster** (`run_enrich --mode cluster`): get_unprocessed → classify(kind) → (story·충분텍스트·비TruthSocial만) **병렬 임베딩(50)** → `VectorIndex.nearest`로 합류/신규 → save_enrichment(embedding·story_id·tags=[]) → mark_processed. **LLM 태깅 없음** → 빠름.
- **Pass 2 — tag** (`run_enrich --mode tag`): `get_untagged_stories` → 스토리 제목 기준 **배치 태깅(gemini-3.1-flash-lite, 10건)** → `set_story_tags`. 1 스토리 = 1 태깅(아이템마다 X)이라 콜 수 ≪ 아이템 수.
- 뷰는 `story.tags`를 읽음(아이템 태그 의존 X). 기존 백필 스토리(1034)는 Pass 2로 일괄 태깅.
- 임계값 0.72·MIN_EMBED_CHARS·NONCLUSTER_SOURCES·thin가드는 실데이터 캘리브레이션값(유지).

## 6. 테스트 전략 (functional core / imperative shell)
- **판단 함수**(classify·cosine·best_match·validate_tags·embed_text) → DB 없이 단위테스트. 버그 대부분 여기.
- **store(문서 I/O)** → **Firestore 에뮬레이터**(Docker)로 통합테스트. `mock-firestore` 폐기(실client 괴리로 to_dict None 등 놓친 전력).
- **외부(Gemini embed/tag, find_nearest)** → 라이브 스모크(소량), CI 분리.
- **processor(오케스트레이션)** → 가짜 LLMClient + 에뮬레이터 store + InMemoryVectorIndex로 end-to-end.
- `docker compose`: `firestore-emulator` + `test` 서비스. `FIRESTORE_EMULATOR_HOST=host:8080`(스킴 없이). 벡터검색은 in-memory 어댑터라 에뮬 벡터기능 불요.
- ⚠️ **에뮬레이터는 복합 인덱스를 무시**(인덱스 없어도 쿼리 통과) → 로컬 그린·프로덕션 `FAILED_PRECONDITION`. **`firestore.indexes.json`을 SSOT로 두고 인덱스 요구를 실 Firestore로 검증**(CI 스모크). 에뮬은 문서계약(예: 빈 doc `to_dict()` None) 충실하나 인덱스·복합쿼리는 못 잡음.

## 7. 배포 / 운영 / 비용 (⚠️ 재검토됨)
- **인리치 Cloud Run Job#2** `newsstore-enricher`(단일 이미지 + CMD=`run_enrich`). Firestore 옆 → over-internet 제거(병목 해결). `GEMINI_API_KEY`는 Secret Manager. **Scheduler#2 주기 실행**(Cloud Scheduler는 3잡 무료 — 빈도 무관 $0).
- 🔴 **비용 정정**: Cloud Run **무료티어(180K vCPU-s/월)는 Tier 1 리전 전용 — 서울(asia-northeast3)은 Tier 2라 무료 없음.** Job은 실행당 **1분 최소 과금**. 서울 1 vCPU 기준: **1분 주기 ≈ $46~93/월, 5분 ≈ $9~18/월, 둘 다 $0 아님.** (→ 현 수집기도 이미 소액 과금 중일 가능성, 무료 크레딧에 가려짐.)
- **리전은 하드 제약 아님(정정)**: 병목의 본질은 "로컬↔클라우드 공용인터넷"이었고 **서버사이드 실행만으로 해소**. 서버↔DB 거리지연은 **현 코드가 배치당 ~250 순차 쓰기**라 누적되는 것 → 진짜 해법은 **Firestore 배치 쓰기**(1 호출에 ≤500 ops)로 왕복을 1~2회로 축소. 그러면 cross-region도 무시 가능 → **무료 Tier 1 리전 사용 가능**.
- **권장**: ① **쓰기 배치/병렬화**(save_enrichment+mark+story 묶기)를 먼저 → 왕복·실행시간 급감, ② 그 위에서 리전은 자유 — 무료 원하면 **Tier 1(us-central1)**, 지연 최소 원하면 서울. 둘 다 배치 후엔 충분히 빠름.
- **비용**: 배치로 실행시간 짧아지면(vCPU-s↓) Tier 1에선 무료 근접, 서울이어도 소액. Cloud Scheduler 3잡 무료.
- **✅ 확정(2026-06-14 대화)**: 인리치 **10분 주기**, **서울 유지 + 소액 수용**(코사인 계산·DB·Gemini는 사실상 $0, 유일 비용은 직원이 깨어 도는 시간). 비용 절감 수단 = **쓰기 배치화** + (옵션) **수집+인리치를 한 잡으로 통합**(직원 하나 → 청구 한 번; 단 모듈 결합도↑ 트레이드오프 — Phase D에서 결정).
- **상세 배포 절차**: operations.md §E 갱신(초안 있음).

## 8. 마이그레이션 계획 (작동 시스템 — 단계별, 각 단계 테스트 그린)
1. **Phase A — 순수 이동(동작 0변경):** contracts 추출(models·ports) + collect 묶기 + 엔트리포인트 분리. import만 바뀜, 동작·테스트 동일.
2. **Phase B — 벡터검색 포트:** `VectorIndex` 포트 + **InMemoryVectorIndex만** 도입(processor가 store.get_open_stories 직접 호출 대신 포트 경유). **FirestoreVectorIndex(find_nearest)는 이번에 안 만듦** — 문서화된 미래 어댑터(스케일 트리거 시). 기존 클러스터 동작 동일(회귀 테스트).
3. **Phase C — store 단일화 + 에뮬레이터:** sqlite 백엔드/팩토리 제거, 테스트를 에뮬레이터로 전환. **(가장 무겁고 분리 가능 — 에뮬 셋업이 과하면 독립 결정/연기 가능. A·B·D와 디커플)**.
4. **Phase D — Cloud Run 배포 + 자동화:** 인리치 Job#2(서울) + Scheduler#2(5분). 수집 주기 변경 없음.
각 Phase 독립 커밋. A·B는 순수 리팩터(외부 영향 0), C·D는 인프라. **Phase A가 사용자 핵심 동기(깔끔함) 충족 — B/C/D는 그 위 선택적 강화.**

## 9. 리스크 / 오픈
- 🔴 **Cloud Run 비용(서울 Tier 2)** — §7. 인리치 배포 자체가 $0 아님 → 리전/주기 사용자 결정.
- **에뮬레이터 한계** — ① 컨테이너로 mock보다 무거움(충실도 이득이 큼) ② **복합 인덱스 무시**(§6, CI에서 실 Firestore 검증) ③ 벡터검색 미문서·중첩 깨짐(top-level 필드 유지, KNN은 실 Firestore 검증).
- **find_nearest는 현 단계 미사용**(in-memory) — 어댑터만 준비. 실제 채택 전: 복합 벡터 인덱스·distance(0.28)·lib≥2.18·재색인 디바운스 확정.
- **centroid 스트리밍 드리프트** — 스토리 수명 중 주제 이동/단독항목 임계 민감/centroid 정규화 누락. `close_stale_stories`로 무한증식 차단(닫힌 스토리는 후보에서 제외 — InMemory·find_nearest 양쪽 확인).
- **sqlite 제거 영향** — 로컬 제로셋업 편의 상실(에뮬레이터로 대체). 외부 소비자가 sqlite 쓰면 확인(현재 무관).
- **기존 백필 데이터** — 1034 스토리는 OLD 로직(일부 무태그). Phase B/C 후 **Pass 2로 일괄 재태깅** + 닫힌 스토리 정리 1회.

## 10. 연결
- 코드 원칙: `docs/coding-principles.md`(SSOT·Fail-Loud·강건성). 함정: `solved_problems.md`.
- 후속: 이 리스트럭처 위에서 **스토리 타임라인 UI**(Phase 2, 별도 spec).

<!-- spec-review: passed lenses=0 date=2026-06-28 note=grandfathered — pre-existing shipped doc (2026-06-12~14), predates review gate; not re-reviewed this session -->

<!-- spec-review: passed lenses=3 date=2026-06-28 -->
