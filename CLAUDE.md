# newsstore — 프로젝트 지침 (매 세션 자동 로드)

## 코드 원칙 (항상 적용)
1. **Single Source of Truth (SSOT)** — 같은 사실(피드 목록·설정값·상수)은 **한 곳에만** 정의하고, 나머지는 거기서 **도출(derive)**. 하드코딩 복제 금지.
2. **복제 말고 도출** — 어떤 리스트/설정이 다른 진짜 출처를 베낀 것이면 런타임/빌드에 끌어와라 (예: 사이트 소스 목록은 `config/feeds.yaml`에서 도출, `index.html`에 하드코딩 ❌).
3. **Fail-Loud** — 드리프트·계약 위반·잘못된 설정은 **조용히 통과시키지 말고** 테스트/검증으로 터뜨린다.
4. **강건성 > 작성자 정확성** — 한 군데 잘못 건드려도 전체가 조용히 깨지지 않게(생성 설정·계약·테스트). **Claude(나)의 정확성에 의존하는 구조를 만들지 말 것.**
5. **TDD** — 구현 전 실패 테스트. **검증 후 주장** — 성공 단언 말고 증거(로그/curl).
6. **비파괴 우선** — 원본 데이터는 보존, 필터·가공은 삭제가 아니라 표시(mark)로.
7. **Docker 전용 개발** — 로컬 Python 사용 **금지**. 모든 실행·테스트·빌드는 **Docker로만** (이 호스트엔 로컬 Python도 없음).
- 상세: `docs/coding-principles.md`

## 환경 (중요)
- 로컬 Python 없음 → **Docker로만** 실행/테스트.
  테스트: **`MSYS_NO_PATHCONV=1 docker compose run --rm test`** (Firestore 에뮬레이터 자동 기동 후 pytest). store 테스트는 에뮬레이터에 붙음 — `mock-firestore`·sqlite 제거됨(store 단일=Firestore).
- 설정은 루트 **`.env`** (`cp .env.example .env`): `APP_ENV` home|office · `GOOGLE_CLOUD_PROJECT` · `GCP_REGION` · `FMP_API_KEY`(비밀). **저장소=Firestore 단일**(로컬/테스트는 `FIRESTORE_EMULATOR_HOST`로 에뮬레이터; sqlite 백엔드 제거).
- **비밀 구분**: `FMP_API_KEY`·`GEMINI_API_KEY`는 **백엔드 전용 비밀**(클라이언트/커밋 금지 — `.env.example`엔 플레이스홀더만). Firebase 웹 apiKey는 **비밀 아님**(클라이언트 OK, 규칙이 데이터 보호).

## 어디를 볼까
- **스코프 (중요):** newsstore = **수집 전용**이다 — 뉴스 RSS 수집 + 가격·펀더멘털 수집(FMP) + Firestore 저장 + 정적 확인 UI. **생성형 LLM/분석/신호/리포트는 이 repo에 없다**(태깅·클러스터·스토리·렌즈·프레임·리포트·레이더 전부 제거). **단 하나의 예외 — 임베딩 벡터 계산**: 수집 후 패스가 story 기사를 gemini-embedding-001(768차원)로 임베딩해 `item_vectors`에 저장한다(다운스트림 재사용 — 분석이 아니라 수집 산출물). 필터는 비-LLM 규칙(중복 제거 + 스팸·스포츠·다이제스트 키워드 분류)이다. content 데이터엔 2개월(60일) TTL(`expire_at`, `feed_state` 제외).
- 현재 상태·아키텍처: `README.md`
- 운영·재배포: `docs/operations.md` · 최초 셋업: `docs/setup.md`
- Firestore 스키마 계약(TTL·kind·FMP 소스): `docs/firestore-contract.md`
- 코드 원칙 상세: `docs/coding-principles.md`
- 오답노트(해결 교훈, append-only): `docs/solved_problems.md`
- 서브에이전트 컨텍스트 주입: `docs/subagent-context.md`

## 관습 (항상)
- **문제·할일 발견 시** → **사용자에게 surface**(손유지 백로그 파일 금지 — 썩는다). 🔴(사용자 결정 필요)는 문서에 묻지 말고 **즉시 surface**.
- **해결 시** → 재사용 교훈을 `docs/solved_problems.md`(오답노트·append-only)에 기록(문제→원인→해결). 일반화 가능하면 `coding-principles`로 승격(중복 금지).
- **진행상태는 문서에 두지 않는다** — 의심되면 코드·gcloud로 재측정(상태 문서는 진실의 캐시일 뿐).
- **구현 전 `docs/solved_problems.md` 확인** — 같은 실수 반복 금지.
- **SDD/ultracode 서브에이전트엔 `coding-principles` + `solved_problems.md`의 '핵심 gotchas'를 주입**(전체 아카이브 X — 관련성>분량). 배선: `docs/subagent-context.md`. 서브에이전트는 세션 맥락이 없어 주입해야 실수를 안 반복한다.

## 배포 (요약, 상세는 operations.md)
- 코드/피드 변경 → 이미지 재빌드 → 세 수집 Job(collector·prices·stocks) 모두 `gcloud run jobs update --image` → execute (같은 이미지, CMD만 다름)
- 사이트(`web/index.html`) 변경 → Hosting REST 재배포
- gcloud가 PATH에 없으면 설치 풀경로로 호출(머신별로 다름 — `where gcloud`/설치 경로로 확인, 머신로컬 값은 메모리에). Firebase REST엔 `x-goog-user-project` 헤더 필수.
