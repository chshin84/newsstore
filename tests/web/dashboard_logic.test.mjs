import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  SCHEDULE, CARDS, TTL_DAYS, isWeekend, isOverdue, relTime, cardFreshness,
  idRange, universeUnion, searchFilter, HIGH_SENTINEL,
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
