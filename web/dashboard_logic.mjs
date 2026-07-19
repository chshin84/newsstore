// 수집 대시보드 순수 로직 — SSOT 상수 + 판정. 페이지·node 테스트가 공유한다.
// 문턱은 계약값(주기·60일 TTL 데드라인)에서 도출(매직넘버 금지). 계약: docs/firestore-contract.md.

export const TTL_DAYS = 60;
export const OVERDUE_FACTOR = 3;    // §1: 기대주기의 몇 배까지 정상으로 볼지(보수적)
export const LEAD_FRACTION = 0.4;   // §2: 지연 문턱 = TTL_DAYS × 이 비율(데드라인 대비 리드타임 확보)

// 실제 수집 스케줄(Cloud Scheduler cron)의 UI측 사본(초).
// 클라이언트는 스케줄러를 못 읽어 불가피한 두 번째 출처 — 스케줄을 바꾸면 여기도 바꾼다.
// (operations.md 리소스 표의 Cloud Scheduler `newsstore-5min` 행과 일치해야 함.)
export const SCHEDULE = { intraday: 300 };

// 카드 SSOT — 뉴스 수집 표면(`items`)만 본다.
// marketData=주말 완화 대상, backfillImpossible=데드라인 문턱(뉴스는 둘 다 해당 없음).
export const CARDS = [
  { key: 'news',       label: '뉴스',              collections: ['items'],
    expectedSec: SCHEDULE.intraday, marketData: false, backfillImpossible: false },
];

// 스케줄 잡 헬스 — 각 잡이 실행 상태를 job_health/{key}에 남긴다(entrypoints/_health.job_health).
// 백필(backfill_embed)은 수동 일회성이라 제외한다(스케줄이 없어 항상 stale=오탐).
export const JOBS = [
  { key: 'collector', label: '뉴스 수집',    expectedSec: SCHEDULE.intraday },
];

// 잡 헬스 판정. h={lastStatus, fetchedMs}(Firestore Timestamp→ms 변환은 호출자).
// 우선순위: 실패 > 멈춤(running 고착=하드 kill) > 지연(안 돎)·미실행 > 정상. level: ok|warn|bad.
export function jobVerdict(h, expectedSec, nowMs, overdueFactor = OVERDUE_FACTOR) {
  if (!h || h.lastStatus == null) return { level: 'bad', text: '미실행' };
  const staleMs = expectedSec * 1000 * overdueFactor;
  const age = (h.fetchedMs == null || !Number.isFinite(h.fetchedMs)) ? Infinity : (nowMs - h.fetchedMs);
  if (h.lastStatus === 'fail') return { level: 'bad', text: '실패' };
  if (h.lastStatus === 'running')
    return age > staleMs ? { level: 'bad', text: '멈춤(정지)' } : { level: 'warn', text: '실행 중' };
  return age > staleMs ? { level: 'bad', text: '지연(안 돎)' } : { level: 'ok', text: '정상' };
}

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
