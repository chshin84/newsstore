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
- 설정은 루트 **`.env`** (`cp .env.example .env`): `APP_ENV` home|office · `GOOGLE_CLOUD_PROJECT` · `GCP_REGION`. **저장소=Firestore 단일**(로컬/테스트는 `FIRESTORE_EMULATOR_HOST`로 에뮬레이터; sqlite 백엔드 제거).
- **비밀 구분**: `GEMINI_API_KEY`는 **백엔드 전용 비밀**(클라이언트/커밋 금지). Firebase 웹 apiKey는 **비밀 아님**(클라이언트 OK, 규칙이 데이터 보호).

## 어디를 볼까
- **스코프 경계 (중요):** newsstore = **수집·저장·호스팅(UI)**. **인리치/분석(LLM 태깅·임베딩·클러스터·스토리·risk/impact·아키타입)은 별개 repo `news-analytics` 소유** — 두 repo는 **Firestore 스키마로만** 결합(코드 import 없음). 경계·계약 SSOT: **`docs/firestore-contract.md`**. (과도기: `src/newsstore/enrich/` 코드와 Job#2/#3이 아직 newsstore에서 운영 중 — 물리 이전은 별도 작업.)
- 현재 상태·아키텍처: `README.md`
- 운영·재배포: `docs/operations.md` · 최초 셋업: `docs/setup.md`
- 로드맵(Step 1~7): `docs/roadmap.md`
- 코드 원칙 상세: `docs/coding-principles.md`
- 문제 로그: `docs/solved_problems.md`(해결) · `docs/unsolved_problems.md`(미해결)
- 서브에이전트 컨텍스트 주입: `docs/subagent-context.md`

## 관습 (항상)
- **문제 발견 시** → `docs/unsolved_problems.md`에 기록(맥락 충분히). **사용자에게도 알릴 것.**
- **해결 시** → `docs/solved_problems.md`로 옮기고(문제→원인→해결), unsolved에서 제거.
- 이 로그가 기억의 원본 — 내(Claude) 기억·정확성에 의존하지 않게.
- **구현 전 `docs/solved_problems.md` 확인** — 같은 실수 반복 금지.
- **SDD/ultracode 서브에이전트엔 `coding-principles` + `solved_problems.md`의 '핵심 gotchas'를 주입**(전체 아카이브·`unsolved`는 X — 🔴 자동구현 사고 위험). 배선·금지: `docs/subagent-context.md`. 서브에이전트는 세션 맥락이 없어 주입해야 실수를 안 반복한다.

## 배포 (요약, 상세는 operations.md)
- 코드/피드 변경 → 이미지 재빌드 → `gcloud run jobs update --image` → execute
- 사이트(`web/index.html`) 변경 → Hosting REST 재배포
- gcloud는 PATH 미등록 → 풀경로 `C:\Users\ho381\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd`, Firebase REST엔 `x-goog-user-project` 헤더 필수.
