# Firestore 데이터 계약 — newsstore ↔ news-analytics

**결정(2026-06-29): 통합.** 인리치/분석을 **newsstore 내에서 개발**한다(클러스터링은 news-analytics에서 `enrich/clustering.py`로 이식됨). newsstore가 `items`·`stories`의 인리치 필드를 **직접 write**한다. 이 문서는 이제 **`items`/`stories` 스키마 정의 + UI read 계약**이며, **미래 재분리(인터페이스 안정·MCP/agent 목표 구체화 시)의 기준선**으로 보존한다. 전략: 메모리 `integration-strategy` · 작업 순서: `docs/roadmap.md` · 분석 설계: `docs/analysis-design.md`.

> 아래 표·스키마에서 "writer = news-analytics"는 **현재 newsstore(통합)**로 읽는다. 분리 전제(Firestore-as-API·import 없음)는 미래 재분리 시에만 유효한 역사적 맥락이다.

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

### `stories` (newsstore 인리치가 기록)
스토리/클러스터(`centroid_sum, count, member_ids, entities, status, first_seen, last_seen, 요약 필드`).
- **`lenses[]`** (string[], Phase 1) — 토픽 렌즈 id 배열(`config/topics.yaml` SSOT). 렌즈 패스(`run_enrich --mode lenses`)가 write, UI가 렌즈 필터·정렬에 read. 없으면 빈 배열 폴백(비파괴). id→type 해석은 topics.yaml.
- **`developments[].delta_time`** (datetime, Phase 2) — 그 전개가 새 정보로 우리 스토어에 처음 편입된 시각(`published_at`=발행시각과 구분되는 2번째 타임스탬프). 요약 패스(`run_enrich --mode summary`)가 write — milestone 게이트(LLM `is_new`)가 진짜 새 전개면 `time`, 단순 recap이면 기존 프런티어(`max(prior delta_time)`)에 귀속해 **새 델타로 앞서지 않게** 한다. 없으면 소비자가 `developments[].time`으로 폴백(additive·비파괴, 레거시 안전).
- 향후 `risk·impact`(Phase 3 score). 변경 시 UI read 계약 함께 갱신.

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

## 문서 안내 (2026-06-29 통합 정리)
분리시대 소유권 인덱스는 폐기됨(통합으로 모두 newsstore 소유, 실행 plan 16종은 삭제 — git 히스토리 보존). 현 SSOT: **작업 순서 `docs/roadmap.md` · 분석 설계 `docs/analysis-design.md`**. `docs/superpowers/specs/`의 날짜별 설계 스펙은 *설계 근거 히스토리*로 보존된다.
