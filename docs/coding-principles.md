# 코딩 접근 원칙 — newsstore 적용·예시

일반 원칙의 정의 SSOT는 전역 디시플린(`~/.claude/disciplined-coder/agent-principles.md`)이다. 이 문서는 그 원칙들의 **newsstore 특화 적용·예시**(feeds.yaml SSOT·Cloud Run IP·Docker 등)를 모은다 — 일반 정의를 재정의하지 않는다. 요약은 `CLAUDE.md`(자동 로드).

## 1. Single Source of Truth (SSOT)
같은 정보는 **한 곳에만** 정의한다.
- 예: 피드/소스 목록의 유일 출처 = `config/feeds.yaml`. 사이트 드롭다운은 그걸 **도출**해서 쓴다(수집기가 `meta/sources` 문서로 Firestore에 기록 → `index.html`이 읽음).
- 복제하면 한쪽만 고쳐 **드리프트** → 조용한 버그. (예전 `index.html`의 `SRC_ORDER` 하드코딩이 이 위반이었음.)

## 2. 복제 말고 도출 (Derive, don't duplicate)
하드코딩한 리스트/상수가 다른 진짜 출처를 베낀 것이면, 런타임 또는 빌드 시 그 출처에서 끌어와라. 사람이 두 곳을 동기화하게 만들지 말 것.

## 3. Fail-Loud (조용한 실패 금지)
설정 드리프트·계약 위반은 **테스트/검증이 즉시 터뜨려야** 한다.
- 예: "사이트가 보는 소스 집합 == `feeds.yaml`의 소스 집합" 드리프트 테스트 → 어긋나면 빨강.

## 4. 강건성 > 작성자 정확성
한 곳의 실수 편집이 전체를 조용히 깨뜨릴 수 없게 구조화한다(생성된 설정·명확한 계약·테스트).
- **사람이든 AI든 "정확히 기억/편집"에 의존하지 않게.** 구조가 실수를 막거나 드러내야 함.

## 5. TDD + 검증 후 주장
- 구현 전 **실패하는 테스트** 먼저.
- "됐다"고 주장하기 전에 **실제 실행해 증거** 확보(테스트 그린/로그/curl). 단언 금지.

## 6. 비파괴 우선
- 원본(raw) 데이터는 보존. 필터·dedup·스팸 제거는 **삭제가 아니라 분류 표시(mark)** 로 → 룰 바뀌면 재처리·복구 가능.
- 저장 전에 거르지 말고, 저장 후 처리 단계에서 표시.

## 7. 측정 먼저 (가정 금지)
- 빌드 전에 실제로 되는지 **측정**(curl 피드 테스트, FMP 엔드포인트 실측 등).
- "집(잔여 IP)에서 됨 ≠ 프로덕션(Cloud Run 데이터센터 IP)에서 됨" — 환경 차이를 먼저 확인.

## 8. Docker 전용 개발/테스트
- **로컬 Python 사용 금지** — 모든 실행·테스트·빌드는 Docker로만.
- 이유: 호스트에 로컬 Python 없음 + 환경 재현성(프로덕션 이미지와 동일 환경에서 테스트).
- 테스트: `MSYS_NO_PATHCONV=1 docker compose run --rm test`(Firestore 에뮬레이터 자동 기동 후 pytest).

## 9. 비밀 분리
- 진짜 비밀(`FMP_API_KEY`, 서비스계정 키)은 **백엔드 전용** — `.env`(gitignore+dockerignore) / Cloud Run env / Secret Manager. 클라이언트·커밋 금지.
- 비밀이 아닌 식별자(Firebase 웹 apiKey)는 클라이언트 노출 OK — 접근은 보안 규칙이 통제.
