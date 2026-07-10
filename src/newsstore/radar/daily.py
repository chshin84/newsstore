"""일보 조립 — radar_out/YYYY-MM-DD.md 한 장(스펙 §3.6 순서: 경고→게이트→필드 뷰(신호 4종)
→스테이션→부록). 데이터가 없으면 조용히 생략하지 않고 '결측: 사유'를 표기한다(FAIL-LOUD).

뷰 임계(결정④ — 커널은 원값, 여기서만 필터): 신호1 24h≥3건 AND (z=='new' or z≥2.0),
신호3 빈도≥3 AND (z=='new' or z≥2.0), 신호2는 신규 간선만, 신호4는 확산 2렌즈 이상.
"""
from __future__ import annotations

import datetime as dt

from . import kernel, ledgers, localdb, match, station, watchlist

FIELD_Z = 2.0
FIELD_MIN = 3
BASELINE_28 = 28
BASELINE_30 = 30
MIN_RATIO = 2 / 3


def _by_day(rows: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for r in rows:
        out.setdefault(localdb.kst_day(r.get("fetched_at") or ""), []).append(r)
    return out


def _passes(cnt: int, z, *, min_cnt: int) -> bool:
    return cnt >= min_cnt and (z == "new" or (isinstance(z, float) and z >= FIELD_Z))


def _field_view(rows: list[dict], vocab: list[str], today: str) -> list[str]:
    lines = [f"## 필드 뷰 (뷰 임계: 빈도≥{FIELD_MIN} & z≥{FIELD_Z} 또는 신규)"]
    byday = _by_day(rows)
    t = dt.date.fromisoformat(today)
    base_days_28 = [(t - dt.timedelta(days=i)).isoformat() for i in range(1, BASELINE_28 + 1)]
    have = [d for d in base_days_28 if byday.get(d)]
    ok, reason = kernel.baseline_coverage(have, window_days=BASELINE_28, min_ratio=MIN_RATIO)

    # 신호1 — 렌즈별 당일 카운트 vs 28일 일별 분포 z
    lines.append("### 신호1 테마 속도")
    if not ok:
        lines.append(f"- {reason}")
    else:
        per_today = kernel.article_lenses(byday.get(today, []))
        counts_today = kernel.lens_counts_from(per_today)
        daily_counts: dict[str, list[int]] = {}
        for d in base_days_28:
            cd = kernel.lens_counts_from(kernel.article_lenses(byday.get(d, [])))
            for lens in set(list(cd) + list(counts_today)):
                daily_counts.setdefault(lens, []).append(cd.get(lens, 0))
        shown = False
        for lens, cnt in sorted(counts_today.items(), key=lambda x: -x[1]):
            z = kernel.zscore(cnt, daily_counts.get(lens, []))
            if _passes(cnt, z, min_cnt=FIELD_MIN):
                lines.append(f"- {lens}: 당일 {cnt}건, z={z if z == 'new' else f'{z:.1f}'}")
                shown = True
        if not shown:
            lines.append("- 해당 없음")

    # 신호2 — 금주 간선 vs 직전 8주(신규 간선만)
    lines.append("### 신호2 그래프 드리프트(신규 간선)")
    week_of = lambda ds: dt.date.fromisoformat(ds).isocalendar()[:2]
    cur_week = week_of(today)
    cur_rows, prev_weeks_rows = [], {}
    for d, rs in byday.items():
        if not d:
            continue
        w = week_of(d)
        if w == cur_week:
            cur_rows += rs
        else:
            prev_weeks_rows.setdefault(w, []).extend(rs)
    prev_edge_sets = [kernel.cooccur_edges(rs, vocab, match.find_alias)
                      for _w, rs in sorted(prev_weeks_rows.items())[-8:]]
    fresh = kernel.new_edges(kernel.cooccur_edges(cur_rows, vocab, match.find_alias), prev_edge_sets)
    lines += [f"- {a} — {b} (금주 신규)" for a, b in sorted(fresh)] or ["- 해당 없음"]

    # 신호3 — 어휘 창발(직전 W=3일 창 vs 창 뒤 30일 일별 분포 — 스펙 §5 정의 그대로)
    lines.append("### 신호3 어휘 창발 (radar_vocab 승격 후보)")
    W3 = 3
    now_days = [(t - dt.timedelta(days=i)).isoformat() for i in range(W3)]
    base_days_30 = [(t - dt.timedelta(days=W3 + i)).isoformat() for i in range(BASELINE_30)]
    have30 = [d for d in base_days_30 if byday.get(d)]
    ok30, reason30 = kernel.baseline_coverage(have30, window_days=BASELINE_30, min_ratio=MIN_RATIO)
    emergent: list = []
    if not ok30:
        lines.append(f"- {reason30}")
    else:
        titles_now = [r.get("title") or "" for d in now_days for r in byday.get(d, [])]
        baseline = [[r.get("title") or "" for r in byday.get(d, [])] for d in base_days_30]
        emergent = [(term, cnt, z) for term, cnt, z in
                    kernel.emerging_terms(titles_now, baseline, w_days=W3)
                    if _passes(cnt, z, min_cnt=FIELD_MIN)][:15]
        lines += [f"- {term}: {cnt}건, z={z if z == 'new' else f'{z:.1f}'}"
                  for term, cnt, z in emergent] or ["- 해당 없음"]

    # 신호4 — 크로스렌즈 확산(창발 어휘+vocab의 금주 렌즈 확산)
    lines.append("### 신호4 크로스렌즈 확산")
    terms4 = [term for term, _c, _z in emergent] + vocab
    per_cur = kernel.article_lenses(cur_rows)
    term_hits = {term: [r["id"] for r in cur_rows
                        if match.find_alias(term, (r.get("title") or ""))]
                 for term in terms4}
    spread = {k: v for k, v in kernel.cross_lens_spread(term_hits, per_cur).items() if v >= 2}
    lines += [f"- {term}: {n}개 렌즈" for term, n in
              sorted(spread.items(), key=lambda x: -x[1])[:10]] or ["- 해당 없음"]
    return lines


def build_report(items_db, prices_db, *, today: str,
                 gates_path="radar/gates.yaml", frames_path="radar/frames.json",
                 journal_path="journal/journal.jsonl",
                 watchlist_path="config/watchlist.yaml",
                 vocab_path="config/radar_vocab.yaml") -> str:
    entries = watchlist.load_watchlist(watchlist_path)
    gates = ledgers.load_gates(gates_path)
    frames = ledgers.load_frames(frames_path, gate_ids={g["id"] for g in gates})
    journal = ledgers.load_journal(journal_path)
    vocab = match.with_watchlist_aliases(match.load_vocab(vocab_path), entries)
    rows = kernel.dedup(localdb.load_items(items_db))

    out = [f"# 레이더 일보 {today} (KST 기준)", ""]
    overdue = ledgers.overdue_pending(gates, today=today)
    if overdue:
        out.append("## 경고")
        out += [f"- pending 만기 경과: {g['id']} ({g['date']}) — 판정 필요" for g in overdue]
    out.append("## 오늘의 게이트 (±2일)")
    due = ledgers.due_around(gates, today=today)
    out += [f"- {g['date']} **{g['id']}** — {g['test']}" for g in due] or ["- 해당 없음"]
    out += _field_view(rows, vocab, today)

    out.append("## 종목 스테이션")
    plans = ledgers.active_plans(journal, today=today)
    total_cov = 0
    for e in watchlist.station_entries(entries):
        out.append(f"### {e['label']} ({e['ticker']})")
        cov = station.coverage(e, rows)
        total_cov += cov["matched"]
        out.append(f"- 커버리지: 매칭 {cov['matched']}건 · 소스 {cov['sources']}종 · "
                   f"본문 보유율 {cov['body_ratio']:.0%} — 이 페이지는 피드가 본 세계다 — 판단 전 웹 확인")
        board = station.status_board(e, prices_db)
        close = None
        if board.get("missing"):
            out.append(f"- 상태판 결측: {board['reason']}")
        else:
            close = board["close"]
            out.append(f"- 상태판({board['basis']}): 종가 {board['close']:,.0f} · "
                       f"전고점 대비 {board['drawdown']:+.1%} · MDD {board['mdd']:+.1%}")
        for g in station.target_gates(e, gates, today=today):
            out.append(f"- 게이트: {g['date']} **{g['id']}** — {g['test']}")
        for p in [p for p in plans if p["target"] == e["id"]]:      # 플랜은 가격과 독립 표기
            chk = station.plan_check(p, close=close)
            mark = (" ⚠️구간 밖(추격 주의)" if chk["out_of_band"]
                    else " (가격 결측 — 비교 불가)" if chk["out_of_band"] is None else "")
            out.append(f"- 플랜 {p['id']}: 구간 {chk['band']} · 무효화 {chk['invalidation']}"
                       f" · 시한 {chk['by']}{mark}")
        arr = station.arrival_news(e, rows, today=today)
        spark = "·".join(str(n) for n in reversed(arr["baseline_7d"]))
        out.append(f"- 도착 뉴스: 전수 {arr['total']}건(표시 {len(arr['shown'])}·접힘 {arr['folded']})"
                   f" · 당일(KST) {arr['count_today']}건 · 7d {spark}")
        for h in arr["shown"]:
            out.append(f"  - {h.get('title')} (매칭: {h['alias']}@{h['pos']}, {h.get('source')})")
        refs = station.frame_refs(e, frames)
        if refs:
            out.append("- 프레임 참조: " + ", ".join(f"{r['lens']}/{r['axis']}/{r['id']}" for r in refs))
    out.append("## 부록 — 커버리지 총계")
    out.append(f"- 코퍼스 {len(rows)}건(중복 제거 후) · 스테이션 매칭 합계 {total_cov}건")
    return "\n".join(out) + "\n"
