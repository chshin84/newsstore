# news-analytics 위임 — newsstore가 요구하는 것 (계약 + 동작 보증)

_작성: 2026-06-28 · 성격: 요구자(newsstore) → 수행자(news-analytics) 위임서 · 회신(§E)을 받으면 이 문서를 갱신한다._

> **핵심 입장:** newsstore는 news-analytics의 **내부 구현을 지시하지 않는다.** 어떻게 만들든(현 코드 포팅·재작성·내부 재설계 무엇이든) 그건 news-analytics의 자유다. newsstore가 요구하는 것은 단 둘 — **(A) 인터페이스 계약 준수**와 **(B) 동작 보증**이다. 이 둘만 지켜지면 내부는 "어떻게든 돌아가든" 상관없다.
>
> **쓰는 법:** 아래 "전달 본문"을 그대로 복사해 news-analytics 세션에 전달한다. 계약의 SSOT는 `docs/firestore-contract.md`이며, 본문 §A는 그 요약이다.

---

## 전달 본문 (복사해서 news-analytics 세션에 전달)

### 0. 너의 정체성·관계
너는 **news-analytics** 라는 별개 repo에서 일한다. 자매 프로젝트 **newsstore**가 뉴스 **수집·저장·호스팅(웹 UI)**을 담당하고, **너는 분석/인리치 계층**(LLM 태깅·임베딩·스토리 클러스터·요약·점수)을 담당한다.

**두 repo는 코드로 결합하지 않는다. 유일한 이음새는 Firestore다.** 너는 newsstore를 import하지 않고 너의 Firestore 클라이언트로 직접 읽고 쓴다. GCP `daily-recap-498506`, 리전 `asia-northeast3`, Firestore `(default)` Native.

**내부 구현은 전적으로 너의 자유다.** newsstore는 아래 §A(계약)와 §B(보증)만 요구한다. 그 둘을 깨지 않는 한, 어떤 코드·알고리즘·구조로 만들지는 네가 정한다.

### A. 하드 계약 — Firestore 스키마 (이건 인터페이스라 못 바꾼다)
> SSOT: newsstore `docs/firestore-contract.md`. 아래는 자기완결 요약.

**컬렉션·소유권**

| 데이터 | 누가 쓰나 | 너의 동작 |
|---|---|---|
| `items` (raw: id, feed_id, source, asset_hint, language, url, title, body, published_at, fetched_at) | newsstore | **읽기만** |
| `items.processed=false, processed_at=null, tags=[]` (raw에 박혀 옴) | newsstore | "인리치 필요" 신호 |
| `items` 인리치 필드: `kind, tags[], embedding[768], story_id, processed=true, processed_at` | **너 (merge 쓰기)** | raw 필드 절대 덮어쓰지 마라 |
| `stories/{id}`: `title, centroid_sum[], count, member_ids[], entities[], first_seen, last_seen, status(open\|closed)` + 요약필드 `summary, latest, developments[{text,time,source_count}], summary_count, summary_at` | **너** | 생성·갱신 |
| `feed_state` | newsstore | **건드리지 마라** |
| `meta` (sources, source tier) | newsstore | **읽기만** |

- **핸드오프**: newsstore가 `processed=false`를 박는다 → 너는 미처리분을 읽어 인리치 → `processed=true, processed_at` **merge** 기록.
- **비파괴 merge**: 인리치 필드만 merge. raw 필드는 절대 덮어쓰지 마라.
- **스키마 안정**: 위 필드명(`tags`, `story_id`, `stories.*`)은 **newsstore 웹 UI가 그대로 읽는다.** 이름을 바꾸면 사이트가 깨진다. 바꿔야 한다면 §E로 newsstore와 합의 먼저.
- **임베딩 차원 768 고정.** 인덱스는 newsstore가 적용 — 필요한 인덱스는 §E로 요청.

### B. 동작 보증 — newsstore가 진짜 요구하는 것 (결과)
1. **연속성·무회귀** — 공개 사이트가 **지금만큼**(태그 필터·스토리 타임라인·요약) 끊김 없이 계속 동작한다. 전환으로 사용자가 보는 품질이 떨어지지 않는다.
2. **완결성** — 현재 라이브로 돌고 있는 기능을 **전부** 인수하고 스케줄대로 계속 돈다(클러스터·태깅/임베딩·스토리 요약). 일부가 조용히 멈추는 상태를 남기지 않는다.
3. **스무스 컷오버** — 현재 newsstore가 돌리는 인리치 Job에서 news-analytics로 **무중단 전환** + **롤백 경로**. 전환 중 이중 처리·데이터 손상 없음.
4. **Fail-soft + 관측** — 분석이 장애·중단되면 사이트는 raw 뉴스로 **우아하게 강등**(빈 화면 금지). 실패는 조용히 삼키지 말고 로그·지표로 **시끄럽게** 드러난다.
5. **비용** — 무료/소액($0 기조) 유지. 비용 늘면 §E로 보고.

### C. 참고 — 현재 동작 (강제 아님, 출발점일 뿐)
지금 인리치 파이프라인은 **newsstore 이미지에서 라이브로 돈다**(Cloud Run Job#2 cluster 10분 / Job#3 summary 시간당). 동작 결과를 빠르고 안전하게 재현하려면 **현 구현을 그대로 포팅하는 것이 가장 짧은 길**이다 — 레퍼런스 코드는 newsstore repo(예: `D:\projects\newsstore`)의 `src/newsstore/enrich/`, `entrypoints/run_enrich.py`, `config/taxonomy.yaml`, `tests/`, 인프라는 `Dockerfile`/`infra/cloudbuild.processor.yaml`/`docs/operations.md §E·§F`, 설계 근거는 `docs/superpowers/`의 step2·modular·story-summary 문서에 있다.

**하지만 포팅할지·다시 짤지·내부를 개선할지는 너의 결정이다.** §A·§B만 지키면 된다. (권장: 분리를 안전하게 하려면 v1은 동작 보존으로 가고, 개선은 컷오버 후 v2로. 단 이 순서도 강제 아님.) 상수·모델명은 코드가 SSOT다 — 특히 **Gemini 모델명은 `gemini.py`에서 읽어라**(README/roadmap엔 드리프트 있음).

### D. 검수 (Definition of Done)
1. **계약(§A) 일치** — Firestore 입출력 필드·핸드오프·비파괴가 계약대로. 검증 가능한 테스트로.
2. **보증(§B) 충족 증거** — 연속성(사이트 실측), 완결성(스케줄 동작 로그), 컷오버(무중단+롤백 시연), fail-soft(장애 주입 시 사이트 정상)를 **증거로** 보인다(주장만 금지).

### E. newsstore(요구자)에 회신할 것
1. **§A 스키마 합의 여부** — 그대로 가능한가? 불가피한 편차가 있으면 무엇·왜.
2. **newsstore에 필요한 작업** — 추가 Firestore 인덱스 목록, `meta`에 source **tier** 발행 필요 여부(현재 싣는지 불확실 — 미포함이면 newsstore가 추가).
3. **컷오버 계획** — 언제 전환 가능, 롤백 방법.
4. **막힌 점·질문**.

---

## 회신 로그 (news-analytics → newsstore)
_§E 회신을 받으면 여기 기록하고, newsstore 반영(인덱스 추가·tier 발행·모델명 교정 등)을 추적한다._

### 1회차 — 2026-06-28 (news-analytics `phase1-clusterer`, 커밋 `ccdeb82`)
> 출처: news-analytics repo의 `docs/handoff/2026-06-28-news-analytics-v1-response.md`. **이 repo에는 없음**(별 repo) — 아래는 newsstore 세션에 전달된 요약 기준. 인덱스 2종의 정확한 필드 스펙 등 일부는 원문 미확보.

**news-analytics가 회신한 것 (§E)**
- §A 스키마: **합의**. 단 비파괴 merge·`processed` 핸드오프는 news-analytics 측 **어댑터**가 담당하기로(내부 구현).
- 결정(HOW=수행자 재량): 현 코드 포팅 대신 **로직만 라이브러리로 추출 + newsstore 어댑터 잔류**.
- newsstore에 요청: **Firestore 인덱스 2종 추가**(정확 스펙은 원문), `meta`에 source **tier 발행**(패리티 우선).
- 컷오버: **섀도우 실행 후 전환** 제안.
- **블로커 5건**을 newsstore에 되물음(아래). 1번은 🔴(사용자 결정).
- B1(연속성·무회귀)·D(DoD)는 **현재 미보증** — 클러스터 과병합 블로커 해소 전까지 정직하게 보류 표기.

**news-analytics의 5개 질문 → newsstore 답 (코드 실측, file:line)**
1. 🔴→✅ **클러스터러 방향 = (a) gray-band LLM 주입** (사용자 결정 2026-06-28, news-analytics 권장 수용). 임계값 근처 gray band의 모호한 쌍에 LLM "같은 사건?" 판정을 끼워 과병합을 실제로 줄인다. **함의: v1은 엄격한 동작 보존을 벗어나 gray-band LLM을 승인된 스코프로 포함한다.** 단서 — 추가 LLM 호출이 §B5(비용) 무료/소액 기조를 깨지 않도록 무료 tier 한도(RPM/RPD)를 점검하고, 넘으면 §E로 보고. gray-band 호출도 `gemini-3.1-flash-lite-preview` 사용(아래 3번).
2. **임베딩 모델 정체성** — 현 프로덕션 `embedding[768]`은 **`gemini-embedding-001` + `output_dimensionality=768`** 으로 생성(`gemini.py:53-54,86-96`). 모델 네이티브 3072차원을 768로 절단; **정규화·`task_type` 미적용**. 임계값도 이 모델로 실데이터 캘리브레이션됨(`cluster.py:14-18`). ⚠️ 과거 일부 벡터는 폐기된 Vertex 임베딩일 수 있음 — 기존 centroid와 비교하려면 news-analytics는 **동일 모델·동일 768·무정규화**를 그대로 써야 함.
3. **gray-band/태깅 LLM + 키 정책** — JSON 생성(태깅·요약, gray-band 호출도 동일)은 **`gemini-3.1-flash-lite-preview`**(`gemini.py:53`, env `GEMINI_MODEL`로 오버라이드 가능, `run_enrich.py:66-69`). 키는 **env `GEMINI_API_KEY`(백엔드 전용 비밀)**, Gemini Developer API 경로(Vertex/ADC 아님, `run_enrich.py:59-61`). **"무료 tier 확정"은 코드가 모르는 운영 사실** — 키의 결제 설정에 달림. 권장: news-analytics **전용 키(별도 Secret)**로 쿼터·blast-radius 분리(가역, 기능상 공유도 가능).
4. **kind enum · asset_hint** — `kind ∈ {story, spam, digest}` 닫힌 집합(`classify.py:16-24`); `story`만 embed/cluster, spam·digest는 kind만 저장(비파괴, `processor.py:87-90`). `asset_hint`는 **자유 문자열**(enum 아님), 기본 `""`(`models.py:10`); 수집 시 `feeds.yaml`이 채움(예: `kr_bond,kr_fx`·`us_stock`·`crypto`·`commodity`·`etf`…, 콤마 결합 가능) — **허용값 SSOT = `config/feeds.yaml`**.
5. **story open→closed 트리거** — 생성 시 open(`create_story`), 멤버 합류 시 `last_seen` 갱신(`append_to_story`, `processor.py:106-111`). **`last_seen < now - CLOSE_AFTER(24h)`** 이면 `close_stale_stories`가 close(매 cluster 패스 실행, `processor.py:18,93`·`run_enrich.py:41`). `OPEN_WINDOW(48h)`는 매칭 후보창(벡터 인덱스 시딩, `processor.py:17`·`run_enrich.py:28`). 쿼리 술어 byte-level SSOT는 `firestore_store.close_stale_stories/get_open_stories`.

**newsstore 측 TODO (회신 반영)**
- [ ] **Firestore 인덱스 2종 추가** — 정확한 필드 스펙 미확보(회신 원문이 별 repo). news-analytics 또는 사용자가 스펙 제공 시 적용.
- [ ] **`meta`에 source `tier` 발행** — `feeds.yaml`엔 `tier: analysis|wire` 존재(미기재=기본). meta 발행 배선 확인/추가 필요(과도기 처방).
- [ ] (문서 드리프트) README/roadmap의 Gemini 모델명을 `gemini.py` 기준으로 교정 — 코드가 SSOT.

**진행 (🔴 해소됨)**
- 1번 결정 (a)로 B1(무회귀)·D(DoD)는 **gray-band 적용 기준**으로 다시 평가한다(과병합 감소를 회귀가 아닌 개선으로 본다). news-analytics는 gray-band 포함 v1을 구현하고, §D 증거(계약 테스트 + 과병합 개선 시연)를 제출한다.

---

## newsstore → news-analytics 회신 (이 블록을 복사해 전달)

§E 회신 잘 받았다. 스키마 합의·어댑터 방식·섀도우 컷오버 모두 OK. 5개 되물음에 답한다.

1. **클러스터러 방향: (a) gray-band LLM 주입으로 간다** (요구자 승인). 임계값 근처 모호한 쌍만 LLM "같은 사건?" 판정으로 과병합을 줄여라. 이로써 v1은 동작 보존을 일부 벗어나 gray-band를 포함하는 것으로 스코프 확정. **단, §B5(비용) 유지** — 무료 tier 한도(RPM/RPD)를 점검하고 초과 위험이 보이면 즉시 보고. gray-band 호출 모델은 아래 3번과 동일하게.
2. **임베딩 모델 정체성**: 현 프로덕션 `embedding[768]` = `gemini-embedding-001` + `output_dimensionality=768`(네이티브 3072 절단), **정규화·task_type 미적용**. 기존 centroid와 비교하려면 동일 모델·동일 768·무정규화를 그대로 써라. ⚠️ 과거 일부 벡터는 폐기된 Vertex 임베딩일 수 있으니, 혼재 시 재임베딩 정책을 §E로 협의.
3. **태깅/요약/gray-band LLM**: `gemini-3.1-flash-lite-preview`(env `GEMINI_MODEL`로 오버라이드 가능). 키는 백엔드 전용 `GEMINI_API_KEY`(Gemini Developer API 경로). **무료 tier 여부는 키의 결제 설정 문제**라 코드가 보장 못 함 — news-analytics **전용 키(별도 Secret)** 사용을 권장(쿼터·blast-radius 분리).
4. **enum**: `kind ∈ {story, spam, digest}`(story만 embed/cluster). `asset_hint`는 자유 문자열(enum 아님), 허용값 SSOT는 newsstore `config/feeds.yaml`(예: `us_stock`·`crypto`·`commodity`·`kr_bond,kr_fx`…).
5. **story 수명주기**: 생성 시 open → 멤버 합류 시 `last_seen` 갱신 → `last_seen < now-24h`(`CLOSE_AFTER`)면 close. 매칭 후보창은 `OPEN_WINDOW=48h`. 정확한 쿼리 술어는 newsstore `firestore_store.close_stale_stories/get_open_stories`가 SSOT.

**newsstore가 처리할 것**: (i) 요청한 Firestore 인덱스 2종 — **정확한 필드·정렬 스펙을 회신해 달라**(원문이 너희 repo라 이쪽에서 못 읽음), 받는 대로 적용. (ii) `meta`에 source `tier` 발행 배선. (iii) README/roadmap 모델명 드리프트 교정.
