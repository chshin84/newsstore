# news-analytics v1 작업 지시 (newsstore → news-analytics 핸드오프)

_작성: 2026-06-28 · 성격: 요구자(newsstore) → 수행자(news-analytics) 핸드오프 · 회신(§7)을 받으면 이 문서를 갱신한다._

> **쓰는 법:** 아래 "전달 본문"을 그대로 복사해 news-analytics 세션에 전달한다. 그 세션은 이 대화 맥락이 없으므로 본문은 자기완결적이다. 계약의 SSOT는 `docs/firestore-contract.md`이며, 본문 §2는 그 요약이다.

---

## 전달 본문 (복사해서 news-analytics 세션에 전달)

### 0. 너의 정체성·관계
너는 **news-analytics** 라는 별개 repo에서 일한다. 자매 프로젝트 **newsstore**가 뉴스 **수집·저장·호스팅(웹 UI)**을 담당하고, **너는 분석/인리치 계층**(LLM 태깅·임베딩·스토리 클러스터·요약·점수)을 담당한다.

**핵심 규칙: 두 repo는 코드로 결합하지 않는다. 유일한 이음새는 Firestore다.** 너는 newsstore를 import하지 않고, **자기 Firestore 클라이언트로 직접** 읽고 쓴다(Firestore-as-API). GCP 프로젝트 `daily-recap-498506`, 리전 `asia-northeast3`, Firestore `(default)` Native.

### 1. 1차 목표 (v1) = 동일 구현 (재설계 아님)
인리치 파이프라인은 **지금 newsstore 이미지에서 라이브로 돌고 있다**(Cloud Run Job#2/#3). 너의 **첫 마일스톤은 새 기능이 아니라, 그 라이브 구현을 news-analytics repo로 옮겨 동작을 동일하게 재현하는 것**(behavior-preserving lift-and-shift)이다. 토픽 렌즈 재설계·risk/impact 점수 같은 새 설계는 **v2이며 이번 범위가 아니다**(§5).

분리를 안전·가역적으로 만들기 위해, v1에서는 동작을 바꾸지 않는다.

### 2. 인터페이스 계약 (Firestore 스키마 = 너와 newsstore의 유일한 약속)
> newsstore repo를 읽을 수 있으면 `docs/firestore-contract.md`가 이 계약의 SSOT다. 아래는 그 요약(자기완결용).

**컬렉션·소유권**

| 데이터 | 누가 쓰나 | 너의 동작 |
|---|---|---|
| `items` (raw: id, feed_id, source, asset_hint, language, url, title, body, published_at, fetched_at) | newsstore | **읽기만** |
| `items.processed=false, processed_at=null, tags=[]` (raw에 박혀 옴) | newsstore | "인리치 필요" 신호 |
| `items` 인리치 필드: `kind, tags[], embedding[768], story_id, processed=true, processed_at` | **너 (merge 쓰기)** | raw 필드 절대 덮어쓰지 마라 |
| `stories/{id}`: `title, centroid_sum[], count, member_ids[], entities[], first_seen, last_seen, status(open\|closed)` + 요약필드 `summary, latest, developments[{text,time,source_count}], summary_count, summary_at` | **너** | 생성·갱신 |
| `feed_state` | newsstore | **건드리지 마라** |
| `meta` (sources, source tier) | newsstore | **읽기만** (tier는 impact prior 등에 사용) |

**`processed` 핸드오프 프로토콜**
1. newsstore가 raw item에 `processed=false`를 박는다.
2. 너는 `where('processed','==',false).order_by('fetched_at')`로 미처리분을 끌어온다.
3. 인리치 끝나면 `processed=true, processed_at`을 **merge**로 기록한다.

**불변식 (반드시 지킬 것)**
- **비파괴 merge**: 인리치 필드만 merge. raw(title/body/url/published_at…)는 절대 덮어쓰지 않는다.
- **임베딩 차원**: 768 고정(`EMBED_DIM`). dim 어긋나면 fail-loud.
- **스키마 안정**: 위 필드명은 newsstore 웹 UI가 그대로 읽는다(`tags`, `story_id`, `stories.*`). 이름 바꾸면 사이트가 깨진다. v1에선 절대 바꾸지 마라.

**Firestore 인덱스(현재 라이브)**: `items`: `source+published_at`, `tags+published_at`, `processed+fetched_at`. 스토리 쿼리용 `status`/`last_seen`. 새 인덱스가 필요하면 §7로 newsstore에 요청하라(인덱스 적용은 newsstore 소유).

### 3. 가져올 것 — 레퍼런스 구현 (newsstore에서 포팅)
레퍼런스는 newsstore repo(예: `D:\projects\newsstore`)에 있다. **동작을 베끼되, store 접근은 직접-Firestore로 재작성**한다.

**순수 로직 — 1:1 복사** (`newsstore/src/newsstore/enrich/`):
`classify.py`(kind 선필터), `cluster.py`(cosine/centroid/assign), `vector_index.py`(InMemoryVectorIndex 최근접), `tagger.py`(통제어휘 검증+태깅), `embedder.py`(임베딩+dim 가드), `gemini.py`(GeminiClient/LLMClient: timeout/retry/None가드), `summarizer.py`(요약 패스), `processor.py`(오케스트레이션), `taxonomy.py`(어휘 로더).

**store 접근 — 재작성** (지금은 `newsstore/src/newsstore/contracts/ports.py`의 Store + `store/firestore_store.py`에 얹혀 있음). 다음 메서드를 **너의 Firestore 클라이언트로 같은 스키마에** 재구현하라:
`get_unprocessed`, `mark_processed`, `save_enrichment`, `create_story`, `append_to_story`, `get_open_stories`, `close_stale_stories`, `get_stories_needing_summary`, `get_story_members`, `save_story_summary`.

**엔트리포인트·설정**: `entrypoints/run_enrich.py`(`--mode cluster|summary|tag`), `config/taxonomy.yaml`(어휘 SSOT — 너의 repo로 인수).

**테스트 — 그대로 가져와 green 유지**: `tests/test_cluster.py`, `test_vector_index.py`, `test_processor.py`, `test_tagger.py`, `test_embedder.py`, `test_llm_client.py`, `test_store_stories.py`, `test_store_enrichment.py`, 요약 테스트. (store 테스트는 Firestore 에뮬레이터에 붙는다.)

**현재 파이프라인 동작 (재현 대상)**:
- **Pass 1 cluster** (`run_enrich --mode cluster`, 10분 주기): get_unprocessed → classify(kind) → (kind=story·충분텍스트·non-TruthSocial만) 병렬 임베딩 → VectorIndex.nearest로 합류/신규 → save_enrichment(embedding·story_id·tags=[]) → mark_processed. 끝에 close_stale_stories.
- **Pass 3 summary** (`run_enrich --mode summary`, 시간당): get_stories_needing_summary → get_story_members → LLM 요약 → save_story_summary(developments 등).
- Pass 2 tag는 레거시(폐기 예정) — 재현 안 해도 됨, 단 동작 확인 후 결정.

**상수·모델명 (코드가 SSOT — 문서엔 드리프트 있음)**: `EMBED_DIM=768`, 클러스터 임계 `cluster.py`의 `DEFAULT_THRESHOLD`(+ env `NEWSSTORE_CLUSTER_THRESHOLD`), `OPEN_WINDOW`/`CLOSE_AFTER`(48h/24h), `NONCLUSTER_SOURCES`, 임베딩 동시성·배치, `MAX_BATCHES`, 요약 배치. **Gemini 모델명은 반드시 `gemini.py`에서 그대로 읽어라** — README/roadmap의 모델명은 어긋나 있으니 믿지 마라.

**인프라 (인수 대상)**: 이미지 `processor:latest`(현재 newsstore `Dockerfile` + `INSTALL_ENRICH=true` + `infra/cloudbuild.processor.yaml`로 빌드), Cloud Run Job#2 `newsstore-enricher`(cluster)·Job#3 `newsstore-summarizer`(`--mode summary`), Scheduler #2(`*/10`)·#3(시간당), 서비스계정 `newsstore-job`, Secret Manager `gemini-api-key`. 상세 절차는 newsstore `docs/operations.md §E·§F`.

**설계 레퍼런스 문서** (newsstore에서 DEPRECATED 표시됨 = 너의 v1 빌드 근거): `docs/superpowers/specs/2026-06-13-newsstore-step2-enrichment-design.md`, `.../2026-06-14-newsstore-modular-restructure-design.md`, `.../2026-06-15-newsstore-story-timeline-ui-design.md`(백엔드 요약 부분), 관련 plans(step2-*, phase-b, story-summary-backend).

### 4. v1 "됨"의 정의 (검증 기준 — 이게 통과해야 완료)
태깅·요약은 LLM이라 출력이 바이트 동일일 수 없다. 따라서 "동일"은 이렇게 정의한다:
1. **포팅한 테스트 스위트 전부 green** (위 §3 테스트 + 에뮬레이터 store 테스트). 결정론 부분(kind 분류·어휘 검증·cosine/centroid·클러스터 배정·dim 가드)이 동일하게 통과해야 한다.
2. **라이브 스모크**: 소량 실제 데이터로 한 패스 돌려, Firestore에 쓰인 **필드 형태·존재·story_id 배정·요약 구조가 §2 계약과 일치**함을 확인(증거: 쿼리/스크린샷).
3. 검증되면 **컷오버**: newsstore의 Job#2/#3을 끄고 news-analytics의 Job으로 전환. (이 컷오버는 newsstore와 조율 — §7.)

### 5. 범위 밖 (v2 — 이번엔 하지 마라)
토픽 렌즈 하이브리드 재설계, risk/impact dual 점수, 개체-aware 병합/gray-band LLM 판정, 델타 타임라인, Now Brief UI. 이건 newsstore `docs/superpowers/specs/2026-06-28-newsstore-topic-lens-redesign-design.md`의 v2 목표다. **v1 동일구현·컷오버가 끝난 뒤** 별도로 다룬다.

### 6. 반드시 준수할 원칙
- **TDD**: 실패 테스트 먼저, 증거로 주장(로그/쿼리). 포팅한 테스트가 기준선.
- **비파괴**: raw 보존, 가공은 merge/마킹으로.
- **비밀 분리**: `GEMINI_API_KEY`는 백엔드 전용(Secret Manager). 커밋·로그·프롬프트에 노출 금지.
- **Fail-loud**: 스키마/차원/계약 위반은 조용히 넘기지 말고 터뜨려라.
- **SSOT**: 어휘·상수·모델명은 한 곳(코드/config)에서 도출. 복제 금지.

### 7. newsstore(요구자)에 회신할 것
v1 진행 중/후 다음을 보고하라(요구자가 이걸 받아 newsstore 쪽을 맞춘다):
1. **§2 스키마 합의 여부** — 그대로 갈 수 있나? 불가피한 편차가 있으면 무엇·왜.
2. **newsstore에 필요한 작업** — 추가 Firestore 인덱스 목록, `meta`에 source **tier** 발행 필요 여부(현재 meta가 tier를 싣는지 불확실 — 미포함이면 newsstore가 추가).
3. **확인된 모델명** (`gemini.py`에서 읽은 실제 값) — 문서 드리프트 교정용.
4. **컷오버 준비 상태** — 언제 Job 전환 가능한지, 롤백 방법.
5. **막힌 점·질문**.

---

## 회신 로그 (news-analytics → newsstore)
_§7 회신을 받으면 여기 기록하고, newsstore 반영(인덱스 추가·tier 발행·모델명 교정)을 추적한다._

- (대기 중)
