# 플랜 B — 스토리 타임라인 뷰 (프론트) · 구현 계획 (v2, 3렌즈 반영)

_근거 설계: `docs/superpowers/specs/2026-06-15-newsstore-story-timeline-ui-design.md`(3렌즈 통과)의 §2·§4 프론트 절반. 백엔드(플랜 A)가 채운 stories 필드를 **읽기만** 한다. 선행: 플랜 A 배포 후 summary 필드가 차지만, **필드 없어도 우아하게 degrade**._

## 0. 목표 한 줄
기존 사이트에 **피드 | 스토리** 탭 추가. 스토리 탭 = 가로 스토리 카드 스트립, **카드 클릭** 시 아래에 그 스토리의 **전개 타임라인 + 실제 기사 카드**가 열린다(목업 `timeline-dedup-v3.html` 레이아웃).

## 1. 핵심 제약 (반드시)
- **단일 파일 배포**: Hosting REST(`operations.md §B`)는 `/index.html` 하나만 올린다. 그러므로 **모든 스토리 뷰 코드는 `web/index.html` 안에 인라인**(별도 .js/.mjs ❌ — 배포 안 됨).
- **읽기 전용**: stories(read:true, 배포됨) + items만 읽음. 쓰기 없음.
- **degrade**: 플랜 A 미배포·미요약 스토리는 summary·latest·developments가 없을 수 있음 → 없으면 제목+건수만, 타임라인은 published_at만으로(단일 버킷).
- **XSS(최우선)**: stories의 title·summary·latest·developments[].text는 **LLM 생성=비신뢰**. 기사 title/body/source/url도 피드 출처=비신뢰. **모든 출력은 기존 `txt()`/`esc()`/`bodyHtml()` 경유**(§5 감사표). 어떤 LLM/피드 문자열도 템플릿 리터럴에 raw 삽입 금지.

## 2. 확정 결정 (스펙 §2/§4 + 리뷰 반영)
- **탭 토글**: 헤더 `피드 | 스토리`. 기본=피드. 상태=URL 해시 `#stories`/`#feed`(`hashchange`로 전환, 새로고침 유지).
- **스트립 쿼리**: `stories where status=='open' order by last_seen desc limit 40` → 클라이언트 `count>=2` 필터 → 상위 ~20. 결과<목표여도 있는 만큼, 0개면 "아직 묶인 스토리가 없어요" 안내. 인덱스 `stories(status,last_seen)` READY.
- **스트립 카드**: title(요약 title 있으면 그것, 없으면 원 title) + summary(2~3줄, 있을 때) + `🔵 최신: {latest}`(있을 때) + 건수 + 상대시간(last_seen). 상단 띠 색 = **스토리 id 해시**(`srcColors` 재사용). **멤버 소스 색점은 스트립에서 생략**(스트립마다 items를 읽지 않으려는 perf 결정 — 스펙 §4의 "소스 색점"에서 의도적 축소, v1). 실제 소스 색은 펼친 디테일의 기사 카드에서 보여줌.
- **스크롤**: `overflow-x:auto` + wheel(deltaY→scrollLeft, 목업 스크립트) + ‹ › 버튼 + 터치 스와이프(native).
- **인터랙션(단일·robust로 확정)**:
  - **호버 = 시각효과만**(DB 안 읽음): 카드 살짝 확대 + **오른쪽 형제 카드를 CSS transform으로 한 칸 밀기**(스펙의 "한 칸 밀기" 충족, 레이아웃 리플로우 없이 transform이라 스크롤과 안 싸움). 호버는 어떤 Firestore 읽기도 트리거하지 않음 → 빠른 호버 read 폭발 원천 차단(adversarial 지적).
  - **클릭 = 디테일 열기**: 선택 카드에 `.sel`, **스트립 아래 디테일 패널**에 그 스토리를 렌더(목업 레이아웃). 이때만 `items where story_id==X` 1회 읽고 **세션 캐시**(같은 스토리 재클릭은 캐시). 다시 클릭/ESC/바깥클릭으로 닫기. 모바일=탭=클릭(동일 경로, 호버 없음).
- **디테일 레이아웃**: `[왼쪽 슬림 세로 타임라인(전개, 위=최신) | 오른쪽 기사 카드 겹친 스택 ~600~900px]`. 전개당 대표 **≤2장 + "+N개 더"**(클릭 시 전부). 기사 카드 = 기존 피드 카드 스타일.
- **전개↔기사 매핑**: 디테일 진입 시 items 로드. **developments를 프론트가 time DESC 재정렬**(저장 배열 순서 불신 — 리뷰 지적). 각 기사를 버킷팅(§3 함수). 시간 비교는 **모두 ms 숫자로 정규화**(Firestore Timestamp→`.toDate().getTime()`; dev.time도 Timestamp). 타입 혼선 차단.
- **dedup 2종**: ① 기사 제목정규화 중복(피드와 공유 `decode().trim().toLowerCase()`) ② 전개당 표시 ≤2(서로 다른 source 우선).

## 3. 순수 로직 (index.html 인라인, 마커 구분, node로 검증)
순수 데이터 변형은 **index.html 안에** 마커로 감싼 블록에 둔다(단일 출처·단일 배포). node 테스트가 그 마커 사이를 **문자열 슬라이스(취약한 JS 정규식 파싱 아님)**해 eval → 실제 배포 코드를 그대로 검증(드리프트 불가).
```
// === STORIES-LOGIC-START (node test가 이 사이를 슬라이스해 검증; 순수함수만, DOM/외부스코프 금지) ===
function toMs(t){ /* Date|Firestore Timestamp|number|null -> number|null */ }
function groupItemsByDevelopment(developments, items){
  // 1) devs = developments에서 toMs(time)!=null만, time DESC 정렬(입력 순서 불신)
  // 2) items에서 toMs(published_at)!=null만(=null은 제외 — backend도 동일)
  // 3) devs 비면 [{dev:null, items: items(published_at DESC)}] 단일 버킷(degrade)
  // 4) 각 item을 (item.ms >= dev.ms 인 devs 중 ms 최대) 전개에 배정(>= 경계: 동률은 그 전개로).
  //    어떤 dev.ms보다도 과거인 item은 가장 이른 전개(devs 마지막)로.
  // 반환: [{dev, items:[...published_at DESC]}], dev DESC. 모든 비-null item 정확히 1버킷.
}
function pickDisplayItems(groupItems, max=2){
  // 서로 다른 source 우선으로 최대 max개 선택(소스<max면 같은 소스로 채움), 나머지 수 moreCount.
  // 반환 {shown:[...], moreCount:N}
}
// === STORIES-LOGIC-END ===
```
- **불변식(테스트로)**: 모든 비-null item이 정확히 한 버킷; 버킷은 time DESC; 각 그룹 내 published_at DESC; shown≤max; moreCount = group.length - shown.length; devs 빈/ items 빈/ 전부 과거/ 경계 동률/ null 섞임 — 전부 throw 없이 처리.

## 4. 구현 단계 (web/index.html)
1. 헤더 탭 토글 + CSS. `#feedView`/`#storiesView` 컨테이너 2개. 해시 라우팅.
2. STORIES-LOGIC 마커 블록(순수 함수) 삽입.
3. 스트립 렌더: stories 쿼리 → 카드(모든 텍스트 `txt()` 경유). 띠색 `srcColors(storyId)`.
4. 가로 스크롤(wheel/arrows) 이식.
5. 호버 시각효과(형제 transform) — CSS만.
6. 클릭 디테일: items 1회 로드(+캐시) → `groupItemsByDevelopment` → 타임라인(왼쪽, dev.text는 `txt()`) + 기사 스택(오른쪽, `pickDisplayItems`, 기존 카드 함수) → "+N개 더" 토글.
7. degrade·빈·에러 상태(스토리 0, developments 0→단일버킷, items 0→"기사 없음", 인덱스 빌딩→기존 재시도 패턴).

## 5. XSS 감사표 (구현 시 이 표대로 — 하나도 raw 금지)
| 값(출처) | 렌더 위치 | 적용 |
|---|---|---|
| story.title (LLM/원제목) | 스트립 카드 제목, 디테일 헤더 | `txt()` |
| story.summary (LLM) | 카드/디테일 요약 | `txt()` |
| story.latest (LLM) | 카드 "최신" | `txt()` |
| developments[].text (LLM) | 타임라인 노드 | `txt()` |
| developments[].source_count (int) | 라벨 | `Number()` 강제 후 텍스트 |
| item.title/body (피드) | 기사 카드 | `txt()`/`bodyHtml()` (기존) |
| item.source (피드) | 소스 칩 + 색 | `txt()` + `srcColors` |
| item.url (피드) | 링크 href | `esc()` (기존 패턴) |
| story.id (내부) | DOM id/data | `esc()` 또는 숫자/해시만 |

## 6. 테스트 / 검증
- **node 순수 로직**: `node tests/web/stories_logic.test.mjs`(또는 `web/` 밖 테스트 디렉토리) — index.html에서 STORIES-LOGIC 블록 슬라이스→eval→불변식(§3) 전부. **드리프트 가드**: 슬라이스가 비거나 함수 미정의면 테스트 실패(FAIL-LOUD).
- **정적 독립 리뷰**: 구현 후 3렌즈(factual: 쿼리/규칙/인덱스/단일파일배포/이스케이프 실제 적용 / consistency: 스펙 §4·degrade·time정규화 / adversarial: XSS 실삽입 시도·호버스크롤·perf·빈데이터).
- **눈 검증(아침)**: 사용자/`run`으로 사이트 띄워 탭·가로스크롤·호버밀기·클릭디테일·타임라인 확인(브라우저 자동검증 불가 — 명시). 배포(Hosting §B)는 **돈/외부 → 사용자 확인 후**.

## 7. 리스크 / 경계
- **호버 vs 스크롤**: 호버는 transform 시각효과만(리플로우/읽기 없음) → 스크롤과 안 싸움. 디테일은 명시적 클릭에서만.
- **perf**: 스트립=stories doc만. 디테일=클릭당 items 1회+세션 캐시. read 폭발 없음.
- **배열 순서/타입**: developments 프론트 time DESC 재정렬 + ms 정규화 비교.
- **degrade/빈데이터**: 요약 전 스토리·전개0(단일버킷)·기사0·스토리0 모두 안전 렌더.
- **모바일**: 호버 없음 → 탭=클릭 동일 경로. 형제 밀기는 데스크톱 호버 한정(모바일은 디테일만).
- **단일파일 배포**: 전 코드 index.html 인라인. 순수함수 마커 블록을 node가 추출 검증(드리프트 가드).

<!-- spec-review: passed lenses=3 date=2026-06-15 -->
