# 수집 대시보드 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** newsstore가 수집하는 각 데이터의 신선도·수집상황을 한 화면에서 확인하고 종목 단위로 스팟체크하는, Firebase Auth 이메일 허용목록으로 잠긴 정적 대시보드 페이지를 만든다.

**Architecture:** 별도 정적 페이지 `web/dashboard.html`. 순수 로직(신선도·지연·범위·유니버스)은 `web/dashboard_logic.mjs`로 분리해 node로 TDD한다. 페이지는 Firestore JS SDK로 컬렉션을 바운드 쿼리(컬렉션당 최신 1건 + 종목별 doc-id 범위)로 읽고, Firebase Auth 구글 로그인 + `config/allowlist` 이메일 게이트로 접근을 막는다. 백엔드 없음.

**Tech Stack:** 정적 HTML + ES 모듈, Firebase v10 modular SDK(app/auth/firestore, CDN), node(테스트 러너 — 기존 `tests/web/*.test.mjs` 관행), Firestore 보안규칙.

**Spec:** `docs/superpowers/specs/2026-07-13-collection-dashboard-design.md` (spec-review: passed).

## Global Constraints

- 순수 로직은 `web/dashboard_logic.mjs`에만 두고(SSOT), 페이지와 node 테스트가 **같은 모듈**을 import한다.
- 매직넘버 금지 — 문턱은 계약값(주기·TTL 30일)에서 도출하고 불변식 테스트로 고정.
- 바운드 쿼리만(전체 스캔·`count()` 금지). 신규 복합 인덱스 0(단일필드·doc-id 자동 인덱스만).
- 2층 접근: `items`·`meta`·`prices`는 공개 read 유지, FMP 팩터/스트림 컬렉션은 `request.auth != null && email ∈ config/allowlist`, **write는 전부 금지**(Admin SDK만).
- 문서에 안 보이는 유니코드 문자 금지 — 상한 sentinel은 코드에서 `String.fromCharCode(0xF8FF)`로 명시(리터럴 U+F8FF·escape 혼동 회피).
- 기존 `web/index.html`(공개 뉴스 리더)은 손대지 않는다. 기존 다크 테마·카드 스타일을 따른다.
- 테스트는 `docker` 불요(순수 node). 실행: `node --test tests/web/`.
- 계약의 17개 컬렉션: `items`·`price_bars`·`prices`·`prices_eod`·`income`·`balance`·`cashflow`·`ratios`·`market_cap`·`grades_history`·`profiles`·`estimates`·`price_targets`·`grades_consensus`·`index_members`·`index_changes`·`delisted`. 대시보드 7카드가 이들을 빠짐없이(중복 없이) 덮는다.

---

## File Structure

- Create `web/dashboard_logic.mjs` — 순수 로직 + SSOT 상수(CARDS·SCHEDULE·문턱). 한 책임: 판정/변환.
- Create `web/dashboard.html` — 페이지(인증 게이트 + Firestore 바운드 쿼리 + 렌더). 위 모듈 import.
- Create `tests/web/dashboard_logic.test.mjs` — 순수 로직 node 테스트.
- Modify `firestore.rules` — 2층 규칙(공개 + 인증 게이트), 레거시 `fundamentals` 규칙 제거.
- Modify `docs/firestore-contract.md` — reader/공개read 항목을 2층 모델로 갱신, 레거시 `fundamentals` 행 정리.
- Runtime 설정(코드 아님, Task 4에 절차): Firebase 콘솔에서 구글 auth provider 활성화 + `config/allowlist` 문서 생성.

---

## Task 1: dashboard_logic.mjs — SSOT 상수 + isOverdue

**Files:**
- Create: `web/dashboard_logic.mjs`
- Test: `tests/web/dashboard_logic.test.mjs`

**Interfaces:**
- Produces: `SCHEDULE`(초 단위 주기), `CARDS`(카드 SSOT 배열), `TTL_DAYS`·`OVERDUE_FACTOR`·`LEAD_FRACTION`, `isWeekend(ms)`, `isOverdue(lastFetchedMs, opts, nowMs) -> {overdue:boolean, reason:string}`.

- [ ] **Step 1: 실패 테스트 작성** — `tests/web/dashboard_logic.test.mjs`

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  SCHEDULE, CARDS, TTL_DAYS, isWeekend, isOverdue,
} from '../../web/dashboard_logic.mjs';

const MON = Date.UTC(2026, 6, 13, 12, 0, 0);   // 2026-07-13 월 12:00 UTC
const SAT = Date.UTC(2026, 6, 11, 12, 0, 0);   // 2026-07-11 토

test('isWeekend: 토/일만 true', () => {
  assert.equal(isWeekend(SAT), true);
  assert.equal(isWeekend(MON), false);
});

test('빈 컬렉션(null)은 항상 경보 — TTL 만료가 정상으로 오탐 안 됨', () => {
  assert.equal(isOverdue(null, { expectedSec: SCHEDULE.weekly }, MON).overdue, true);
  assert.equal(isOverdue(undefined, { expectedSec: SCHEDULE.daily }, MON).overdue, true);
  assert.equal(isOverdue(NaN, { expectedSec: SCHEDULE.daily }, MON).overdue, true);
});

test('§1: 정상 주기 내면 지연 아님, OVERDUE_FACTOR배 초과면 지연', () => {
  const opts = { expectedSec: SCHEDULE.weekly };            // §1(기본)
  const fresh = MON - SCHEDULE.weekly * 1000;               // 1주 전
  const stale = MON - SCHEDULE.weekly * 1000 * 4;           // 4주 전(>3배)
  assert.equal(isOverdue(fresh, opts, MON).overdue, false);
  assert.equal(isOverdue(stale, opts, MON).overdue, true);
});

test('시장 데이터는 주말에 지연 완화(빈 결과는 예외 — 여전히 경보)', () => {
  const opts = { expectedSec: SCHEDULE.daily, marketData: true };
  const old = SAT - SCHEDULE.daily * 1000 * 10;             // 아주 오래됐어도 주말엔 완화
  assert.equal(isOverdue(old, opts, SAT).overdue, false);
  assert.equal(isOverdue(old, opts, MON).overdue, true);    // 평일엔 지연
  assert.equal(isOverdue(null, opts, SAT).overdue, true);   // 빈 결과는 주말에도 경보
});

test('§2(백필 불가)는 30일 데드라인에서 문턱 도출 — 21일보다 이르게 경보', () => {
  const opts = { expectedSec: SCHEDULE.weekly, backfillImpossible: true };
  const at13d = MON - 13 * 86400 * 1000;                    // 13일 경과(> 30*0.4=12일)
  const at10d = MON - 10 * 86400 * 1000;                    // 10일 경과(< 12일)
  assert.equal(isOverdue(at13d, opts, MON).overdue, true);
  assert.equal(isOverdue(at10d, opts, MON).overdue, false);
  // 불변식: §2 문턱 < 30일 데드라인이고 복구 리드타임이 남는다.
  assert.ok(TTL_DAYS * 0.4 < TTL_DAYS - 7);
});

test('CARDS는 계약 17개 컬렉션을 빠짐없이·중복 없이 덮고, expectedSec는 SCHEDULE 값', () => {
  const CONTRACT = ['items','price_bars','prices','prices_eod','income','balance','cashflow',
    'ratios','market_cap','grades_history','profiles','estimates','price_targets',
    'grades_consensus','index_members','index_changes','delisted'];
  const covered = CARDS.flatMap(c => c.collections);
  assert.equal(covered.length, new Set(covered).size, '중복 배치 없음');
  assert.deepEqual([...covered].sort(), [...CONTRACT].sort(), '계약 전 컬렉션 커버');
  const sched = new Set(Object.values(SCHEDULE));
  for (const c of CARDS) assert.ok(sched.has(c.expectedSec), `${c.key} expectedSec는 SCHEDULE 값`);
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `node --test tests/web/dashboard_logic.test.mjs`
Expected: FAIL — `Cannot find module '../../web/dashboard_logic.mjs'`.

- [ ] **Step 3: 최소 구현** — `web/dashboard_logic.mjs`

```js
// 수집 대시보드 순수 로직 — SSOT 상수 + 판정. 페이지·node 테스트가 공유한다.
// 문턱은 계약값(주기·30일 TTL 데드라인)에서 도출(매직넘버 금지). 계약: docs/firestore-contract.md.

export const TTL_DAYS = 30;
export const OVERDUE_FACTOR = 3;    // §1: 기대주기의 몇 배까지 정상으로 볼지(보수적)
export const LEAD_FRACTION = 0.4;   // §2: 지연 문턱 = TTL_DAYS × 이 비율(데드라인 대비 리드타임 확보)

// 실제 수집 스케줄(Cloud Scheduler cron / run_factors cadence)의 UI측 사본(초).
// 클라이언트는 스케줄러를 못 읽어 불가피한 두 번째 출처 — 스케줄을 바꾸면 여기도 바꾼다.
// (docs/operations.md §8 · setup.md §8과 일치해야 함.)
export const SCHEDULE = { intraday: 300, daily: 86400, weekly: 604800 };

// 카드 SSOT — 계약 17개 컬렉션을 7카드로 빠짐없이 묶는다.
// marketData=주말 완화 대상, backfillImpossible=§2(30일 데드라인 문턱).
export const CARDS = [
  { key: 'news',       label: '뉴스',              collections: ['items'],
    expectedSec: SCHEDULE.intraday, marketData: false, backfillImpossible: false },
  { key: 'intraday',   label: '시세(5분봉)',        collections: ['price_bars', 'prices'],
    expectedSec: SCHEDULE.intraday, marketData: true,  backfillImpossible: false },
  { key: 'eod',        label: '배당조정 EOD',       collections: ['prices_eod'],
    expectedSec: SCHEDULE.daily,    marketData: true,  backfillImpossible: false },
  { key: 'statements', label: '재무제표',           collections: ['income', 'balance', 'cashflow'],
    expectedSec: SCHEDULE.weekly,   marketData: false, backfillImpossible: false },
  { key: 'ratios',     label: '프로파일·비율·시총·등급이력', collections: ['profiles', 'ratios', 'market_cap', 'grades_history'],
    expectedSec: SCHEDULE.weekly,   marketData: false, backfillImpossible: false },   // grades_history=§1 백필 가능
  { key: 'consensus',  label: '컨센서스(추정·목표·등급분포)', collections: ['estimates', 'price_targets', 'grades_consensus'],
    expectedSec: SCHEDULE.weekly,   marketData: false, backfillImpossible: true },   // §2 백필 불가 3종만
  { key: 'universe',   label: '유니버스',           collections: ['index_members', 'index_changes', 'delisted'],
    expectedSec: SCHEDULE.weekly,   marketData: false, backfillImpossible: false },
];

export function isWeekend(ms) {
  const d = new Date(ms).getUTCDay();   // 0=일, 6=토 (UTC 근사 — 완화용이라 충분)
  return d === 0 || d === 6;
}

// 빈 컬렉션(null/NaN)은 항상 경보. 시장 데이터는 주말 완화(단 빈 결과는 예외).
// §2는 데드라인에서 문턱 도출, §1은 OVERDUE_FACTOR × 기대주기.
export function isOverdue(lastFetchedMs, opts, nowMs) {
  const { expectedSec, marketData = false, backfillImpossible = false,
          overdueFactor = OVERDUE_FACTOR, ttlDays = TTL_DAYS, leadFraction = LEAD_FRACTION } = opts;
  if (lastFetchedMs == null || !Number.isFinite(lastFetchedMs)) {
    return { overdue: true, reason: 'empty' };
  }
  if (marketData && isWeekend(nowMs)) {
    return { overdue: false, reason: 'weekend-relaxed' };
  }
  const thresholdMs = backfillImpossible
    ? ttlDays * 86400 * 1000 * leadFraction
    : expectedSec * 1000 * overdueFactor;
  const overdue = (nowMs - lastFetchedMs) > thresholdMs;
  return { overdue, reason: overdue ? 'stale' : 'ok' };
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `node --test tests/web/dashboard_logic.test.mjs`
Expected: PASS (6 tests).

- [ ] **Step 5: 커밋**

```bash
git add web/dashboard_logic.mjs tests/web/dashboard_logic.test.mjs
git commit -m "feat(dashboard): 순수 로직 — CARDS SSOT + isOverdue(빈결과·주말·§2 데드라인)"
```

---

## Task 2: dashboard_logic.mjs — relTime + cardFreshness

**Files:**
- Modify: `web/dashboard_logic.mjs`
- Test: `tests/web/dashboard_logic.test.mjs`

**Interfaces:**
- Produces: `relTime(fromMs, nowMs) -> string`, `cardFreshness(fetchedMsList) -> {lastFetchedMs:number|null, anyEmpty:boolean}`.
- Consumes(Task1): —

- [ ] **Step 1: 실패 테스트 추가** (`tests/web/dashboard_logic.test.mjs` 끝에)

```js
import { relTime, cardFreshness } from '../../web/dashboard_logic.mjs';

test('relTime: 상대시각 포맷', () => {
  const now = Date.UTC(2026, 6, 13, 12, 0, 0);
  assert.equal(relTime(now - 30 * 1000, now), '방금');
  assert.equal(relTime(now - 5 * 60 * 1000, now), '5분 전');
  assert.equal(relTime(now - 3 * 3600 * 1000, now), '3시간 전');
  assert.equal(relTime(now - 2 * 86400 * 1000, now), '2일 전');
});

test('cardFreshness: 가장 오래된 값, 하나라도 비면 anyEmpty(→경보)', () => {
  assert.deepEqual(cardFreshness([300, 100, 200]), { lastFetchedMs: 100, anyEmpty: false });
  assert.deepEqual(cardFreshness([300, null, 200]), { lastFetchedMs: null, anyEmpty: true });
  assert.deepEqual(cardFreshness([]), { lastFetchedMs: null, anyEmpty: true });
});
```

- [ ] **Step 2: 실패 확인**

Run: `node --test tests/web/dashboard_logic.test.mjs`
Expected: FAIL — `relTime`/`cardFreshness` not exported.

- [ ] **Step 3: 구현 추가** (`web/dashboard_logic.mjs` 끝에)

```js
export function relTime(fromMs, nowMs) {
  const s = Math.max(0, Math.floor((nowMs - fromMs) / 1000));
  if (s < 60) return '방금';
  const m = Math.floor(s / 60); if (m < 60) return `${m}분 전`;
  const h = Math.floor(m / 60); if (h < 24) return `${h}시간 전`;
  return `${Math.floor(h / 24)}일 전`;
}

// 카드 신선도 = 묶인 컬렉션들의 '최신 fetched_at' 중 가장 오래된 것(하나만 멈춰도 카드가 잡음).
// 하나라도 비었으면(수집 전·TTL 만료) anyEmpty → 카드는 경보 처리.
export function cardFreshness(fetchedMsList) {
  let anyEmpty = false, oldest = null;
  for (const v of fetchedMsList) {
    if (v == null || !Number.isFinite(v)) { anyEmpty = true; continue; }
    oldest = oldest == null ? v : Math.min(oldest, v);
  }
  if (fetchedMsList.length === 0) anyEmpty = true;
  return { lastFetchedMs: anyEmpty ? null : oldest, anyEmpty };
}
```

- [ ] **Step 4: 통과 확인**

Run: `node --test tests/web/dashboard_logic.test.mjs`
Expected: PASS (8 tests).

- [ ] **Step 5: 커밋**

```bash
git add web/dashboard_logic.mjs tests/web/dashboard_logic.test.mjs
git commit -m "feat(dashboard): relTime + cardFreshness(가장 오래된 컬렉션, 빈 결과 경보)"
```

---

## Task 3: dashboard_logic.mjs — idRange + universeUnion + searchFilter

**Files:**
- Modify: `web/dashboard_logic.mjs`
- Test: `tests/web/dashboard_logic.test.mjs`

**Interfaces:**
- Produces: `HIGH_SENTINEL`, `idRange(symbol) -> {low:string, high:string}`, `universeUnion(memberDocs) -> {symbol,name}[]`, `searchFilter(universe, q) -> {symbol,name}[]`.

- [ ] **Step 1: 실패 테스트 추가**

```js
import { idRange, universeUnion, searchFilter, HIGH_SENTINEL } from '../../web/dashboard_logic.mjs';

test('idRange: 상한 sentinel이 하한보다 크고, 인접 접두를 안 물어들인다', () => {
  const r = idRange('AAPL');
  assert.equal(r.low, 'AAPL__');
  assert.ok(r.high > r.low, '상한 sentinel 존재(없으면 0건)');
  // 실제 문서는 low 이상, high 이하 — AAPL 자기 문서만 포함
  assert.ok('AAPL__20240101' >= r.low && 'AAPL__20240101' <= r.high);
  // 인접 접두 AAP는 AAPL을 안 물어들인다: 'AAPL__...' 은 AAP 범위(하한 'AAP__') 밑
  const rAAP = idRange('AAP');
  assert.ok(!('AAPL__20240101' >= rAAP.low && 'AAPL__20240101' <= rAAP.high));
});

test('universeUnion: 3개 지수 합집합·중복제거·심볼 정렬', () => {
  const docs = [
    { members: [{ symbol: 'AAPL', name: 'Apple' }, { symbol: 'MSFT', name: 'Microsoft' }] },
    { members: [{ symbol: 'MSFT', name: 'Microsoft' }, { symbol: 'NVDA', name: 'Nvidia' }] },
    { members: [] },
    null,
  ];
  assert.deepEqual(universeUnion(docs).map(x => x.symbol), ['AAPL', 'MSFT', 'NVDA']);
});

test('searchFilter: 심볼·이름 부분일치, 빈 쿼리는 빈 결과', () => {
  const u = [{ symbol: 'AAPL', name: 'Apple' }, { symbol: 'MSFT', name: 'Microsoft' }];
  assert.deepEqual(searchFilter(u, 'aap').map(x => x.symbol), ['AAPL']);
  assert.deepEqual(searchFilter(u, 'micro').map(x => x.symbol), ['MSFT']);
  assert.deepEqual(searchFilter(u, '  '), []);
});
```

- [ ] **Step 2: 실패 확인**

Run: `node --test tests/web/dashboard_logic.test.mjs`
Expected: FAIL — not exported.

- [ ] **Step 3: 구현 추가**

```js
// 문서 id {symbol}__{YYYYMMDD}의 종목별 범위. 상한 sentinel 필수(없으면 0건).
// U+F8FF를 안 보이는 문자로 쓰지 말고 fromCharCode로 명시(스펙 리뷰 교훈).
export const HIGH_SENTINEL = String.fromCharCode(0xF8FF);
export function idRange(symbol) {
  return { low: symbol + '__', high: symbol + '__' + HIGH_SENTINEL };
}

// index_members 문서들(각 {members:[{symbol,name}]})에서 유니버스 도출(중복제거·심볼 정렬).
export function universeUnion(memberDocs) {
  const bySym = new Map();
  for (const d of (memberDocs || [])) {
    for (const m of (d && d.members ? d.members : [])) {
      if (m && m.symbol && !bySym.has(m.symbol)) bySym.set(m.symbol, m.name || '');
    }
  }
  return [...bySym.entries()]
    .map(([symbol, name]) => ({ symbol, name }))
    .sort((a, b) => (a.symbol < b.symbol ? -1 : a.symbol > b.symbol ? 1 : 0));
}

export function searchFilter(universe, q) {
  const s = (q || '').trim().toUpperCase();
  if (!s) return [];
  return universe.filter(x =>
    x.symbol.toUpperCase().includes(s) || (x.name || '').toUpperCase().includes(s));
}
```

- [ ] **Step 4: 통과 확인**

Run: `node --test tests/web/dashboard_logic.test.mjs`
Expected: PASS (11 tests).

- [ ] **Step 5: 커밋**

```bash
git add web/dashboard_logic.mjs tests/web/dashboard_logic.test.mjs
git commit -m "feat(dashboard): idRange(상한 sentinel) + universeUnion + searchFilter"
```

---

## Task 4: firestore.rules — 2층 게이트 + 런타임 설정

**Files:**
- Modify: `firestore.rules` (전체 교체)
- Runtime(코드 아님): Firebase 콘솔 구글 auth 활성화 + `config/allowlist` 문서 생성

**Interfaces:**
- Produces: 공개 read(`items`·`meta`·`prices`) + 인증 게이트(팩터 컬렉션) + write 전면 금지 규칙.

- [ ] **Step 1: 현재 규칙 확인**

Run: `cat firestore.rules`
Expected: 현재 `items`·`meta`·`prices`·`fundamentals` 공개 read가 보인다(레거시 `fundamentals` 포함).

- [ ] **Step 2: 규칙 전체 교체** — `firestore.rules`

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    // ── 공개 read (공개 뉴스 리더 web/index.html) — RSS·시세 스냅샷, FMP 재배포 제약 밖 ──
    match /items/{id}  { allow read: if true;  allow write: if false; }
    match /meta/{id}   { allow read: if true;  allow write: if false; }
    match /prices/{id} { allow read: if true;  allow write: if false; }

    // ── 인증 + 이메일 허용목록 게이트 (FMP 팩터/스트림) ──
    // 로그인했고 이메일이 config/allowlist.emails 에 있어야 read. write는 전면 금지(Admin SDK만).
    function allowed() {
      return request.auth != null
        && request.auth.token.email in
           get(/databases/$(database)/documents/config/allowlist).data.emails;
    }
    match /price_bars/{id}       { allow read: if allowed(); allow write: if false; }
    match /prices_eod/{id}       { allow read: if allowed(); allow write: if false; }
    match /income/{id}           { allow read: if allowed(); allow write: if false; }
    match /balance/{id}          { allow read: if allowed(); allow write: if false; }
    match /cashflow/{id}         { allow read: if allowed(); allow write: if false; }
    match /ratios/{id}           { allow read: if allowed(); allow write: if false; }
    match /market_cap/{id}       { allow read: if allowed(); allow write: if false; }
    match /grades_history/{id}   { allow read: if allowed(); allow write: if false; }
    match /profiles/{id}         { allow read: if allowed(); allow write: if false; }
    match /estimates/{id}        { allow read: if allowed(); allow write: if false; }
    match /price_targets/{id}    { allow read: if allowed(); allow write: if false; }
    match /grades_consensus/{id} { allow read: if allowed(); allow write: if false; }
    match /index_members/{id}    { allow read: if allowed(); allow write: if false; }
    match /index_changes/{id}    { allow read: if allowed(); allow write: if false; }
    match /delisted/{id}         { allow read: if allowed(); allow write: if false; }

    // 허용목록 자체는 비공개(이메일 PII) — 규칙 get()만 접근
    match /config/{id} { allow read, write: if false; }

    // 그 외(feed_state·레거시 fundamentals/stories/frames 등) 기본 거부.
    // 수집기는 Admin SDK라 규칙 우회 — write:false여도 정상 적재.
    match /{document=**} { allow read, write: if false; }
  }
}
```

- [ ] **Step 3: 규칙 배포 + 검증(에뮬레이터 또는 콘솔)**

에뮬레이터로 확인(로컬):
```bash
# 별도 터미널: 규칙+에뮬레이터 기동(파이어베이스 CLI 있으면)
firebase emulators:start --only firestore
```
검증(수동 또는 콘솔 규칙 플레이그라운드):
- 미인증 `income/AAPL__20250101` read → **거부**.
- `config/allowlist`에 없는 이메일로 인증 read → **거부**.
- 허용목록 이메일로 인증 read → **허용**.
- `items` read(미인증) → **허용**(공개 유지).
Expected: 위 4가지가 기대대로.

- [ ] **Step 4: 런타임 설정(콘솔 — 1회)**

1. Firebase 콘솔 → Authentication → Sign-in method → **Google** 사용 설정.
2. Firestore에 `config/allowlist` 문서 생성: `{ "emails": ["you@example.com", "guest@example.com"] }`.
   (사람 추가/취소 = 이 배열 편집. 규칙 재배포 불요.)
3. 프로덕션 규칙 배포: `firebase deploy --only firestore:rules` (또는 콘솔에 붙여넣기, `x-goog-user-project` 헤더 REST 경로는 `docs/operations.md §C`).

- [ ] **Step 5: 커밋**

```bash
git add firestore.rules
git commit -m "feat(dashboard): firestore 2층 규칙 — 공개(items/meta/prices) + 인증 게이트(팩터), 레거시 fundamentals 제거"
```

---

## Task 5: web/dashboard.html — 인증 게이트 + 바운드 쿼리 + 렌더

**Files:**
- Create: `web/dashboard.html`
- Depends: `web/config.js`(Firebase 설정), `web/dashboard_logic.mjs`(Task 1-3)

**Interfaces:**
- Consumes: `dashboard_logic.mjs`의 `CARDS`·`isOverdue`·`relTime`·`cardFreshness`·`idRange`·`universeUnion`·`searchFilter`. Firestore SDK(`collection`·`query`·`orderBy`·`limit`·`getDocs`·`doc`·`getDoc`·`where`·`documentId`). Auth SDK(`GoogleAuthProvider`·`signInWithPopup`·`onAuthStateChanged`·`signOut`).

- [ ] **Step 1: config.js export 형태 확인**

Run: `cat web/config.js`
Expected: Firebase 설정 객체가 보인다. **export 이름을 확인**한다 — 아래 코드는 `export const firebaseConfig = {...}`를 가정한다. 이름이 다르면(예: default export, `window.__cfg`) 그에 맞춰 아래 import 줄만 조정한다. `authDomain` 필드가 있어야 구글 팝업 로그인이 된다(없으면 `<projectId>.firebaseapp.com`으로 config.js에 추가).

- [ ] **Step 2: 페이지 작성** — `web/dashboard.html`

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>newsstore 수집 대시보드</title>
<style>
  :root { --bg:#0f1115; --card:#1a1e26; --line:#2a2f3a; --fg:#e6e9ef; --mut:#8b93a3; --alert:#ff6b6b; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--fg); font:14px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif; }
  header { padding:14px 20px; border-bottom:1px solid var(--line); display:flex; justify-content:space-between; align-items:center; }
  h1 { font-size:16px; margin:0; } h2 { font-size:14px; margin:0; }
  .mut { color:var(--mut); } .alert { color:var(--alert); font-weight:600; }
  button { background:#252b36; color:var(--fg); border:1px solid var(--line); border-radius:6px; padding:6px 12px; cursor:pointer; }
  main { padding:16px 20px; max-width:920px; margin:0 auto; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:12px 14px; margin-bottom:10px; }
  .card .row { display:flex; justify-content:space-between; align-items:baseline; gap:10px; }
  .sample { color:var(--mut); font-size:13px; margin-top:4px; }
  #signin { text-align:center; padding:64px 20px; }
  input { background:#252b36; color:var(--fg); border:1px solid var(--line); border-radius:6px; padding:8px 10px; width:100%; }
  .suggest { border:1px solid var(--line); border-radius:6px; margin-top:4px; max-height:180px; overflow:auto; }
  .suggest div { padding:6px 10px; cursor:pointer; } .suggest div:hover { background:#252b36; }
  .panel { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:12px; }
  .box { background:#141821; border:1px solid var(--line); border-radius:8px; padding:8px 10px; }
  .box .none { color:var(--mut); font-style:italic; }
  a { color:#6db3ff; }
</style>
</head>
<body>
<header>
  <h1>newsstore 수집 대시보드</h1>
  <div><span id="who" class="mut"></span> <button id="signout" style="display:none">로그아웃</button></div>
</header>

<div id="signin">
  <p class="mut">허용된 이메일로 로그인해야 데이터가 보입니다.</p>
  <button id="google">구글로 로그인</button>
  <p id="denied" class="alert" style="display:none">이 계정은 접근 권한이 없습니다(허용목록에 없음).</p>
</div>

<main id="app" style="display:none">
  <p class="mut">불러온 시각: <span id="loaded"></span> · <button id="refresh">새로고침</button></p>
  <section id="cards"></section>
  <section class="card">
    <h2>종목 드릴다운</h2>
    <input id="search" placeholder="심볼 또는 이름 검색 (예: AAPL)" autocomplete="off">
    <div id="suggest" class="suggest" style="display:none"></div>
    <div id="detail"></div>
  </section>
</main>

<script type="module">
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import { getAuth, GoogleAuthProvider, signInWithPopup, signOut, onAuthStateChanged }
  from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";
import { getFirestore, collection, query, orderBy, limit, getDocs, doc, getDoc,
         where, documentId }
  from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";
import { firebaseConfig } from "./config.js";
import { CARDS, isOverdue, relTime, cardFreshness, idRange, universeUnion, searchFilter }
  from "./dashboard_logic.mjs";

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);
const $ = (id) => document.getElementById(id);
const toMs = (ts) => {                        // Firestore Timestamp | ISO 문자열 | null → ms
  if (!ts) return null;
  if (typeof ts.toMillis === "function") return ts.toMillis();
  const t = Date.parse(ts); return Number.isFinite(t) ? t : null;
};

// ── 인증 게이트 ──
$("google").onclick = () => signInWithPopup(auth, new GoogleAuthProvider()).catch(e => {
  $("denied").textContent = "로그인 실패: " + e.code; $("denied").style.display = "block";
});
$("signout").onclick = () => signOut(auth);
onAuthStateChanged(auth, async (user) => {
  if (!user) { $("signin").style.display = "block"; $("app").style.display = "none";
               $("signout").style.display = "none"; $("who").textContent = ""; return; }
  // 허용목록 통과 여부는 실제 read 시도로 확인(규칙이 최종 판정). 우선 UI 전환 후 로드.
  $("who").textContent = user.email; $("signout").style.display = "inline-block";
  try { await load(); $("signin").style.display = "none"; $("app").style.display = "block"; }
  catch (e) {                                  // permission-denied = 허용목록 밖
    $("app").style.display = "none"; $("signin").style.display = "block";
    $("denied").textContent = "이 계정은 접근 권한이 없습니다(허용목록에 없음)."; $("denied").style.display = "block";
  }
});

// ── 로드: 상태 카드 + 유니버스 ──
let universe = [];
async function latestFetched(coll) {           // 컬렉션 최신 fetched_at(ms) — 바운드(limit 1)
  const snap = await getDocs(query(collection(db, coll), orderBy("fetched_at", "desc"), limit(1)));
  if (snap.empty) return { ms: null, doc: null };
  const d = snap.docs[0].data();
  return { ms: toMs(d.fetched_at), doc: d };
}
async function load() {
  $("loaded").textContent = new Date().toLocaleString("ko-KR");
  const now = Date.now();
  // 카드별: 묶인 컬렉션의 최신 fetched_at을 모아 신선도·지연 판정
  const cardsEl = $("cards"); cardsEl.innerHTML = "";
  for (const c of CARDS) {
    const results = await Promise.all(c.collections.map(latestFetched));
    const { lastFetchedMs, anyEmpty } = cardFreshness(results.map(r => r.ms));
    const verdict = isOverdue(lastFetchedMs, c, now);
    const when = lastFetchedMs == null ? "데이터 없음" : relTime(lastFetchedMs, now);
    const flag = verdict.overdue
      ? `<span class="alert">⚠️ ${anyEmpty ? "데이터 없음/기한 초과" : "지연"}</span>` : "";
    const sample = sampleLine(c, results);
    const el = document.createElement("div"); el.className = "card";
    el.innerHTML = `<div class="row"><h2>${c.label}</h2><span class="mut">마지막 수집: ${when} · 기대: ${cadenceLabel(c.expectedSec)} ${flag}</span></div>`
                 + (sample ? `<div class="sample">${sample}</div>` : "");
    cardsEl.appendChild(el);
  }
  // 유니버스: index_members 3문서만 읽어 검색 후보 구성(추가 읽기 없음)
  const um = await getDocs(collection(db, "index_members"));
  universe = universeUnion(um.docs.map(d => d.data()));
}
function cadenceLabel(sec) { return sec <= 300 ? "5분" : sec <= 86400 ? "일" : "주"; }
function sampleLine(card, results) {
  if (card.key === "universe") {
    const im = results[0].doc;                 // index_members 첫 결과(문서 하나의 members)
    const n = im && im.members ? im.members.length : 0;
    return im ? `한 지수 구성 ${n}종목 (유니버스 전체는 드릴다운 검색)` : "";
  }
  const d = results[0].doc;
  if (!d) return "";
  if (card.key === "news")  return `최근: ${d.source || ""} · ${(d.title || "").slice(0, 60)}`;
  if (card.key === "intraday") return `최근 바: ${d.datetime || d.symbol || ""}`;
  if (d.symbol) return `샘플 종목: ${d.symbol}${d.date ? " · " + d.date : ""}`;
  return "";
}
$("refresh").onclick = () => load().catch(() => {});

// ── 드릴다운 ──
const DRILL = [                                // {coll, label, shape:'range'|'single', render}
  { coll: "profiles", label: "프로파일", shape: "single",
    render: d => `${d.data?.[0]?.companyName || d.symbol || ""} · ${d.data?.[0]?.sector || ""} · 시총 ${fmt(d.data?.[0]?.marketCap)}` },
  { coll: "ratios", label: "비율", shape: "range",
    render: d => `P/E ${num(d.priceToEarningsRatio)} · P/S ${num(d.priceToSalesRatio)} · P/B ${num(d.priceToBookRatio)} (${d.date || ""})` },
  { coll: "income", label: "손익", shape: "range",
    render: d => `매출 ${fmt(d.revenue)} · 순이익 ${fmt(d.netIncome)} (${d.date || ""})` },
  { coll: "balance", label: "대차", shape: "range",
    render: d => `총자산 ${fmt(d.totalAssets)} · 총부채 ${fmt(d.totalLiabilities)} (${d.date || ""})` },
  { coll: "cashflow", label: "현금흐름", shape: "range",
    render: d => `영업CF ${fmt(d.operatingCashFlow)} · FCF ${fmt(d.freeCashFlow)} (${d.date || ""})` },
  { coll: "estimates", label: "추정치(as-of)", shape: "range",
    render: d => `캡처 ${d.as_of || ""} · FY추정 ${d.data?.[0]?.epsAvg ?? "?"} EPS` },
  { coll: "price_targets", label: "목표가(as-of)", shape: "range",
    render: d => `consensus ${num(d.data?.[0]?.targetConsensus)} (H ${num(d.data?.[0]?.targetHigh)}/L ${num(d.data?.[0]?.targetLow)})` },
  { coll: "grades_consensus", label: "등급 분포(as-of)", shape: "range",
    render: d => `buy ${d.data?.[0]?.buy ?? "?"} · hold ${d.data?.[0]?.hold ?? "?"} · sell ${d.data?.[0]?.sell ?? "?"}` },
  { coll: "prices_eod", label: "배당조정 EOD", shape: "range",
    render: d => `최근 adjClose ${num(d.adjClose)} (${d.date || ""})` },
];
function num(v) { return (v == null || Number.isNaN(+v)) ? "?" : (+v).toLocaleString(); }
function fmt(v) { if (v == null) return "?"; const n = +v; return Math.abs(n) >= 1e9 ? (n/1e9).toFixed(1)+"B" : n.toLocaleString(); }

async function latestOf(coll, symbol) {        // 종목 최신 1건 — doc-id 범위(상한 sentinel)
  const { low, high } = idRange(symbol);
  const q = query(collection(db, coll),
    where(documentId(), ">=", low), where(documentId(), "<", high),
    orderBy(documentId(), "desc"), limit(1));
  const snap = await getDocs(q);
  return snap.empty ? null : snap.docs[0].data();
}
async function drill(symbol) {
  const detail = $("detail"); detail.innerHTML = `<div class="mut">${symbol} 불러오는 중…</div>`;
  const panel = document.createElement("div"); panel.className = "panel";
  for (const spec of DRILL) {
    let data = null;
    try {
      data = spec.shape === "single"
        ? await getDoc(doc(db, spec.coll, symbol)).then(s => s.exists() ? s.data() : null)
        : await latestOf(spec.coll, symbol);
    } catch (e) { data = { __err: e.code || "error" }; }
    const box = document.createElement("div"); box.className = "box";
    const body = data == null ? `<span class="none">데이터 없음(미수집)</span>`
              : data.__err ? `<span class="alert">오류: ${data.__err}</span>`
              : spec.render(data);
    box.innerHTML = `<b>${spec.label}</b><br>${body}`;
    panel.appendChild(box);
  }
  detail.innerHTML = `<h2 style="margin-top:12px">${symbol}</h2>`; detail.appendChild(panel);
}
$("search").oninput = (e) => {
  const hits = searchFilter(universe, e.target.value).slice(0, 12);
  const box = $("suggest");
  if (!hits.length) { box.style.display = "none"; return; }
  box.innerHTML = ""; box.style.display = "block";
  for (const h of hits) {
    const d = document.createElement("div"); d.textContent = `${h.symbol}  ${h.name || ""}`;
    d.onclick = () => { $("search").value = h.symbol; box.style.display = "none"; drill(h.symbol); };
    box.appendChild(d);
  }
};
</script>
</body>
</html>
```

- [ ] **Step 3: 배포 + 수동 검증(브라우저)**

`web/`를 Firebase Hosting에 배포하거나 로컬 서빙(`docs/operations.md §B`):
```bash
firebase deploy --only hosting
```
검증(브라우저에서 `.../dashboard.html`):
- 로그인 전: "구글로 로그인" 화면만.
- 허용목록 밖 계정: 로그인해도 "접근 권한 없음".
- 허용목록 계정: 카드 7개 + 신선도/지연 + 유니버스, 검색→종목 드릴다운(값 또는 "데이터 없음").
- 미수집 컬렉션 카드: `⚠️ 데이터 없음/기한 초과`.
Expected: 위 동작.

- [ ] **Step 4: 커밋**

```bash
git add web/dashboard.html
git commit -m "feat(dashboard): 수집 대시보드 페이지 — 인증 게이트 + 상태 카드 + 종목 드릴다운"
```

---

## Task 6: docs/firestore-contract.md — reader/공개read 2층 모델 반영

**Files:**
- Modify: `docs/firestore-contract.md`

- [ ] **Step 1: 현재 reader/공개read 서술 확인**

Run: `grep -n "공개 read\|reader\|fundamentals" docs/firestore-contract.md`
Expected: 상단 컬렉션 표의 reader 열, "인프라" 절의 공개 read 목록, 레거시 `fundamentals` 흔적이 보인다.

- [ ] **Step 2: 2층 모델로 갱신**

`docs/firestore-contract.md`에서:
- "인프라" 절의 공개 read 목록을 `items`·`prices`·`meta`(공개, index.html)로 고치고, 팩터/스트림 컬렉션은 **"인증+허용목록 게이트(대시보드) — `web/dashboard.html`, 규칙 `firestore.rules`"** 로 명시.
- 팩터 컬렉션의 reader를 "다운스트림(Admin SDK) + 허용목록 인증 사용자(대시보드)"로 갱신.
- 레거시 `fundamentals` 컬렉션/스키마 흔적이 남아 있으면 "폐기 — income/balance/cashflow가 대체" 한 줄로 정리(규칙에서도 제거됨).

- [ ] **Step 3: 커밋**

```bash
git add docs/firestore-contract.md
git commit -m "docs(contract): reader/공개read를 2층 모델(공개 뉴스 + 인증 게이트 팩터)로 갱신"
```

---

## Self-Review

- **Spec coverage:** 목적(상태 카드 §화면1 → Task 1·2·5, 드릴다운 §화면2 → Task 3·5), 읽기 전략(바운드·doc-id 범위 → Task 3·5), 인증 게이트(§배경·규칙 → Task 4), 지연 로직(빈결과·§2·주말 → Task 1), 테스트(§테스트 → Task 1-3), 계약 갱신(→ Task 6). 전 섹션 커버 확인.
- **Placeholder scan:** 코드 스텝은 실제 코드로 채움("적절한 처리" 류 없음). 런타임 설정(Task 4 Step 4)은 콘솔 절차라 코드 아님 — 명시.
- **Type consistency:** `isOverdue(lastFetchedMs, opts, nowMs)`·`cardFreshness([ms])`·`idRange(symbol)->{low,high}`·`universeUnion(docs)->{symbol,name}[]`가 Task 1-3 정의와 Task 5 소비에서 이름·형태 일치.

<!-- spec-review: passed -->
