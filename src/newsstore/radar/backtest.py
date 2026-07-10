"""신호 소급 실행 러너 — 신호3 캘리브레이션 + 신호1 평시 오탐(요일 분해) + 신호2 산출량 실측.
프로덕션 커널 함수를 임포트해 --as-of만 주입한다(로직 복제 금지 — SSOT, 스펙 결정⑧).
파라미터는 평시 오탐률로 좁히고 리드타임은 채점만(과적합 방지 — 스펙 §9)."""
from __future__ import annotations

import datetime as dt

from . import kernel, localdb, match

# 스펙 §9 사전 등록 타깃 10종 — 실행 시점에 고르지 않는다.
TARGET_TERMS = ["엔드게임", "사이드카", "서킷브레이커", "변동성의 덫", "반사성",
                "레버리지", "ADR", "북빌딩", "디레버리징", "HBM"]


def _rows_by_day(db) -> dict[str, list[dict]]:
    """프로덕션(daily)과 동일한 입력 파이프라인 — 전 컬럼 로드 + dedup + KST 버킷.
    측정기가 입력을 다르게 복제하면 캘리브레이션이 오염된다(재리뷰 major — 실제
    asset_hint·language·body를 그대로 쓰고, kr_stock 하드코딩·UTC substr 경계 오차를 제거)."""
    rows = kernel.dedup(localdb.load_items(db))
    out: dict[str, list[dict]] = {}
    for r in rows:
        out.setdefault(localdb.kst_day(r.get("fetched_at") or ""), []).append(r)
    return out


def _titles_by_day(db, start: str, end: str) -> dict[str, list[str]]:
    byday = _rows_by_day(db)
    return {d: [r.get("title") or "" for r in rs]
            for d, rs in byday.items() if d and start <= d <= end}


def corpus_presence(db, terms: list[str]) -> dict[str, int]:
    out = {}
    for t in terms:
        out[t] = db.execute("SELECT COUNT(*) FROM items WHERE title LIKE ?",
                            (f"%{t}%",)).fetchone()[0]
    return out


def _emerging_on(byday: dict[str, list[str]], day: str, *, w_days: int, b_days: int = 30):
    d = dt.date.fromisoformat(day)
    now = [t for i in range(w_days)
           for t in byday.get((d - dt.timedelta(days=i)).isoformat(), [])]
    baseline = [byday.get((d - dt.timedelta(days=w_days + i)).isoformat(), [])
                for i in range(b_days)]
    return kernel.emerging_terms(now, baseline, w_days=w_days)


def _detected(hits, *, m: int, z: float) -> set[str]:
    return {t for t, cnt, zz in hits
            if cnt >= m and (zz == "new" or (isinstance(zz, float) and zz >= z))}


def lead_times(db, *, terms: list[str], event_day: str, start: str, end: str,
               w_days: int, m: int, z: float) -> dict[str, int | None]:
    byday = _titles_by_day(db, "2026-01-01", end)
    res: dict[str, int | None] = {t: None for t in terms}
    d, endd, ev = (dt.date.fromisoformat(x) for x in (start, end, event_day))
    while d <= endd:
        got = _detected(_emerging_on(byday, d.isoformat(), w_days=w_days), m=m, z=z)
        for t in terms:
            if res[t] is None and t in got:
                res[t] = (d - ev).days
        d += dt.timedelta(days=1)
    return res


def false_positive_rate(db, *, month_start: str, month_end: str, w_days: int, m: int, z: float) -> float:
    byday = _titles_by_day(db, "2026-01-01", month_end)
    d, endd = dt.date.fromisoformat(month_start), dt.date.fromisoformat(month_end)
    days = total = 0
    while d <= endd:
        total += len(_detected(_emerging_on(byday, d.isoformat(), w_days=w_days), m=m, z=z))
        days += 1
        d += dt.timedelta(days=1)
    return total / max(days, 1)


def signal1_fp_by_weekday(db, *, month_start: str, month_end: str) -> dict[int, float]:
    """요일(0=월)별 '유의 렌즈 수' 평균 — 주말 왜곡 실측(스펙 §5 요일 가드 판정 근거).
    입력은 _rows_by_day(실제 asset_hint·language) — 프로덕션 동일 경로."""
    byday = _rows_by_day(db)
    lenses_by_day = {d: kernel.lens_counts_from(kernel.article_lenses(rs))
                     for d, rs in byday.items()}                  # 일별 1회만 분류(재분류 금지)
    out: dict[int, list[int]] = {i: [] for i in range(7)}
    d, endd = dt.date.fromisoformat(month_start), dt.date.fromisoformat(month_end)
    while d <= endd:
        cnt_today = lenses_by_day.get(d.isoformat(), {})
        base: dict[str, list[int]] = {}
        for i in range(1, 29):
            cd = lenses_by_day.get((d - dt.timedelta(days=i)).isoformat(), {})
            for lens in set(list(cd) + list(cnt_today)):
                base.setdefault(lens, []).append(cd.get(lens, 0))
        sig = 0
        for lens, c in cnt_today.items():
            z = kernel.zscore(c, base.get(lens, []))
            if c >= 3 and (z == "new" or (isinstance(z, float) and z >= 2.0)):
                sig += 1
        out[d.weekday()].append(sig)
        d += dt.timedelta(days=1)
    return {wd: (sum(v) / len(v) if v else 0.0) for wd, v in out.items()}


def signal2_weekly_volume(db, *, weeks: int, as_of: str) -> list[int]:
    """주별 신규 간선 수 — '월 3건 미만이면 필드 뷰 강등'(스펙 §5) 판정 근거.
    입력은 _rows_by_day(실제 body 포함) — 프로덕션 cooccur_edges와 동일 재료."""
    byday = _rows_by_day(db)
    vocab = match.load_vocab()
    week_rows: dict[tuple, list[dict]] = {}
    for d, rs in byday.items():
        if not d or d > as_of:
            continue
        w = dt.date.fromisoformat(d).isocalendar()[:2]
        week_rows.setdefault(w, []).extend(rs)
    ordered = sorted(week_rows.items())[-weeks:]
    edge_sets = [kernel.cooccur_edges(rs, vocab, match.find_alias) for _w, rs in ordered]
    return [len(kernel.new_edges(cur, edge_sets[:i])) for i, cur in enumerate(edge_sets)]


def main(as_of: str | None = None) -> None:
    db = localdb.connect_items("data/local.db")
    event = as_of or "2026-07-07"
    present = corpus_presence(db, TARGET_TERMS)
    print(f"타깃 용어 실재(사전 게이트): {present}")
    if sum(1 for v in present.values() if v > 0) < 2:
        print("중단: 코퍼스 실재 용어 2개 미만 — 제목-only 입력 재설계 필요(스펙 §9)")
        return
    for w in (1, 3, 7):
        for m in (3, 5, 10):
            for z in (2.0, 3.0):
                lt = lead_times(db, terms=TARGET_TERMS, event_day=event,
                                start="2026-06-20", end="2026-07-10", w_days=w, m=m, z=z)
                fp = false_positive_rate(db, month_start="2026-05-01", month_end="2026-05-31",
                                         w_days=w, m=m, z=z)
                found = {k: v for k, v in lt.items() if v is not None}
                print(f"W={w} m={m} z={z}: 검출 {len(found)}/{len(TARGET_TERMS)}, "
                      f"리드타임 {found}, 평시 오탐 {fp:.1f}건/일")
    print("신호1 요일별 유의 렌즈 평균:", signal1_fp_by_weekday(
        db, month_start="2026-05-01", month_end="2026-05-31"))
    print("신호2 주별 신규 간선(8주):", signal2_weekly_volume(db, weeks=8, as_of=event))
