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
