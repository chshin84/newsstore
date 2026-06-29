# 미해결 / 대기 문제 (unsolved_problems)

발견됐으나 아직 안 끝난 것 + 사용자 결정이 필요한 것. (해결되면 `solved_problems.md`로 이동.)
범례: 🔴 사용자 결정 필요 · 🟡 방향 정해짐·구현 대기 · 🔵 향후/선택.

> ⚠️ **서브에이전트(worker) 주입 금지.** 이건 오케스트레이터/사용자용 백로그다. 격리된 worker가 받으면 🔴(사용자 결정 대기)를 "구현하라"로 오인 → 임의 구현 **사고**. 주입해야 한다면 "참고·구현 금지" 명시 + 🔴는 **사용자 승인 게이트** 뒤. (원칙 4: 구조가 실수를 막는다)

## 🔴 결정 필요
- **본문 스크래핑 정책 오버라이드 (한경 body 인리치 spec)** — *증상/트리거*: spec `docs/superpowers/specs/2026-06-28-body-enrichment-korean-design.md`(타 세션 작성, untracked)가 한경 6피드의 **개별 기사 페이지 fetch로 본문 채움**을 제안. 그러나 `operations.md:151,157`이 "**기사 페이지 스크래핑은 안 함**(Cloud Run IP 차단·JS렌더·리다이렉트로 fragile), 본문 부족하면 피드 추가"로 **이미 결정**해 둠. spec은 이를 "wholesale 긁기만 금지였다"고 재해석하며 "사용자 의도상 허용"이라 주장하나, **그 승인 맥락은 이 세션에서 검증 불가**. domain-spec-review 3렌즈 중 grounding·adversarial이 동일 critical 지목 → **escalated**(spec 마커 escalated). *처방(다음엔 이렇게)*: 사용자가 **무스크래핑 정책 오버라이드를 명시 승인**해야 진행. 승인 시 ⓐ operations.md 정책 줄도 같이 갱신(SSOT 드리프트 방지) ⓑ 구현 전 아래 major 4건 반영. **🔴 누구도 자율 구현 금지.**
  - (review major, 승인 시 반영) ① **동시 폴링 레이스** — `filter_new_ids`가 upsert 전이라 폴 겹치면 같은 항목 이중 fetch 가능(가드 없음). ② **레이트리밋 부재** — 폴당 신규 N건을 연속 동기 GET → 프로덕션 IP 차단 위험(repo의 IP-비대칭 교훈 직결). ③ **드리프트 수동탐지** — 빈본문률 로그만 있고 알람 임계 없음(한경 HTML 변경 시 조용히 헤드라인 강등). ④ **타임아웃 미명시** — `fetch_body`가 ssl_config 기본 90s 상속, 한 기사 hang이 피드 전체 90s 블록. (consistency 렌즈는 무결, minor `filter_new_ids`는 "새 메서드"인데 spec이 "기존 로직 재사용"으로 오기 — §4.2 문구 교정 권장.)
- ~~**infra.md 스킬 / docker-compose 부활**~~ — **해소.** infra **파일**(Dockerfile/cloudbuild)은 도구가 먹는 실파일이라 .md로 갈음 불가(결론 유지). docker-compose는 **이미 부활됨**(커밋 e6acedb, 린 test/collect 서비스 — `docker compose run --rm test`). 결정 대기 아님.
- **Step-2 태그 통제 어휘(vocabulary)** — 어디까지 한정할지(티커 유니버스 / 엔티티: 연준·ECB·BOJ·재무부·OPEC… / 토픽: 금리·인플레·채권·FX·크립토·실적·M&A·지정학…). "이란 전쟁" 류 *사건*은 태그가 아니라 *스토리(클러스터)*로 잡기로 함.
- **태깅 LLM 선택** — Haiku vs Gemini Flash (둘 다 무료/저가). 임베딩이 Gemini면 한 provider 이점.
- **스토리 open/close 시간창** — 새 기사를 어느 기간의 "열린 스토리"와 비교할지(예 24~48h), 언제 close.

## 🟡 구현 대기 (Step-2 인리치먼트 — 설계·검증 완료, 일부 구현)
> spec: `docs/superpowers/specs/2026-06-13-newsstore-step2-enrichment-design.md`. 검증: 스파이크(centroid T≈0.83, 30건/~12초).
> **✅ Plan 1(순수 로직) 완료** — `src/newsstore/enrich/`(taxonomy·classify·cluster), 65 passed.
> **✅ Plan 2(Store 확장) 완료** — `save_enrichment`·stories(create/append centroid·get_open·close_stale) 양쪽 스토어, 72 passed. (`docs/superpowers/plans/2026-06-13-step2-store-ext.md`)
> **✅ Plan 3 완료(2026-06-14)** — `enrich/llm.py`(GeminiClient + retry/None가드/LLMError, DI)·`tagger.py`(결정론 어휘/티커 적합성 검증)·`embedder.py`(768 dim 가드). 92 passed. (`docs/superpowers/plans/2026-06-14-step2-llm-tagging.md`)
> **✅ Plan 4 로직 완료(2026-06-14)** — `enrich/processor.py::process_once` + `process.py` 엔트리포인트 + Dockerfile `INSTALL_ENRICH`/cloudbuild.processor + operations §E. 96 passed. **배포는 사용자 게이트**(아래). (`docs/superpowers/plans/2026-06-14-step2-processor-deploy.md`)
> **남은 것 = 라이브 배포 + Phase 2 뷰.**
> **이연(후속 Plan에서)**: ① classify SPAM_SIGNALS가 web/index.html JUNK와 *전이적 중복*(view가 `kind` 읽으면 근본해소) — **2026-06-14: 드리프트 가드 테스트(`tests/test_spam_signals_drift.py`) 추가로 최소 안전망 확보**(set 동등성 fail-loud). 근본 해소(뷰→kind 쿼리, JUNK 제거)는 Plan 3/4 잔여. ~~② `cosine` 차원불일치 assert~~ → **2026-06-14 해소**(`cosine`/`add_vectors` ValueError + 두 스토어 도출, `solved_problems.md` 참조). ③ `assign`의 open_stories TypedDict화(미해소, low) ④ classify 제목·본문 접합 false-positive(미해소, 본문 파이프라인 연결 전 수정 권장).
- **새 처리기 `src/newsstore/processor.py`(가칭)** — `get_unprocessed` → 선필터(kind) → 임베딩 → centroid 클러스터 → `mark_processed`. (Cloud Run Job #2 + Scheduler)
- **`kind` 마킹(비파괴)** — story/spam/digest 분류를 저장. → **뷰의 `JUNK` 스팸필터를 백엔드로 이사**(브라우저마다 계산 X, 한 번 계산해 저장). → 뷰는 `kind == story` 쿼리.
- **Bloomberg ", More" 다이제스트 선필터** — 패턴 분명(`, More` / `Balance of Power` / `(Podcast)`), 클러스터 전 제외. (스팸필터와 같은 위치)
- **`stories` 컬렉션 + 중심핵** — `{title(LLM 캐노니컬), centroid_sum, count, member_ids(타임라인), entities, first/last_seen, status}`. `items`에 `embedding/story_id/kind` 추가.
- **프로덕션 임베딩 = Gemini Tier3 키** — `.env`에 `GEMINI_API_KEY` 넣음(사용자), **코드 연결 미완**. 스파이크는 Vertex(검증용).
- **복합 인덱스** — Step-2 쿼리용 추가 필요 시(스토리/태그). 기존 `source/tags/processed` READY.
- **🔴 Plan 4 배포 (사용자 게이트, 라이브)**: ① `infra/requirements.lock`에 google-genai 추가·재생성(constraints라 미포함 시 빌드 실패; httpx<1.0 등 핀 충돌 해소). ② 라이브 스모크(소량 실태깅·실임베딩, 768 dim 확인). ③ operations.md §E대로 배포(비밀 생성→processor 이미지 빌드→Job#2→Scheduler#2). 코드·문서·cloudbuild는 준비됨, 빌드/키 주입만 남음.
- **🟡 Phase 2 뷰 read 계약 (사이트 UI)**: base.py Store Protocol에 `get_items_by_kind(kind='story', ...)`(spec §4) + `list_stories(status, since)` 추가(양쪽 스토어 + Protocol 드리프트 테스트) → web/index.html이 backend `kind`/`stories` 쿼리(클라이언트 JUNK 필터 제거 → SPAM SSOT 근본해소). `get_open_stories`는 클러스터 전용(centroid만)이라 뷰엔 부적합.
- **🔵 요약 패스가 `count<2` 단일 스토리도 요약 (경미·비용)** — (2026-06-15 Step-3 라이브 후 발견) `get_stories_needing_summary`는 `count>summary_count`만 보고 `count>=2`는 안 본다. 그러나 사이트 스트립은 `count>=2`만 표시 → **표시 안 되는 단일-기사 스토리에 flash-lite 콜이 낭비**(예: 칸예/킴 가십 단건). 해소=`get_stories_needing_summary`의 파이썬 필터에 `count>=2` 추가 + 테스트 1개 + 이미지 재빌드·`newsstore-summarizer`/`newsstore-enricher` 이미지 갱신(operations §F 0). 비용 작아 즉시성 낮음.
- ✅ ~~(감사) Plan 3 선결: Plan 문서·google-genai extra·비기능요건~~ → 2026-06-14 해소(Plan 3 구현). lock 재생성만 배포 게이트로 잔존(위).
- **(2026-06-14 감사, low) 잔여 견고성 드리프트**: ① `append_to_story` member_ids가 published_at 순 미보장(spec §4 타임라인 계약) + member_id 중복 비방지(save+mark 비원자 시 재처리로 이중카운트) ② firestore N+1 read·비원자 RMW(close_stale batch화, get_open `where` 쿼리화) ③ sqlite `get_open_stories` count==0 가드 부재(firestore는 `or 1` — 비대칭) ④ firestore tz/누락 last_seen 가드가 sqlite와 비대칭 ⑤ `taxonomy.yaml` topics 표기(`energy`)가 spec §6(`energy/oil`)과 드리프트 ⑥ `load_taxonomy` 미지 키·빈 축 무음 통과 ⑦ `body_mode: calendar` 선언만·미구현(조용히 summary 폴백).

## 🟡 Phase D 후속 (인리치 배포됨 — 리뷰 권고 follow-up)
- **잡 실패 알림** — Scheduler는 잡을 `:run`으로 띄우고 **수락(200)만 받음 → 잡이 죽어도 Scheduler는 초록**(Fail-Loud 위반). Cloud Monitoring 알림(`newsstore-enricher` 실패 카운트>0) 추가 필요.
- **requirements.lock에 google-genai 핀** — 현 processor 이미지는 google-genai를 unpinned로 해소(빌드는 됨). 재현성 위해 lock 재생성(전이의존 포함) 권장.
- **Pass 2(스토리 태깅) 자동화** — 현재 cluster pass만 10분 자동화. 태깅은 수동(`--mode tag`). 별 Scheduler/주기 결정.
- **인덱스 배포 확인** — `firestore.indexes.json`의 복합 인덱스가 실 Firestore에 READY인지(에뮬레이터는 인덱스 무시 → 계약 가드 테스트만으로는 실배포 미보장).

## 🟡 Phase 4 후속 (스토리 리포트 리더 — 배포됨 2026-06-29, 캘리브레이션 잔여)
> 코드·테스트·배포 완료(main 머지·푸시, 4 Job + 스케줄러 3개 lens→score→article 순, Hosting 재배포, 프로덕션 article 11건 생성 확인). 설계 SSOT: spec `docs/superpowers/specs/2026-06-29-phase4-story-report-ui-design.md`. (과도기 `HANDOFF-phase4.md`에서 이관 — 그 파일이 가리킨 PC-로컬 메모리 `phase4-story-report.md`는 회사 PC에만 있고 집 PC엔 부재라, 유실 방지차 여기로 옮김.)
- **🔴 캘리브레이션 (provisional 동작 중 — 라이브 데이터로 사용자가 튜닝, 자율 변경 금지)**: 0~3 스케일 의미·게이트 임계·`REF_WINDOW`(현 24h)·헤드라인 delta 가중·`EVENT_SANITY_DAYS`(현 14). 라이브 분포를 보고 조정.
- **라이브 모니터링**: article 생성 품질(헤드라인/리드/bullet), scorer risk/impact 분포, 렌즈 커버리지, 일일 비용($3 상한 내).
- (참고, TODO 아님) `event_time`는 summary가 새 멤버 붙을 때마다 점진 백필 — 기존 스토리는 보도시각 폴백(자동).

## 🟡 Phase 4 마무리 + 위생 백로그 (2026-06-29 4영역 코드 감사)
> 리포트 탭 착수 전 선결 정리. 6개 패스 코드는 라이브지만 spec 대비 미완·드리프트가 남음(roadmap/HANDOFF "완료"가 과장이었음 — 실측으로 교정). 아키타입(응용레이어) 제외. 증상 → 처방.
### 주요 (계획됐는데 안 돌거나 반쪽)
- **Phase 4 UI 부분구현 (`web/index.html`)** — spec `2026-06-29-phase4-story-report-ui-design` §7·§8 대비: ① **렌즈별 섹션 그룹화·risk순 정렬 없음**(현재 전체 스토리 단순 나열, 라인~517-524) ② **번역/원문 토글 동작 안 함**(버튼·리스너만, `renderDetail`이 `detailMode` 미사용) ③ **impact 임계 숨김 없음**(`count>=2`만 필터). *처방*: 렌즈 groupBy→섹션 헤더→섹션 내 최대 risk 정렬; `detailMode==='original'` 분기로 멤버 원문 전개; `IMPACT_THRESHOLD` 상수+필터(캘리브레이션 대기).
- **sports kind 미구현 (enrich+UI 가로지름)** — `classify.py:16-24` `classify_kind()`가 story/spam/digest만 반환(analysis-design §4가 요구한 `sports` 누락) → 스포츠 마킹도, UI 숨김도 불가. *처방*: classify에 sports 신호+kind 추가, 그다음 UI 스토리탭 필터 `it.kind!=='sports'`.
- **운영 런북 누락** — `operations.md`에 lens/score/article Job·Scheduler 절차 없음(enricher·summarizer만). `deploy-office.ps1`도 3개 잡 미포함. *처방*: operations.md에 3패스 Job 생성/갱신/실행/로그 절차 + deploy-office.ps1에 3잡 추가.
- **잡 실패 무음** — (기존 Phase D 항목과 동일) Scheduler 200만 수락→잡 死에도 초록. *처방*: Cloud Monitoring 알림(job 실패 카운트>0, lens/score/article/enricher 전부).
### 견고성 부채 (`firestore_store.py` — 지금 돌지만 동시성·규모에서 깨짐; §34와 중복 통합)
- `append_to_story`: member_ids **정렬 미보장 + 중복 방지 없음 + 비원자 RMW**(count·centroid 증분 손실). *처방*: published_at 정렬 유지 + `if member_id not in members` + `FieldValue.increment()`/transaction.
- `close_stale_stories`: **N+1 쓰기** → `batch()` 청크.
- **requirements.lock google-genai 미핀** — (기존 Phase D 항목) 재현성. lock 재생성.
### 사소·선택·정리
- `body_mode: calendar` 선언만(무음 summary 폴백, `parser.py`) → 구현/제거/`NotImplementedError` 택1 · `taxonomy` energy/oil 명칭 드리프트 · `load_taxonomy` 미지키 무음(fail-loud화) · 복합인덱스 READY 실확인(`gcloud firestore indexes`) · feeds.yaml `tier` → `meta` 발행 배선.
### 대조 (에이전트 과대평가 교정)
- store 감사가 "`get_items_by_kind`/`list_stories` 미구현=blocker"라 했으나 feed-kind-filter(756f106)로 클라이언트가 backend `kind`를 읽어 필터 → SSOT 목표 사실상 달성, 쿼리 백엔드 이전은 순도 문제(사소). ✅ 완료 확인: event_time 추출·per-story lead·fail-soft 렌즈라벨.

## 🔵 향후 / 선택
- **Phase 2 — 스토리 타임라인 UI** — 스크린샷처럼 같은 내러티브를 타임라인으로(속보 N건). Phase 1이 `stories` 채운 뒤.
- **서비스 단위 src 분할** — `src/newsstore/{collector,enrichment,store}` — Step-2 착수 시 자연스럽게.
- **보안 강화(선택)** — Firebase App Check / apiKey HTTP 리퍼러 제한(읽기 quota 남용 차단). 무료티어라 당장 불필요.
- **Step 4~7(아키타입·시나리오·국면)** — `docs/roadmap.md`. ultracode(병렬 팬아웃) 적합.

## 참고 — 이미 닫혔지만 기록
- "드리프트 감지 테스트"(SRC_ORDER) → **SSOT로 중복 자체 제거**되어 불필요해짐(테스트할 드리프트가 없음).
