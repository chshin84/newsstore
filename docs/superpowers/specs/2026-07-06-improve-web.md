# Spec IMP-web — 가격탭 자산군 그루핑 + 캡션 정합 (넓은 스윕 · 6렌즈 반영)

작성: 2026-07-06 · 개정(6렌즈 반영) · 구간 소유권 = `web/index.html` + `tests/web/*`만. **백엔드(`src/`·`config/`) 금지**(IMP-backend 병렬). 사용자 강조: UI·가격. 스키마 불변(표시만).

## 왜 (스윕 주제 3: 가격탭↔리포트 정보위계 갭)
가격탭이 '순수 시세'라 자산군 스캔이 안 되고, 리포트 카드가 가격 배지를 달면서 '가격 미반영' 캡션을 단다(모순). 저비용 UI 정합. **IW3 딥링크는 리뷰 지적(price_key 키공간 미확정·pcard id 부재·해시 오낙하·값<복잡도)으로 드롭·이연.**

## 현 구조 (grounding — 리뷰 교정 반영)
- 가격 대시보드 `renderPriceDashboard`(~1725) — 카드를 자산군 구분 없이 평면 그리드(`pcards`). 카드 `pcard`(~1733)는 **class만, id 없음**(무순서 Firestore docs). group·order 필드는 IMP-backend가 신규 산출.
- 리포트 카드: divergence 배지 `divHtml`(~1431-1433). 하단 `dmeta` 캡션(~1498) "가격 미반영(이슈 중심)" **무조건**. divergenceChip은 `price_key`를 `|| ""`로 반환(빈 배지 가능).
- 순수로직 마커 PRICE-LOGIC(~1050)·REPORT-LOGIC(~885) + node 테스트 슬라이스.

## IW1. 가격탭 자산군 섹션 그루핑 [M, 가격] — 리뷰 반영(order·pin)
- `renderPriceDashboard`가 가격 doc의 **`group`·`order` 필드**(IMP-backend frozen: 지수·금리·환율·원자재·변동성 문자열 + int order)로 카드를 **자산군 섹션**으로 묶어 렌더. 섹션 라벨 = group 문자열 **그대로**(드리프트 없음). 섹션·카드 순서 = `order` 오름차순(web에 순서 하드코딩 금지 — 백엔드 order로 도출). "금리는 다 올랐나" 스캔 가능. **graceful**: group 부재(구형)면 기존 평면(배포순서 무관). 그루핑·정렬 순수로직은 PRICE-LOGIC 마커 안·node 테스트(빈/부재/order 정렬 불변식).

## IW2. 리포트 캡션 vs divergence 모순 해소 [S, UI 카피] — 유일 실측 결함
- `dmeta` 캡션(~1498)을 **divHtml 존재 시 조건부**: divergence 배지가 있으면 "가격 미반영(이슈 중심)" 단정을 제거/수정(예 캡션에서 그 문구 생략). **배지 없는 카드는 기존 캡션 유지**(깨끗한 신호 보존). 순수 결정(divHtml 유/무→캡션)은 순수 seam·node 테스트.

## 통합/배포 (오케스트레이터가 머지 후)
- node 웹테스트 GREEN(그루핑·order 정렬·graceful·캡션 분기 순수로직 테스트 추가). Playwright: 가격탭 자산군 섹션(order 순·group 부재 graceful), 캡션 모순 해소(배지 유/무 분기), 모바일·레이아웃 불변식. Hosting 재배포.

## 범위 밖 (이연 — 리뷰 반영)
**IW3 divergence→가격 딥링크(드롭)** — price_key 키공간(doc-id vs symbol) 미확정·pcard id 부재·`#price-*` 해시 라우팅 오낙하·FAIL-LOUD 라벨 vs fail-silent·값<복잡도. 백엔드(IMP-backend): group·order 산출·VIX/달러·텔레메트리. 가격탭 해석레이어(이례성 배지). 리포트/가격 스키마 재편.

## 리스크/주의 (주입 gotchas)
- 순수함수는 마커 안(PRICE-LOGIC/REPORT-LOGIC), 렌더·DOM 밖. graceful·캡션분기도 순수 seam(node 테스트).
- **Spec B/WW5 불변식 보호**: --side-w·.side-ghost·scrollbar-gutter·사이드바 트리·프레임 인라인·리드 불릿·divergence/conviction 배지·스토리 평면50·v1/v2 토글·스크롤스파이 회귀 0.
- **frozen 계약**: 가격 doc `group`·`order` 소비, 부재 graceful(배포순서 무관). 섹션 라벨=group 문자열 그대로(드리프트 금지). **web에 그룹 순서 하드코딩 금지**(order로 도출).
- 모바일 overflow-x 금지·매직넘버 금지. DB·문서 불변(표시만). Hosting=전체 스냅샷. 머지·배포는 오케스트레이터(브랜치까지만).

<!-- 6렌즈 반영: (drop)IW3 딥링크 — price_key 키공간 미확정·pcard id 부재·해시 오낙하·FAIL-LOUD vs fail-silent·값<복잡도로 이연. IW1 order 필드로 순서 도출(web 하드코딩 금지)·group 문자열 그대로(드리프트 없음)·graceful. IW2 견고 유지(유일 실측 결함, 배지 유무 분기). pcard id 부재 grounding 교정. -->
<!-- spec-review: passed -->
