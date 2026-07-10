# Spec B — 리포트 UI 재구성 (프론트)

작성: 2026-07-05 · v2(3렌즈 리뷰 반영) · 구간 소유권 = `web/index.html` + `tests/web/*`
(백엔드는 Spec A 소유 — `src/newsstore/*`·`config/*` 안 건드림. A의 계약 소비만.)

## 이 재작성이 바꾼 것 (리뷰 반영)
- 기사 출처 **데이터 위치 정정**(grounding): 기사 url/제목은 **스토리 문서가 아니라 `items` 컬렉션**에 있고 `where story_id==id` 쿼리로 가져온다(openStory가 이미 그렇게 함). → 리포트 항목 근거는 **접이식 토글을 펼칠 때만** 인용 스토리의 items를 lazy fetch(비용 한정).
- **saga 렌더 제거**(A에서 연기). B4=divergence 배지 + conviction만.
- 요구 **#1(렌더 구조·'잘림')을 B에 명시 배정**(B0 진단).

## 배경/맥락 (서브에이전트 주입 필수)
- 코드 원칙: SSOT(렌즈/그룹은 meta/report_groups·LENS_LABELS에서 도출, 하드코딩 복제 금지), Fail-Loud, 비파괴.
- 웹 테스트: node로 `web/index.html`의 `REPORT-LOGIC-START/END` 등 마커 슬라이스(순수함수만, `new Function`). DOM/외부스코프 금지. 순수함수는 마커 안, 렌더/DOM은 밖. `node --test tests/web/report_logic.test.mjs`.
- Firebase Hosting = **전체 스냅샷**(index.html+config.js 함께 — 하나 빠지면 404, solved 사고).
- 현 구조(grounding): SPA 4탭(피드·스토리·리포트·가격). `renderReportDoc`(≈891–966행): backdrop→글로벌프레임(mktframe)→다이제스트→렌즈별 섹션. 섹션 헤더 `seclbl`=group만 표시(그래서 "주식" 2번). 스토리 카드=storyCardHtml. 앵커=meta/report_groups(그룹→렌즈). `openStory`(≈790행)가 `items` where story_id 조회해 `it.url`(≈717행) 렌더 — **리포트 렌더는 현재 members를 fetch하지 않음**(스토리 열 때만 lazy). 다크/라이트·모바일(@media max-width:680px 단일 브레이크), `.strip` overflow-x:auto 존재.
- 리포트 그룹 순서 SSOT=topics.yaml report_group. 렌즈 라벨=LENS_LABELS(ensureLensLabels).

## 📥 소비 계약 (A가 `reports/{lens}`에 발행 — 있으면 렌더, 없으면 graceful)
```
divergence?: { kind: "over_fear"|"over_hope"|"aligned"|"none", price_key, price_pct, note }
conviction:  { level: "high"|"medium"|"low", basis }
```
필드 부재(가격 없는 렌즈·옛 문서) → **조용히 생략**(Fail-soft). saga 없음.

## 작업

### B0. 렌더 구조 확인 + '잘림' 진단·수정 (#1)
- 스크린샷의 항목 텍스트가 중간에 끊김. **저장 데이터는 안 잘림 확인**(len 96~122 완결) → 표시 잘림.
- **먼저 어느 DOM인지 특정**(추측 금지): 트리거 '문장'(`it.text`, `.abul li`)엔 클램프가 **없다**(=클램프 아님). 클램프는 **스토리 카드 제목/요약**(`.scard .st`/`.ssum`의 `-webkit-line-clamp:3;overflow:hidden`, ≈127–128행)에만 있다. 즉 스크린샷 끊김이 스토리 카드면 클램프고 → **B3에서 스토리 카드 제거로 자연 해소**. 트리거 문장이면 클램프가 아니라 다른 원인(폭/줄바꿈) — 실제 렌더로 규명 후 수정. **원인 요소부터 못박고** 처리.

### B1. 렌즈 라벨 표기 (#3 — 최소수정)
- 섹션 헤더가 report_group("주식")만 → "주식 2번". **렌즈 라벨(한국 주식/미국 주식)을 섹션 헤더에** 표기(그룹은 상위 맥락 유지 가능). LENS_LABELS 사용, 앵커와 일관.

### B2. backdrop/글로벌 프레임 정리 (#4)
- 개별 렌즈 리포트마다 반복되는 backdrop(AI 요약)을 **렌즈 리포트에서 제거**, **글로벌 시장 프레임을 리포트 진입 시 최상단 1회만**. _backdrop 문서는 백엔드 유지 — UI에서 렌즈마다 반복 안 함(최상단 1회 노출 or 글로벌 프레임 리드 축약은 재량, 렌즈 반복 금지).

### B3. 스토리 카드 → 기사 출처(접이식, lazy·캐시) (#6)
- **스토리 카드 제거**(자리 낭비). 리포트 항목 근거 = **기사 단위 링크**.
  - 항목당 **'근거 N건' 접이식 토글**(기본 접힘=밀도↑). **펼칠 때** 인용 story_id들의 `items`(where story_id) lazy fetch → 기사 제목+url 링크.
  - **캐시 필수**: story_id별 fetch 결과 메모이즈 — 재펼침·여러 항목이 같은 story_id 인용 시 **중복 fetch 금지**(리뷰 지적 N+1). 초기 렌더 items fetch 0.
  - **초기 스토리-doc eager fetch도 제거**: 현 `loadReport`는 인용 스토리 문서를 `where(documentId() in ...)`로 eager 로드(카드용). 카드를 없애므로 이 eager 로드도 제거/최소화 — 리포트 항목 텍스트·엣지 신호는 리포트 문서 자체에 있어 스토리 doc 없이 렌더 가능(story_ids만 있으면 됨).
  - 출처=기사(원문 url), 스토리 문서 아님. 클러스터 맥락 완화(재량): 펼친 목록에서 기사를 story_id별 소제목으로 얇게 묶음 — 스토리 '카드' 위젯 복원 금지.
- 재인용 dedup은 리포트 범위 안(기존 계약 유지).

### B4. 엣지 신호 렌더 (A 계약 소비) — #2(가격 정합)의 UI 표면
- **divergence(재료 — 판정 아님)**: 약한 프록시라(A 자인) '판정'처럼 안 보이게. **경고색·최상단 대형 배너 금지** — 헤드라인 옆/아래 **작은 재료 칩**("가격 정합: 괴리(재료)" 정도) + note는 툴팁/보조. over_fear/over_hope만 표시, aligned/none 생략. 사용자가 '단정'으로 오독하지 않게 시각 위계를 낮춘다.
- **conviction**: 등급(high/med/low) pill/미터 — **약한 근거를 디스카운트하라는 신뢰도 신호**(A2 실이득). basis는 툴팁.

### B5. 좌측 사이드바 네비 (#5)
- **데스크톱**: 좌측 고정 사이드바 — 리포트(그룹→렌즈) + 스토리 목록 위아래. 클릭=앵커 스크롤, 현재 위치 하이라이트(스크롤 스파이). **중간폭(681~1000px)도** 사이드바가 본문 압박 안 하게(브레이크 추가 or 유동폭). **모바일**: 햄버거/드로어 접기, 본문 가림·가로스크롤 없이(overflow-x 금지, 기존 .strip과 충돌 주의).
- **디폴트 첫 화면 = 리포트**. ⚠️ **무한로딩 방어**(solved: 리포트 탭 config.js/모듈 실패 시 '불러오는 중' 무한 — 이제 그게 첫 화면): 리포트 로드 실패 시 에러 표시 or 피드 폴백으로 **첫 페인트가 빈 로딩에 멈추지 않게**. #해시 라우팅·기존 딥링크(#rep-*·#story-*) 유지, 맨URL도 정상.

## 통합/배포 (오케스트레이터가 머지 후)
- node 웹 테스트 GREEN. Playwright 라이브 검증: #1 잘림 해소, 렌즈 라벨 구분, backdrop 미반복, 기사-출처 접이식 lazy, divergence 배지·conviction, 사이드바 네비·모바일 드로어, 디폴트=리포트, 딥링크 유지. Hosting 재배포(전체 스냅샷).

## 범위 밖
- 백엔드/스키마(A). divergence/conviction **계산**(A). 피드·가격 탭 본질 변경(사이드바 통합은 포함). saga(연기).

## 리스크/주의
- 순수함수는 REPORT-LOGIC 마커 안(node 테스트), 렌더는 밖.
- 사이드바 모바일 overflow-x 금지, 기존 브레이크(680px)·`.strip` 가로스크롤과 충돌 주의.
- A 필드 부재 graceful(옛 문서). 디폴트 첫화면 변경이 기존 라우팅·북마크 안 깨게.
- lazy fetch 비용: 펼칠 때만, 인용 스토리 수만큼. 초기 렌더 0.

<!-- 3렌즈 재리뷰(v2): 계약(divergence·conviction) 일치·saga 잔재 0 확인. major(B3 캐시·eager 제거, B5 무한로딩 방어·중간폭, B4 재료칩=경고배너 금지) 반영. #2=B4(가격 정합 UI)로 추적. -->
<!-- spec-review: passed -->
