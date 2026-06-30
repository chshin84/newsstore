# Firestore 데이터 계약 — newsstore

이 문서는 `items`/`stories` 스키마 정의 + UI read 계약이다. 분석 설계: `docs/analysis-design.md`.

## 소유권 — 누가 쓰고 누가 읽나

| 데이터 | writer | reader | 비고 |
|---|---|---|---|
| `items` (raw 필드) | collect Job | web UI | 기사 원본 |
| `items.processed=false` (seed) | upsert | enrich 패스 | "인리치 필요" 핸드오프 신호 |
| `items` (인리치 필드) | enrich 패스 (merge) | web UI | `kind·tags·embedding·story_id·processed=true·processed_at` |
| `feed_state` | collect Job | collect Job | etag/last_modified 폴링 상태 |
| `meta` (sources) | collect Job | web UI | 소스 목록 발행(tier 전파는 §공유 설정 참조) |
| `stories` | enrich 패스 | web UI | centroid·member_ids·요약·점수 |

## 컬렉션 스키마

### `items`
- **raw (collect로 기록)** — `feed_id, source, asset_hint, language, url, title, body, published_at, fetched_at`. 모델 SSOT는 `src/newsstore/contracts/models.py`의 `RawItem`.
- **seed (upsert 시 기록)** — `processed=false, processed_at=null, tags=[]`. 출처: `src/newsstore/store/firestore_store.py` `_to_doc`. **`processed=false`가 핸드오프 신호다.**
- **enrich (enrich 패스가 merge로 기록)** — `kind, tags[], embedding[], story_id, processed=true, processed_at`. **raw 필드는 절대 덮어쓰지 않는다(merge only).** (risk/impact는 `items`가 아니라 `stories`에 산출 — 아래 §stories.)

### `feed_state` (수집기 전용)
폴링 캐시(`etag, last_modified, last_fetched`).

### `meta` (collect가 기록, 공개 read)
사이트용 소형 메타 문서(예: `sources`). 소스 목록과 **소스 tier**(아래 §공유 설정)를 여기로 발행한다(tier 전파 작업은 GitHub Issue #17).

### `stories` (인리치가 기록)
스토리/클러스터(`centroid_sum, count, member_ids, entities, status, first_seen, last_seen, 요약 필드`).
- **`lenses[]`** (string[]) — 토픽 렌즈 id 배열(`config/topics.yaml` SSOT). 렌즈 패스(`run_enrich --mode lenses`)가 write, UI가 렌즈 필터·정렬에 read. 없으면 빈 배열 폴백(비파괴). id→type 해석은 topics.yaml.
- **`risk`·`impact`** (int 0~3) — dual score. **`risk_reason`·`impact_reason`** (str, advisory 근거 1줄). 점수 패스(`run_enrich --mode score`)가 write(`save_story_score`, merge·비파괴), UI가 정렬·임계 노출에 read. 없으면 미표시 폴백(비파괴). risk=렌즈/내러티브 정렬, impact=스토리·종목 정렬(설계 `analysis-design.md` §7).
- **`scored_count`** (int) — 이 멤버수까지 채점함(incremental 가드, `lensed_count`·`summary_count`와 동일 per-pass 컨벤션). **`scored_at`** (datetime) — 채점 시각.
- **`developments[].delta_time`** (datetime) — 그 전개가 새 정보로 우리 스토어에 처음 편입된 시각(`published_at`=발행시각과 구분되는 2번째 타임스탬프). 요약 패스(`run_enrich --mode summary`)가 write — milestone 게이트(LLM `is_new`)가 진짜 새 전개면 `time`, 단순 recap이면 기존 프런티어(`max(prior delta_time)`)에 귀속해 **새 델타로 앞서지 않게** 한다. 없으면 소비자가 `developments[].time`으로 폴백(additive·비파괴, 레거시 안전).
- **`developments[].event_time`** (datetime|null) — 그 전개의 **사건 실제 시각**(요약 패스가 본문에서 추출, ISO·sanity 검증, 실패 시 null). UI는 null이면 `time`(보도시각)으로 폴백. `delta_time`과 같은 추가 타임스탬프(비파괴·레거시 안전). **요약 패스 단독 writer**(article 패스는 안 건드림).
- **`headline`·`lead`·`article[]`** (str·str·string[]) — 생성 보고서. **article 패스**(`run_enrich --mode article`)가 write, UI가 헤드라인/리드/bullet로 read. **article 패스는 `developments`를 안 쓴다(자기 필드만 merge — 비파괴 by construction).** 없으면 UI 폴백(`headline`→`title`, `lead`→`summary`, `article`→생략).
- **`risk_ref`·`impact_ref`** (int 0~3) · **`score_ref_at`** (datetime) — 전일대비 24h 롤링 기준(article 패스 유지). UI가 `risk−risk_ref`로 ▲▼ 도출(ref 없으면 화살표 생략, best-effort). `NEW`는 `first_seen`만으로 판정(ref 무관).
- **`articled_count`** (int) · **`articled_at`** (datetime) — incremental 가드(`summary_count`·`scored_count`와 동일 per-pass 컨벤션).

## 핸드오프 프로토콜 — `processed` 플래그
1. newsstore가 raw item을 쓸 때 `processed=false`를 박는다(verified: `firestore_store.py` `_to_doc`).
2. 인리치 패스가 `processed==false`인 item을 오래된 순으로 끌어와(`get_unprocessed` 패턴) 인리치한다.
3. 끝나면 `processed=true, processed_at`을 merge로 기록(`mark_processed` 패턴).
- **고정 계약:** 필드명 `processed`(bool), 기본값 `false`, 방향(수집=false 생산, 인리치=true 소비). 어느 쪽도 이 의미를 임의로 바꾸지 않는다.

## 불변식 (계약 테스트로 강제 — FAIL-LOUD)
구두 약속이 아니라 테스트로 지킨다.
- **비파괴 merge** — 인리치 패스는 인리치 필드만 merge하고 raw 필드(title/body/url/published_at…)를 덮어쓰지 않는다.
- **스키마 드리프트 가드** — web UI가 읽는 인리치 필드명(`tags, story_id, stories.*`)이 바뀌면 터지는 계약 테스트. 이름이 조용히 어긋나면 사이트가 빈 화면이 된다.
- **Fail-soft 렌더** — 인리치 패스가 미실행/중단이면 인리치 필드가 없을 수 있다. UI는 그래도 raw 목록을 정상 렌더하고, 인리치 의존 컨트롤(태그 드롭다운·스토리 탭)은 우아하게 강등한다. `web/index.html`은 필드 가드(`it.tags || []`, `s.developments || []`, `Number(s.count) || …`, 빈-상태 폴백)로 `stories` 컬렉션이 비면 스토리 탭을 빈 목록으로 강등해야 한다. 이 강등 불변식을 회귀 테스트로 지킨다.

## 인프라
- Firestore 보안규칙(`items`·`stories` public read)·복합 인덱스는 newsstore가 적용한다(보안규칙 `docs/operations.md §C`, 복합 인덱스 §D).
- 비밀(`GEMINI_API_KEY`)은 백엔드 전용(SECRETS) — 클라이언트/커밋 금지.

## 공유 설정
- **`config/taxonomy.yaml`** — LLM 태거의 어휘/티커 검증용이다. **web UI는 taxonomy를 읽지 않고** `items.tags`에서 드롭다운을 도출한다(`refreshTagOptions`).
- **`config/feeds.yaml`의 `tier` 필드** — `feeds.yaml`은 수집기 SSOT다. 수집 패스가 `meta/sources`에 `{"sources":[...], "tiers":{source: tier}}`로 발행한다(`run_collect` → `source_tiers`, 첫 피드 우선). UI는 거기서 소스 등급을 읽는다. 파일을 복제하지 않는다(SSOT).
