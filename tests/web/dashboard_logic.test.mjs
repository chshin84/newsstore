import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  SCHEDULE, CARDS, JOBS, isWeekend, isOverdue, relTime, cardFreshness, jobVerdict,
} from '../../web/dashboard_logic.mjs';

const MON = Date.UTC(2026, 6, 13, 12, 0, 0);   // 2026-07-13 월 12:00 UTC
const SAT = Date.UTC(2026, 6, 11, 12, 0, 0);   // 2026-07-11 토

test('isWeekend: 토/일만 true', () => {
  assert.equal(isWeekend(SAT), true);
  assert.equal(isWeekend(MON), false);
});

test('빈 컬렉션(null/NaN)은 항상 경보 — TTL 만료가 정상으로 오탐 안 됨', () => {
  assert.equal(isOverdue(null, { expectedSec: SCHEDULE.intraday }, MON).overdue, true);
  assert.equal(isOverdue(NaN, { expectedSec: SCHEDULE.intraday }, MON).overdue, true);
});

test('정상 주기 내면 지연 아님, OVERDUE_FACTOR배 초과면 지연', () => {
  const opts = { expectedSec: SCHEDULE.intraday };
  const fresh = MON - SCHEDULE.intraday * 1000;               // 1주기 전
  const stale = MON - SCHEDULE.intraday * 1000 * 4;           // 4주기 전(>3배)
  assert.equal(isOverdue(fresh, opts, MON).overdue, false);
  assert.equal(isOverdue(stale, opts, MON).overdue, true);
});

test('CARDS는 뉴스(items) 카드만 덮고, expectedSec는 SCHEDULE 값', () => {
  assert.deepEqual(CARDS.map(c => c.key), ['news']);
  assert.deepEqual(CARDS.flatMap(c => c.collections), ['items']);
  const sched = new Set(Object.values(SCHEDULE));
  for (const c of CARDS) assert.ok(sched.has(c.expectedSec), `${c.key} expectedSec는 SCHEDULE 값`);
});

test('JOBS는 collector 하나(뉴스 수집 잡)', () => {
  assert.deepEqual(JOBS.map(j => j.key), ['collector']);
});

test('jobVerdict: 실패 > 멈춤(running 고착) > 지연/미실행 > 정상', () => {
  const exp = SCHEDULE.intraday;
  const staleAge = exp * 1000 * 5;                                        // 문턱(3배) 초과
  assert.equal(jobVerdict(null, exp, MON).level, 'bad');                                          // 미실행
  assert.equal(jobVerdict({ lastStatus: 'fail', fetchedMs: MON }, exp, MON).level, 'bad');        // 실패
  assert.equal(jobVerdict({ lastStatus: 'running', fetchedMs: MON }, exp, MON).level, 'warn');    // 실행 중
  assert.equal(jobVerdict({ lastStatus: 'running', fetchedMs: MON - staleAge }, exp, MON).level, 'bad'); // 멈춤(정지)
  assert.equal(jobVerdict({ lastStatus: 'ok', fetchedMs: MON }, exp, MON).level, 'ok');           // 정상
  assert.equal(jobVerdict({ lastStatus: 'ok', fetchedMs: MON - staleAge }, exp, MON).level, 'bad'); // 지연(안 돎)
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
