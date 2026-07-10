# Spec W3 — 사이드바 트리 재구성 + 선택 표식 재디자인

작성: 2026-07-05 · 구간 소유권 = `web/index.html` + `tests/web/*`만. **백엔드(`src/`·`config/`) 금지.** 리포트 섹션 스키마·백엔드 무변경(그룹 SSOT=meta/report_groups 그대로, 렌더 방식만 바꾼다).

## 왜 (사용자가 라이브에서 짚음)
방금 배포한 사이드바는 4탭 평면 목록이라, (1) 계층이 안 보이고, (2) 피드가 사이드바에 낄 이유가 없고, (3) 리포트 목차가 "주식·급부상" 같은 중간 그룹 헤더를 거쳐 한 단계 깊고, (4) 선택 표식이 진부하다. 사용자: "하위 디렉토리처럼 구성", "선택 표식 조금 다른 UI로."

## 현 구조 (grounding)
- `.sidenav#sidenav`에 3개 `.navsec`: "메뉴"(navtabs=피드·스토리·리포트·가격 4개 `.navtab`), "리포트 목차"(`#navReportList`←`buildReportNav`), "스토리 목록"(`#navStoryList`←`buildStoryNav`).
- `buildReportNav(docm)`: `docm.sections`를 돌며 `group`이 바뀔 때 `.navgroup` 헤더(주식/급부상/원자재…)를 찍고 그 밑에 렌즈 `.navlink`. **이 `.navgroup`이 없앨 "중간 구분".**
- 그룹 순서 SSOT = `docm.sections`(=topics.yaml report_group 순서). 하드코딩 복제 금지.
- 스크롤스파이(`setupReportSpy`)·딥링크(`#rep-*`·`#story-*`)·`sideToggle`(☰ 접기)·모바일 드로어(`navScrim`)가 이미 있음(방금 Spec B).
- 카드 좌측 여러 색 = 리포트 섹션 컴포넌트(`.rsec-h` 계열, Spec B에서 semantic 색점으로 개편). **이건 카드용으로 좋으니 유지** — 사이드바 선택 표식은 이것과 **다른 접근**으로.

## 작업

### W3-1. 사이드바를 계층 트리로 (하위 디렉토리 은유)
- 최상위 항목 = 뷰(스토리·리포트·가격). **피드는 사이드바에서 제거**(헤더 탭 `#tabFeed`·피드 뷰 자체는 유지 — 사이드바 목록에서만 뺀다). 스토리는 그대로 유지.
- 자식이 있는 항목(리포트→렌즈들, 스토리→스토리들)은 **폴더처럼 펼침/접힘**. 현 평면 3섹션(메뉴/리포트목차/스토리목록)을 이 트리로 통합하거나, 계층이 드러나게 재배치. 트리 상태(펼침)는 localStorage로 유지(Spec B 토글과 일관).

### W3-2. 리포트 목차 평면화 (중간 그룹 제거)
- `buildReportNav`에서 `.navgroup` 헤더(주식/급부상/원자재…)를 **없애고 렌즈를 바로 나열**("한국 주식", "미국 주식", …). 라벨 = `LENS_LABELS`(SSOT). 급부상(rising)도 별도 구분 없이 같은 평면에.
- 순서 SSOT(`docm.sections`=report_group 순서)는 유지 — **표시에서 그룹 헤더만 감춘다**(백엔드·순서 불변, 렌더 변경). 딥링크·스크롤스파이 계속 동작.

### W3-3. 선택 표식 재디자인 (진부함 탈피 · 카드 컴포넌트와 차별)
- 현 `.navlink` active 표식을 **신선한 처리**로. **왼쪽 색 막대(카드용 모티프)는 재사용 금지** — 사이드바는 다른 언어로(예: 채워진 pill 배경·선행 도트/아이콘·미묘한 inset 강조 중 frontend-design 감각으로 택1). semantic 유지하되 세련되게. 스크롤스파이 하이라이트도 같은 새 표식.
- **frontend-design 스킬로 접근** — 택한 접근과 근거를 완료 보고에 명시(사용자가 "다른 UI로 접근" 위임).

## 통합/배포 (오케스트레이터가 머지 후)
- node 웹테스트 GREEN(새 순수 로직 있으면 테스트 추가 — 예 트리 빌드/평면화). Playwright: 트리 펼침·접힘, 피드 사이드바 부재·피드 탭 동작, 리포트 목차 평면(그룹헤더 없음)·딥링크·스크롤스파이, 새 선택 표식, 모바일 드로어, 가로 overflow 0. Hosting 재배포(전체 스냅샷).

## 범위 밖
백엔드·리포트 스키마(그룹 SSOT 불변). 리포트 본문 렌더 재편(#4 — 별도 web 라운드). divergence/conviction. 카드 컴포넌트 색(유지).

## 리스크/주의 (주입 gotchas)
- 순수함수는 REPORT-LOGIC 마커 안(node 테스트 `new Function` 슬라이스), 렌더·DOM은 밖.
- **SSOT**: 트리·목차는 meta(report_groups/LENS_LABELS)·`docm.sections`에서 도출 — 렌즈·순서 하드코딩 복제 금지.
- 딥링크(`#rep-*`·`#story-*`)·스크롤스파이·모바일 드로어·`sideToggle` graceful 유지(회귀 0). 모바일 overflow-x 금지, 680px·`.strip` 반응형 안 깨게.
- A 필드(divergence·conviction) 및 Spec B 근거 dedup lazy fetch 유지. DB·스토리 문서 불변(표시만).
- Hosting=전체 스냅샷(index.html+config.js 둘 다). 머지·main push·배포는 오케스트레이터가(브랜치까지만).

<!-- 리뷰 보류·escalated: 사용자가 리포트 UI를 실시간 재설계 중(2026-07-05 추가 지시 — 리포트 순서 라이징-최상단→한/미주식→금리채권→나머지, 글로벌 프레임 삭제, 프레임 보기=스토리 내용 뒤 배치, 프레임 글자색 제거, 서브섹션 구조 재검토, 텍스트 짤림 버그 MAX_ITEM_TEXT=240). 사이드바(트리·피드제거·평면화·선택표식)는 이 리포트 본문 재설계와 같은 web/index.html·같은 순서 SSOT를 공유하므로 별개 워크트리로 쪼개면 충돌. → 서브섹션 fork 확정 후 '리포트 UI 통합 스펙'으로 재작성해 web 단일 라운드로. 지금은 설계 수렴 대기. -->
<!-- spec-review: escalated -->
