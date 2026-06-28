# Firestore 데이터 계약 — newsstore ↔ news-analytics

newsstore(뉴스 수집·저장·호스팅)와 **news-analytics**(별개 repo — LLM 태깅·임베딩·클러스터·스토리·risk/impact 점수)는 **코드로 결합하지 않는다.** 두 repo가 만나는 유일한 이음새는 **Firestore 스키마**다. 이 문서가 그 경계의 SSOT다.

- **결정(2026-06-28):** news-analytics는 **Firestore에 직접** read/write 한다(Firestore-as-API). newsstore 라이브러리를 import 하지 않는다 → 코드 결합 0, 계약은 스키마뿐.
- **이 문서의 역할:** 누가 무엇을 쓰고 읽는지, 핸드오프·불변식·인프라 소유를 못 박는다. 두 repo의 세션이 이 문서를 기준선으로 합의한다.

## 소유권 — 누가 쓰고 누가 읽나

| 데이터 | writer | reader | 비고 |
|---|---|---|---|
| `items` (raw 필드) | **newsstore** (collect Job) | news-analytics, web UI | 기사 원본 |
| `items.processed=false` (seed) | **newsstore** (upsert 시) | news-analytics | "인리치 필요" 핸드오프 신호 |
| `items` (인리치 필드) | **news-analytics** (merge) | web UI | `kind·tags·embedding·story_id·processed=true·processed_at` (+ `risk·impact` 예정) |
| `feed_state` | **newsstore** | newsstore | etag/last_modified 폴링 상태 |
| `meta` (sources·tier) | **newsstore** | web UI, news-analytics | 소스 목록 + tier를 발행(아래 §공유 설정) |
| `stories` | **news-analytics** | web UI | centroid·member_ids·요약·점수 |

## 컬렉션 스키마

### `items`
- **raw (newsstore가 collect로 기록)** — `feed_id, source, asset_hint, language, url, title, body, published_at, fetched_at`. 모델 SSOT는 `src/newsstore/contracts/models.py`의 `RawItem`.
- **seed (newsstore가 upsert 시 기록)** — `processed=false, processed_at=null, tags=[]`. 출처: `src/newsstore/store/firestore_store.py` `_to_doc`. **`processed=false`가 핸드오프 신호다.**
- **enrich (news-analytics가 merge로 기록)** — `kind, tags[], embedding[], story_id, processed=true, processed_at`. 향후 `risk, impact`(topic-lens 재설계). **raw 필드는 절대 덮어쓰지 않는다(merge only).**

### `feed_state` (newsstore 전용)
폴링 캐시(`etag, last_modified, last_fetched`). news-analytics는 손대지 않는다.

### `meta` (newsstore가 기록, 공개 read)
사이트용 소형 메타 문서(예: `sources`). 소스 목록과 **소스 tier**(아래 §공유 설정)를 여기로 발행한다.

### `stories` (news-analytics가 기록)
스토리/클러스터(`centroid, member_ids, entities, status, 요약, 점수`). 스키마의 SSOT는 **news-analytics repo**이며 변경 시 이 문서의 UI read 계약을 함께 갱신한다.

## 핸드오프 프로토콜 — `processed` 플래그
1. newsstore가 raw item을 쓸 때 `processed=false`를 박는다(verified: `firestore_store.py` `_to_doc`).
2. news-analytics가 `processed==false`인 item을 오래된 순으로 끌어와(`get_unprocessed` 패턴) 인리치한다.
3. 끝나면 `processed=true, processed_at`을 merge로 기록(`mark_processed` 패턴).
- **고정 계약:** 필드명 `processed`(bool), 기본값 `false`, 방향(newsstore=false 생산, analytics=true 소비). 어느 쪽도 이 의미를 임의로 바꾸지 않는다.

## 불변식 (계약 테스트로 강제 — FAIL-LOUD)
별개 repo가 된 만큼 구두 약속이 아니라 테스트로 지킨다.
- **비파괴 merge** — news-analytics는 인리치 필드만 merge하고 raw 필드(title/body/url/published_at…)를 덮어쓰지 않는다.
- **스키마 드리프트 가드** — web UI가 읽는 인리치 필드명(`tags, story_id, stories.*`)이 바뀌면 터지는 계약 테스트. 이름이 조용히 어긋나면 사이트가 빈 화면이 된다.
- **Fail-soft 렌더** — news-analytics가 미배포/중단이면 인리치 필드가 없을 수 있다. UI는 그래도 raw 목록을 정상 렌더하고, 인리치 의존 컨트롤(태그 드롭다운·스토리 탭)은 우아하게 강등한다. `web/index.html`에 필드 가드(`it.tags || []`, `s.developments || []`, `Number(s.count) || …`, 빈-상태 폴백)는 **이미 존재** — `stories` 컬렉션이 비면 스토리 탭이 빈 목록으로 강등된다(검증됨). 분리 후에도 이 강등 불변식을 회귀 테스트로 지킨다.

## 인프라 소유권
- **newsstore = DB 인프라 소유** — Firestore 자체, 보안규칙(`items`·`stories` public read), 복합 인덱스 적용.
- **news-analytics = 필요 인덱스·필드 선언** — 새 쿼리에 인덱스가 필요하면 news-analytics가 선언하고 newsstore가 적용한다(`docs/operations.md §D`).
- **GEMINI 시크릿·Cloud Run Job#2/#3·Scheduler#2/#3 = news-analytics 소유** — 비밀(`GEMINI_API_KEY`)은 백엔드 전용(SECRETS). **과도기 현실은 아래 참조.**

## 공유 설정
- **`config/taxonomy.yaml` → news-analytics 소유(이전 후보)** — LLM 태거의 어휘/티커 검증용이다. **web UI는 taxonomy를 읽지 않고** `items.tags`에서 드롭다운을 도출한다(`refreshTagOptions`). 따라서 newsstore에 남길 이유가 없다.
- **`config/feeds.yaml`의 `tier` 필드 → newsstore 파일에 두되, analytics는 `meta`에서 읽는다** — `feeds.yaml`은 수집기 SSOT라 newsstore 소유다. news-analytics는 그 파일이 없으므로 **newsstore가 source·tier를 `meta` 문서로 발행**(기존 `set_meta` 재사용)하고 analytics가 거기서 읽는다. 파일을 두 repo에 복제하지 않는다(SSOT). — **처방(미배선)**: `tier` 필드는 `feeds.yaml`에 이미 존재하나, 현재 `meta` 발행이 tier까지 포함하는지는 별도 배선 확인 필요(미포함이면 추가).

## 과도기 현실 (정직하게 — 아직 코드는 안 옮겨짐)
분리는 **조직/방향상** 결정됐지만, 2026-06-28 현재 **코드는 물리적으로 newsstore에 잔류**한다:
- `src/newsstore/enrich/`(분류·태깅·임베딩·클러스터·요약·점수)와 엔트리포인트 `run_enrich`가 newsstore src 안에 있다.
- `processor:latest` 이미지는 **newsstore Dockerfile**(`INSTALL_ENRICH=true`)에서 빌드되고, Cloud Run Job `newsstore-enricher`(#2)·`newsstore-summarizer`(#3)가 **라이브로 운영 중**이다(`docs/operations.md §E·§F`).
- `contracts/ports.py`의 `Store` Protocol이 수집 메서드와 인리치 메서드를 **한 인터페이스에 섞고 있다**(분리 시 인리치 절반이 news-analytics로 이동 대상).

→ 위 계약은 **목표 경계**다. 코드 물리 이전(enrich 디렉터리·ports 분할·이미지 빌드 출처 이전)은 별도 작업이며, 완료 전까지 이 문서가 "어디로 가야 하는지"의 기준이다.

## 스펙/플랜 소유권 인덱스 (분할 후)
기존 `docs/superpowers/` 문서가 단일 repo를 전제로 쓰여 있어, 분할 기준으로 재분류한다. 각 파일 상단 배너가 이 표를 가리킨다.

| 문서 | 소유 | 상태 |
|---|---|---|
| specs/2026-06-12-newsstore-design | newsstore | 유효 |
| specs/2026-06-12-newsstore-gcp-deploy-design | 혼합 | 인리치 스키마(processed/tags)는 본 계약이 SSOT |
| specs/2026-06-13-newsstore-step2-enrichment-design | **news-analytics** | DEPRECATED(분할) |
| specs/2026-06-14-newsstore-modular-restructure-design | 혼합 | enrich 부분만 news-analytics |
| specs/2026-06-15-newsstore-story-timeline-ui-design | 혼합 | 백엔드 요약=analytics / UI=newsstore |
| specs/2026-06-28-newsstore-topic-lens-redesign-design | **news-analytics** | DEPRECATED(분할) — 단 §9 피드는 별도 스펙 |
| specs/2026-06-28-feed-source-expansion-design | newsstore | 유효 |
| plans/2026-06-12-newsstore-collector | newsstore | 유효 |
| plans/2026-06-12-newsstore-firestore-store | newsstore | 유효 |
| plans/2026-06-13-step2-enrich-core | **news-analytics** | DEPRECATED(분할) |
| plans/2026-06-13-step2-store-ext | 혼합 | 인리치 store 메서드는 news-analytics |
| plans/2026-06-14-step2-llm-tagging | **news-analytics** | DEPRECATED(분할) |
| plans/2026-06-14-step2-processor-deploy | **news-analytics** | DEPRECATED(분할) |
| plans/2026-06-14-phase-a-modular-restructure | newsstore | 유효(enrich 번들링은 이전 대상) |
| plans/2026-06-14-phase-b-vector-index-port | **news-analytics** | DEPRECATED(분할) |
| plans/2026-06-14-phase-c-emulator-single-store | newsstore | 유효 |
| plans/2026-06-14-phase-d-deploy-batch | 혼합 | Job#2 배포는 news-analytics |
| plans/2026-06-15-story-summary-backend-plan | **news-analytics** | DEPRECATED(분할) |
| plans/2026-06-15-story-timeline-frontend-plan | newsstore | 유효(UI) |
| plans/2026-06-28-feed-source-expansion | newsstore | 유효 |
