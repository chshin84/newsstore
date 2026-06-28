# 피드가 백엔드 `kind`로 스팸·다이제스트 필터 — 설계

_작성: 2026-06-28 · 상태: 설계(검토중) · 성격: 자기완결 기능(호스팅/UI 레이어, newsstore 범위 · news-analytics 산출물 소비)_

## 1. 목표 / 범위
공개 사이트 피드(`web/index.html`)가 스팸을 **브라우저에 복제한 키워드 목록(`JUNK`)**으로 거르는 대신, **news-analytics가 쓰는 백엔드 `kind` 필드**(`story|spam|digest`)를 직접 읽어 거른다.

- **이건 news-analytics 산출물 소비 기능** — `kind`는 분석 계층이 `items`에 merge로 쓰는 인리치 필드(계약: `docs/firestore-contract.md`). 뷰는 그걸 신뢰한다.
- **SSOT 해소**: 현재 `JUNK`(index.html line 169-175)는 `src/newsstore/enrich/classify.py`의 `SPAM_SIGNALS`를 손으로 복제한 것 — 한쪽만 고치면 드리프트(`tests/test_spam_signals_drift.py`가 임시로 막던 위반). `kind`를 읽으면 어휘 출처가 백엔드 한 곳으로 일원화된다.
- **실질 개선**: 현 `JUNK`는 다이제스트(블룸버그 `, More`·`(Podcast)`·`(Video)`)를 **안 거른다**. `kind=digest`를 읽으면 이것들도 피드에서 빠진다(스토리 아님).
- **범위 밖**: 서버측 `where(kind==story)` 쿼리(미인리치 항목엔 `kind`가 없어 누락 → 신규 뉴스가 사라짐; 수집 시 `kind` 시딩이 필요하고 이는 `collect`/`store` 변경이라 동시 세션 영역 → 제외). 피드 카드에 스토리 클러스터 배지. 스토리 뷰(`storiesView`)는 변경 없음.

## 2. 확정된 결정
1. **클라이언트측 필터, 서버 쿼리 불변**: 기존 `query(items, orderBy(published_at desc), limit(80))` 그대로. 받은 뒤 `kind`로 거른다. (서버 `where(kind==...)`는 미인리치 누락 문제로 채택 안 함 — §1 범위 밖.)
2. **판정 규칙(fail-soft)**: `kind ∈ {spam, digest}` → 숨김. `kind` 없음(미인리치 fresh) 또는 `story`/그 외 값 → **노출**. 분석이 멈춰도 피드는 raw 뉴스로 우아하게 강등(빈 화면 금지 — 계약 §B4).
3. **`JUNK`/`isJunk` 제거**: 중복 어휘를 코드에서 들어낸다. 대체 = 순수함수 `keepInFeed(item)`.
4. **드리프트 가드 테스트 제거**: `tests/test_spam_signals_drift.py`는 "뷰가 backend kind로 이전하기 전까지의 최소 안전망"(그 docstring 명시). 이전이 끝나면 **막을 중복 자체가 없어** 목적 소멸 → 제거(선례: `unsolved_problems.md` §참고 SRC_ORDER "SSOT로 중복 자체 제거되어 불필요"). ※ 이 테스트가 지키던 것은 **프런트↔백엔드 어휘 일치**다 — `JUNK` 배열을 물리적으로 삭제하면 비교 대상이 사라져 목적이 소멸한다(서버측 `SPAM_SIGNALS` 사용은 계속되므로 "그래서 테스트를 되살려야 하나?"는 아니다 — 되살릴 대상이 없다).
5. **테스트 가능 배치**: `keepInFeed`를 `// === FEED-LOGIC-START/END ===` 마커 블록에 둔다(스토리 로직과 동일 패턴, line 288-330). node 테스트가 마커를 슬라이스해 검증 — 복붙 드리프트 불가.

## 3. 트레이드오프 (명시)
- **신규 미인리치 스팸이 노출창 동안 보인다.** 수집 직후~클러스터 패스(`--mode cluster`, 정상 시 10분 주기)가 해당 항목에 `kind`를 쓸 때까지 법무법인 PR 등이 피드에 노출될 수 있다(현 키워드 필터는 제목 텍스트라 수집 즉시 차단). **노출창 크기 = 인리치 사이클 지연** — 정상·큐 비백로그면 ~10분이나, **수집률 > 배치 처리율이면 큐가 밀려 더 길어질 수 있다**(하드 SLO로 보장하지 않음). 스팸 항목도 분류되면 `kind:"spam"`이 영속되어(`processor.py:87-90`) 그 뒤로 숨겨진다.
- **수용 근거**: (a) 백로그가 명시한 방향(뷰→kind), (b) 같은 `SPAM_SIGNALS` 로직이 서버측에서 인리치 사이클 내 분류, (c) SSOT 위반(어휘 이중출처) 제거 가치가 노출창보다 크다.
- **장애 degrade(major, 명시):** 키워드 필터는 백엔드 없이도 동작했으나, 이 변경으로 **스팸 차단이 인리치 가동에 결합**된다. 인리치 Job이 **장애·중단**이면 항목이 계속 kind-absent → `keepInFeed`가 fail-soft로 **스팸까지 노출**(분석 정지 시 raw 강등 = 계약 §B4와 합치하나, 오늘보다 스팸 차단이 약해지는 회귀임). **완화책은 신규 추가하지 않고 기존 백로그에 위임** — `unsolved_problems.md` Phase D "잡 실패 알림"(Scheduler가 잡 죽어도 초록 → Cloud Monitoring 실패 카운트 알림)이 그 가드다. 그 알림이 서면 장애 노출창이 사람에게 드러난다. (이 spec은 모니터링을 구현하지 않는다 — 인프라·별건.)
- **되돌리기 쉬움(REVERSIBLE):** 코드는 `keepInFeed`에 키워드 폴백을 더하면 복원. 단 **배포 비용은 0이 아님** — 사이트 Hosting REST 재배포(~수 분)가 끼며 그 사이엔 변경 전 동작.

## 4. 컴포넌트
### 4.1 `web/index.html`
- 신규 마커 블록 `FEED-LOGIC`:
  ```js
  // === FEED-LOGIC-START (node test가 슬라이스해 검증; 순수함수만, DOM/외부스코프 금지) ===
  const HIDDEN_KINDS = new Set(["spam", "digest"]);
  function keepInFeed(it) { return !HIDDEN_KINDS.has(it && it.kind); }  // kind 없음/story → 노출(fail-soft)
  // === FEED-LOGIC-END ===
  ```
- `load()`의 `if (isJunk(it)) continue;`(line 242) → `if (!keepInFeed(it)) continue;`.
- `JUNK` 배열(169-175)·`isJunk`(176-179) 삭제.

### 4.2 테스트
- 신규 `tests/web/feed_logic.test.mjs`: 마커 슬라이스 → `keepInFeed` 검증.
  - `kind:"spam"` → false, `kind:"digest"` → false.
  - `kind:"story"` → true, `kind` 없음 → true, `kind:"기타"` → true(fail-soft).
  - `it` null/undefined → throw 없이 true(강건).
- `tests/test_spam_signals_drift.py` 삭제(§2.4).
- `tests/test_index_contract.py`는 무관(인덱스 계약, `kind` 미참조) — 영향 없음 확인.

## 5. 검증 (TDD)
- 실패 테스트 먼저(`feed_logic.test.mjs`) → `keepInFeed` 구현 → `node tests/web/feed_logic.test.mjs` 통과.
- 기존 node 테스트 회귀 없음(`node tests/web/stories_logic.test.mjs`).
- 파이썬 스위트: `MSYS_NO_PATHCONV=1 docker compose run --rm test` — drift 테스트 제거 후 FAIL=0(잔여 스위트 그대로 통과; 매직넘버 단언 없음, 불변식만).

## 6. 배포 / 스코프 경계
- 사이트(`web/index.html`) 변경 → **Hosting REST 재배포**(`operations.md` 사이트 배포 절차). **outward-facing → 사용자 게이트**(이 세션에서 배포 안 함). 배포 후 스모크: 피드에서 다이제스트/스팸 비노출 + 신규 뉴스 정상 노출 육안 확인.
- **동시 세션 비충돌**: 변경은 `web/index.html` + `tests/web/feed_logic.test.mjs` + (삭제)`tests/test_spam_signals_drift.py`만. `collect`/`contracts`/`store`(본문가져오기 세션 영역) 불건드림.

## 7. 범위 밖 / 후속
- 수집 시 `kind` 기본 시딩 → 서버측 `where(kind==story)` 쿼리 가능(읽기 비용↓). `collect`/`store` 변경이라 별도.
- 피드 카드에 `story_id` 클러스터 배지(여러 헤드라인 묶임 표시).
- 다이제스트를 숨기는 대신 접기/별도 섹션 옵션.

<!-- spec-review 반영: grounding 0 / consistency 0 / adversarial major2(인리치장애 degrade·노출창 SLO)+minor → §3·§2.4 보강. critical 0 = accept. -->
<!-- spec-review: passed lenses=3 date=2026-06-28 -->
