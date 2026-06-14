# 미해결 / 대기 문제 (unsolved_problems)

발견됐으나 아직 안 끝난 것 + 사용자 결정이 필요한 것. (해결되면 `solved_problems.md`로 이동.)
범례: 🔴 사용자 결정 필요 · 🟡 방향 정해짐·구현 대기 · 🔵 향후/선택.

> ⚠️ **서브에이전트(worker) 주입 금지.** 이건 오케스트레이터/사용자용 백로그다. 격리된 worker가 받으면 🔴(사용자 결정 대기)를 "구현하라"로 오인 → 임의 구현 **사고**. 주입해야 한다면 "참고·구현 금지" 명시 + 🔴는 **사용자 승인 게이트** 뒤. (원칙 4: 구조가 실수를 막는다)

## 🔴 결정 필요
- **infra.md 스킬 / docker-compose 부활** — 결론: infra **파일**(Dockerfile/cloudbuild)은 도구가 먹는 실파일이라 .md로 갈음 불가, "클론→셋업" 목표는 setup.md+.env.example로 이미 충족. **docker-compose를 Docker-only 편의용(린한 test/collect 서비스)으로 되살릴지**는 사용자 선택 대기.
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
- ✅ ~~(감사) Plan 3 선결: Plan 문서·google-genai extra·비기능요건~~ → 2026-06-14 해소(Plan 3 구현). lock 재생성만 배포 게이트로 잔존(위).
- **(2026-06-14 감사, low) 잔여 견고성 드리프트**: ① `append_to_story` member_ids가 published_at 순 미보장(spec §4 타임라인 계약) + member_id 중복 비방지(save+mark 비원자 시 재처리로 이중카운트) ② firestore N+1 read·비원자 RMW(close_stale batch화, get_open `where` 쿼리화) ③ sqlite `get_open_stories` count==0 가드 부재(firestore는 `or 1` — 비대칭) ④ firestore tz/누락 last_seen 가드가 sqlite와 비대칭 ⑤ `taxonomy.yaml` topics 표기(`energy`)가 spec §6(`energy/oil`)과 드리프트 ⑥ `load_taxonomy` 미지 키·빈 축 무음 통과 ⑦ `body_mode: calendar` 선언만·미구현(조용히 summary 폴백).

## 🔵 향후 / 선택
- **Phase 2 — 스토리 타임라인 UI** — 스크린샷처럼 같은 내러티브를 타임라인으로(속보 N건). Phase 1이 `stories` 채운 뒤.
- **서비스 단위 src 분할** — `src/newsstore/{collector,enrichment,store}` — Step-2 착수 시 자연스럽게.
- **보안 강화(선택)** — Firebase App Check / apiKey HTTP 리퍼러 제한(읽기 quota 남용 차단). 무료티어라 당장 불필요.
- **Step 4~7(아키타입·시나리오·국면)** — `docs/roadmap.md`. ultracode(병렬 팬아웃) 적합.

## 참고 — 이미 닫혔지만 기록
- "드리프트 감지 테스트"(SRC_ORDER) → **SSOT로 중복 자체 제거**되어 불필요해짐(테스트할 드리프트가 없음).
