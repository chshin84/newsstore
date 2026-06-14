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
> **다음 = Plan 3**(Gemini Flash 태깅+리뷰어 + 임베딩 Tier3), Plan 4(Processor+배포).
> **이연(후속 Plan에서)**: ① classify SPAM_SIGNALS가 web/index.html JUNK와 *전이적 중복*(view가 `kind` 읽으면 근본해소) — **2026-06-14: 드리프트 가드 테스트(`tests/test_spam_signals_drift.py`) 추가로 최소 안전망 확보**(set 동등성 fail-loud). 근본 해소(뷰→kind 쿼리, JUNK 제거)는 Plan 3/4 잔여. ~~② `cosine` 차원불일치 assert~~ → **2026-06-14 해소**(`cosine`/`add_vectors` ValueError + 두 스토어 도출, `solved_problems.md` 참조). ③ `assign`의 open_stories TypedDict화(미해소, low) ④ classify 제목·본문 접합 false-positive(미해소, 본문 파이프라인 연결 전 수정 권장).
- **새 처리기 `src/newsstore/processor.py`(가칭)** — `get_unprocessed` → 선필터(kind) → 임베딩 → centroid 클러스터 → `mark_processed`. (Cloud Run Job #2 + Scheduler)
- **`kind` 마킹(비파괴)** — story/spam/digest 분류를 저장. → **뷰의 `JUNK` 스팸필터를 백엔드로 이사**(브라우저마다 계산 X, 한 번 계산해 저장). → 뷰는 `kind == story` 쿼리.
- **Bloomberg ", More" 다이제스트 선필터** — 패턴 분명(`, More` / `Balance of Power` / `(Podcast)`), 클러스터 전 제외. (스팸필터와 같은 위치)
- **`stories` 컬렉션 + 중심핵** — `{title(LLM 캐노니컬), centroid_sum, count, member_ids(타임라인), entities, first/last_seen, status}`. `items`에 `embedding/story_id/kind` 추가.
- **프로덕션 임베딩 = Gemini Tier3 키** — `.env`에 `GEMINI_API_KEY` 넣음(사용자), **코드 연결 미완**. 스파이크는 Vertex(검증용).
- **복합 인덱스** — Step-2 쿼리용 추가 필요 시(스토리/태그). 기존 `source/tags/processed` READY.
- **(2026-06-14 감사) Plan 3 선결**: ① Plan 3/4 SDD 계획 파일 부재 → `writing-plans`로 작성. ② `google-genai` 의존성·lock·Dockerfile build-arg 미준비(SDK는 google-genai 권장 — GEMINI_API_KEY=Developer API 경로, vertexai 아님). ③ Gemini 호출 비기능요건(timeout/retry/None가드/구조화출력 파싱실패 가드/비용·쿼터 상한/배치10건/리뷰어/로깅) 코드 전무 → 구현 시 `disciplined-coder:advisor-nonfunctional` 주입.
- **(2026-06-14 감사) Plan 4 선결 — 뷰 read 계약 공백**: base.py Store Protocol에 인리치 결과 read 경로 부재. `get_open_stories`는 클러스터 전용(centroid만, title/member_ids 없음). 추가 필요: `get_items_by_kind(kind='story', ...)`(spec §4 'kind==story 읽기' 뒷받침) + `list_stories(status, since)`(뷰 타임라인). 양쪽 스토어 구현 + Protocol 드리프트 테스트. story_id 생성은 Processor 내부 `uuid4()`로 충분(Store 계약 불필요).
- **(2026-06-14 감사) Plan 4 배포 인프라**: Processor 엔트리포인트(`src/newsstore/process.py`)·Cloud Run Job#2(`newsstore-processor`, 단일이미지+CMD 오버라이드 권장)·Scheduler#2·Secret Manager로 `GEMINI_API_KEY` 주입(`--update-secrets`, SA에 secretAccessor)·operations.md/setup.md 절차 추가.
- **(2026-06-14 감사, low) 잔여 견고성 드리프트**: ① `append_to_story` member_ids가 published_at 순 미보장(spec §4 타임라인 계약) + member_id 중복 비방지(save+mark 비원자 시 재처리로 이중카운트) ② firestore N+1 read·비원자 RMW(close_stale batch화, get_open `where` 쿼리화) ③ sqlite `get_open_stories` count==0 가드 부재(firestore는 `or 1` — 비대칭) ④ firestore tz/누락 last_seen 가드가 sqlite와 비대칭 ⑤ `taxonomy.yaml` topics 표기(`energy`)가 spec §6(`energy/oil`)과 드리프트 ⑥ `load_taxonomy` 미지 키·빈 축 무음 통과 ⑦ `body_mode: calendar` 선언만·미구현(조용히 summary 폴백).

## 🔵 향후 / 선택
- **Phase 2 — 스토리 타임라인 UI** — 스크린샷처럼 같은 내러티브를 타임라인으로(속보 N건). Phase 1이 `stories` 채운 뒤.
- **서비스 단위 src 분할** — `src/newsstore/{collector,enrichment,store}` — Step-2 착수 시 자연스럽게.
- **보안 강화(선택)** — Firebase App Check / apiKey HTTP 리퍼러 제한(읽기 quota 남용 차단). 무료티어라 당장 불필요.
- **Step 4~7(아키타입·시나리오·국면)** — `docs/roadmap.md`. ultracode(병렬 팬아웃) 적합.

## 참고 — 이미 닫혔지만 기록
- "드리프트 감지 테스트"(SRC_ORDER) → **SSOT로 중복 자체 제거**되어 불필요해짐(테스트할 드리프트가 없음).
