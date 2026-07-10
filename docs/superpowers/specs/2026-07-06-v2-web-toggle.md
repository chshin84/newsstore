# Spec V2-web — v1↔v2 토글 + 스토리·리포트 v2 뷰 (6렌즈 반영)

작성: 2026-07-06 · 개정(6렌즈 반영) · 구간 소유권 = `web/index.html` + `tests/web/*`만. **백엔드(`src/`·`config/`·`firestore.rules`) 금지**(V2-backend 병렬). v2=백엔드 additive 증강 렌더 + 상단 v1↔v2 전환.

## 왜
최종 v2를 **상단에서 v1과 전환**(사용자 명시). v2=스토리·리포트 탭에 번들(개체 착지·설명 안 되는 움직임·매크로 브레드스)을 얹은 대체 뷰. 가격=데이터원, 피드 무변경. **검증 전이라 전부 '조사 트리아지 큐/가설'**(conviction 아님).

## 프로즌 계약 (백엔드가 확정 — 그대로 소비, graceful)
- 스토리 doc `landing`: `{tickers:[{ticker,label,excess_pct,window_days,resolved}], asset_class_fallback, unverified}`.
- 스토리 doc `breadth`: `{span, asset_classes:[], price_confirmed, uncovered:[], unverified}`.
- `signals/unexplained_moves` doc: `{generated_at, items:[{ticker|key,label,kind,move_z,move_pct,vol_confirmed,story_coverage:false,rank,unverified}], min_sample_ok}`. **정렬은 백엔드 rank 그대로**(web 재정렬 금지 — SSOT).
- **graceful 양방향**: 필드/도큐 부재 시 v2도 안 깨지고 생략(배포 순서 무관).

## 작업

### WV1. v1↔v2 토글 (상단 · 배선 완결 — 리뷰 medium 해소)
- 헤더 탭 근처 세그먼트 토글(v1/v2). **모드 저장 = 신규 키 `ns_view`**(문자열; `ns_expand` boolean맵과 별개). 기본 v1.
- **딥링크에 뷰 상태 포함**: 해시/쿼리에 뷰 인코딩(예 `#report&v2` 또는 `?view=v2`) → 공유 링크가 같은 뷰 재현(리뷰: v1/v2가 URL에 없으면 수신자가 v1로 강등). routeFromHash가 뷰도 파싱.
- **모든 렌더 진입점이 토글을 읽어야 함**: `loadReport`/`loadStories` 뿐 아니라 **`rerenderActiveTab`·5분 자동경신·탭 재진입**도 현재 뷰로 분기(안 하면 리프레시 후 v1 회귀 — 리뷰 medium). 별 렌더 함수는 v1 경로 보존.
- **맥락 게이팅**: 토글은 스토리·리포트 탭에서만 활성/표시(피드·가격에선 no-op이므로 숨기거나 비활성 — 혼란 방지).

### WV2. 스토리 탭 v2 — 개체 착지 + 브레드스
- 스토리 카드/상세에 `landing`: **얽힌 실제 종목 + 지수 대비 초과수익**. **회고적 base-rate 톤·저살리언스**(숫자는 버킷/반올림으로 거짓정밀 억제 — 리뷰: 티커+정밀% = 고살리언스 매매신호 오독). `resolved=false`(폴백)면 종목 없이 자산군 라벨만. `breadth` 배지. 없으면 생략.
- 스토리 v2 순수로직(landing 포맷·breadth)은 **STORIES-LOGIC 마커 안**(리포트 v2는 REPORT-LOGIC — 리뷰: 마커 분리).

### WV3. 리포트 탭 v2 — 설명 안 되는 움직임 큐 + 브레드스
- `signals/unexplained_moves`를 급부상 근처/신규 섹션에 "조사 큐": 큰 이동+거래량확인(주식)인데 서사 없는 자산/종목. 라벨=**공유 상수**(백엔드와 동일 문자열, 드리프트 방지). `vol_confirmed=null`(FX·금리·선물)은 거래량 표기 생략. `min_sample_ok=false`면 순위 대신 '표본 부족' 표기.

### WV4. 트리아지 프레이밍 + 빈 상태 (계약)
- v2 신호 전부 **가설/조사 큐** 위계(회색·"가설"·"가격 동시발생, 인과 아님" 툴팁). `unverified` 소비.
- **빈 상태**(리뷰): 세 증강 전부 부재면 v2 뷰에 "v2 신호 준비 중(백엔드 대기)" 안내 또는 토글 자동 숨김 — v2가 v1과 똑같아 고장처럼 보이지 않게.

## 통합/배포 (오케스트레이터가 머지 후)
- node 웹테스트 GREEN(v2 순수로직 — landing 포맷·breadth·큐 소비·뷰 라우팅; STORIES/REPORT 마커 적재). Playwright: 토글 동작·유지·딥링크 재현·리프레시 후 뷰 유지·맥락게이팅, v2 스토리/리포트, 가설 위계·빈상태, graceful, v1 회귀 0(사이드바·프레임·리드·레이아웃 불변식), 모바일. Hosting 재배포.

## 범위 밖
백엔드(V2-backend): 엔진·거래량·매핑·신호계산·정렬·firestore.rules. 가격탭·피드. 성적표(Phase-2).

## 리스크/주의 (주입 gotchas)
- 순수함수는 마커 안(스토리=STORIES-LOGIC·리포트=REPORT-LOGIC), 렌더·DOM 밖. graceful 판단도 순수 seam으로(node 테스트 가능하게).
- **Spec B/WW5 불변식 보호**: --side-w·.side-ghost·scrollbar-gutter·사이드바 트리·근거 dedup·A필드(divergence/conviction)·리드 불릿·프레임 위치 등 v1 회귀 0. v2는 additive 별 경로(드롭 쉽게).
- **frozen 계약**: 위 스키마 그대로 소비, 부재 graceful. **정렬 백엔드 rank 신뢰**(재정렬 금지).
- **거짓정밀 금지**: 초과수익·z는 버킷/반올림, 정밀% 남발 금지. 라벨=공유 상수.
- 딥링크·모바일·매직넘버 금지. Hosting=전체 스냅샷. 머지·배포는 오케스트레이터(브랜치까지만).

<!-- 6렌즈 반영: 프로즌 스키마 구체 소비(백엔드와 필드 일치). 토글 배선 완결(모든 진입점 read·rerenderActiveTab·5분폴링·딥링크 뷰상태·맥락게이팅). 빈상태 추가. STORIES/REPORT 마커 분리. ns_view 신규키. 숫자 저살리언스·버킷(오독 완화). 정렬 백엔드 SSOT(web 재정렬 금지). 라벨 공유상수(드리프트). tests/web/*만. v1 회귀 0·additive라 롤백 쉬움. 전부 엔지니어링 수정. -->
<!-- spec-review: passed -->
