# 해결된 문제 로그 (solved_problems)

작업 중 발견·해결된 문제 기록. 대부분 **사용자 지적/요청**이나 **코드 리뷰**에서 나왔다. 각 항목: 문제 → 원인 → 해결.
(미해결·대기 항목은 `unsolved_problems.md`.)

> ⏱ **이 로그는 *발생 시점(2026-06-12~13)의 사실*이다 — 현재 규칙이 아님.** 재사용 가능한 교훈은 `coding-principles.md`로 승격됨(여기엔 일회성 기록 위주, 중복 배제=SSOT). 서브에이전트는 이를 *과거 사실*로 읽을 것 — 살아있는 작업 지시가 아니다(예: "fxstreet 제거"는 이미 끝난 일).

## 핵심 gotchas (재발 방지 — 서브에이전트 주입용 다이제스트)
*반복되는 cross-cutting 함정*만 추림. SDD/ultracode 서브에이전트엔 **이 섹션 + `coding-principles.md`를 주입**(전체 아카이브 말고). 배선: `docs/subagent-context.md`.
- **Docker-only**: 테스트 `docker compose run --rm test` (또는 `MSYS_NO_PATHCONV=1 docker run -v "D:/projects/newsstore:/app" newsstore pytest -q`). `$(pwd)` 마운트는 stale 이미지로 조용히 폴백.
- **Firestore 실client**: 빈 문서 `to_dict()`가 `None` 반환 → 항상 `... or {}` (MockFirestore는 못 잡음).
- **PowerShell 변수 대소문자 비구분**: `$h`와 `$H`는 같은 변수 → 충돌 주의.
- **Firebase REST**: 헤더 `x-goog-user-project: daily-recap-498506` 없으면 403.
- **인라인 주석 금지**: `.gitignore`/`.env`/`--env-file`은 줄끝 `# 주석`을 값/패턴에 섞음 → 주석은 별도 줄.
- **프로덕션을 테스트에 맞춰 약화 금지**: 테스트 더블이 부실하면 *테스트*를 고쳐라(프로덕션 `client.close()`를 guard로 무르게 X).
- **하드코딩 금지(SSOT)**: 리스트/설정은 원본(feeds.yaml 등)에서 도출, 두 곳 복제 X.

## 환경 / 툴링
- **로컬 Python 없음** — 호스트 `python`은 Windows Store 스텁. → **Docker 전용 개발**(개발 원칙 7). 모든 실행·테스트는 Docker.
- **Docker bind-mount 경로 폴백** — Git Bash `$(pwd)`/`${PWD}`가 망가져 마운트가 *stale 이미지*로 조용히 폴백 → 테스트 수가 틀리게(44 대신 33) 나옴. → `MSYS_NO_PATHCONV=1 docker run --rm -v "D:/projects/newsstore:/app" newsstore pytest -q`.
- **Workflow `args`가 문자열로 전달** — 첫 피드검증 워크플로가 `feeds.map is not a function`로 실패. → 스크립트에 `typeof args === 'string' ? JSON.parse(args) : args` 폴백.
- **PowerShell 변수 대소문자 비구분** — Hosting 배포에서 루프변수 `$h`(해시)가 `$H`(헤더)를 덮어써 실패. → 변수명 분리(`$hdr`/`$rh`) + 해시→바이트 직접 맵 + `[byte[]]` 캐스팅.
- **`.gitignore` 인라인 주석 미지원** — `uv.lock  # ...` 패턴이 안 먹혀 파일이 계속 추적됨. → 주석을 별도 줄로.

## 코드 리뷰에서 잡은 것 (FirestoreStore)
- **`get_feed_state`/`get_unprocessed`의 `to_dict()` None** — 실제 google client는 빈 문서에 `None` 반환 → `AttributeError`(MockFirestore는 못 잡음). → `snap.to_dict() or {}` 가드.
- **`run.py` 프로덕션 약화** — 구현자가 테스트 더블 맞추려 `client.close()`를 `getattr(client,"close",...)`로 약화. → 리뷰가 잡음 → 프로덕션 원복 + 테스트가 `close()` 있는 가짜 제공.
- **미사용 import / N+1 read** — `from typing import Optional` 미사용 제거, `mark_processed` 배치-read TODO 주석.

## GCP / Firebase 배포
- **Firebase REST 403 (quota project)** — gcloud 토큰으로 Firebase API 호출 시 quota project 미설정. → 헤더 **`x-goog-user-project: daily-recap-498506`** 필수.
- **콘솔에 프로젝트 안 보임 / 웹앱·apiKey 못 찾음** — GCP 프로젝트에 Firebase 미추가 상태. → **REST `:addFirebase`** 로 추가 + 웹앱 생성 + config 발급(콘솔 헤맬 필요 없어짐).
- **실수로 만든 중복 프로젝트** `daily-recap-498506-5ff8b` — "새 Firebase 프로젝트"를 눌러 별개 빈 프로젝트 생성. → 무해(이름만 중복, ID 다름) 확인 후 삭제. 진짜는 `daily-recap-498506`.
- **apiKey 노출 우려** — 공개 repo/사이트에 Firebase 웹 apiKey 보임. → **비밀 아님**(식별자일 뿐, 접근은 보안규칙이 통제) 확인. 단 **`GEMINI_API_KEY`는 진짜 비밀** → 백엔드 전용(개발 원칙 8).
- **fxstreet 항상 실패** — Cloud Run 데이터센터 IP에서 차단(집 IP에선 됨). → 피드 제거(실패 0).

## 사이트 — 데이터 품질 / UX
- **`&quot;` 등 엔티티 노출** — 제목에 디코딩 안 된 HTML 엔티티(인포맥스 이중 인코딩). → 표시 전 클라이언트 디코드.
- **TruthSocial이 본문을 제목에** — 피드가 본문을 title에 실음. → 제목="Truth Social", 본문은 미리보기.
- **같은 뉴스 중복**(BitGo PR 등) — dedup이 URL(link) 기준이라 같은 뉴스가 URL만 달라 중복 저장. → 사용자 선택대로 **뷰에서 제목 정규화 dedup**(비파괴).
- **집단소송 로펌 PR + "$X 투자했다면" 클릭베이트** — Benzinga 양산 스팸. → 고정밀 키워드 필터(뷰). (Step-2에서 백엔드 이사 예정)
- **소스 색 겹침** — 해시 충돌. → 황금각(137.5°) 배정.
- **영어 폰트 가독성** — → Inter(영) + Noto Sans KR(한).
- **블룸버그 너무 적음** — 실은 132건(3위)인데 최신순 80개에 고빈도 소스(Benzinga·GNews)에 밀려 안 보였음. → **소스 필터 드롭다운** + Bloomberg 카테고리 피드 5개 추가.
- **소스 드롭다운에 빈 항목** — ForexLive/FXStreet/FinancialJuice 등 데이터 없는 소스 하드코딩. → 실제 소스만 → 이후 **SSOT**(meta/sources)로 완전 자동화.
- **소스 선택 시 인덱스 에러** — `source+published_at` 복합 인덱스 생성 중. → 친절 안내+자동 재시도, 인덱스 READY.

## 피드 / 수집
- **Reuters GN 중복** — 새 `reuters_top`이 기존 `gn_macro_reuters`(둘 다 site:reuters.com)와 겹침 + 헤드라인뿐. → `gn_macro_reuters` 제거, Reuters 단독화.
- **본문 스크래핑 가능성** — 전 소스 curl 테스트 → Bloomberg 403·CoinDesk/CT/Investing JS렌더·GN 리다이렉트로 fragile. → **스크래핑 안 함, 피드 확충이 정답**(결정).

## 설계 — 임베딩 클러스터링 (스파이크 검증)
- **union-find 과병합** — naive 단일임계 쌍연결이 *전이 연쇄*로 무관한 한국어 금융기사 9건을 한 덩어리로. → **centroid 온라인 + 임계 0.83**(중심과 비교 → 사슬 차단). 실데이터 검증: 묶인 건 전부 진짜 스토리, 30/40 단독, 30건 ~12초.

## 정리 / 리팩터
- **SSOT 위반: `index.html` SRC_ORDER 하드코딩** — 사용자 지적. feeds.yaml 소스를 복제 → 드리프트 위험. → 수집기가 `meta/sources`를 feeds.yaml에서 도출·기록 → 사이트가 읽음. **중복 제거**(드리프트 테스트 불필요).
- **firebaseConfig 인라인** — → `web/config.js` 분리.
- **uv.lock / data;C / docker-compose / .env.example / .dockerignore** — uv.lock gitignore · `data;C` 빈 잔재 삭제 · 미사용 docker-compose 삭제 · 디스크 소실된 .env.example 복원 · .dockerignore에 tests/·web/·*.md 추가(런타임 이미지 순수화).
