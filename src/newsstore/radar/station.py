"""종목 스테이션(1차 뷰) — 판단하지 않는다. 수신 준비만 한다(스펙 §4).
약속은 '피드-상대 전수': 무임계로 전부 세고, 표시는 최신순 20건+접기(임계가 아니라 표시 규칙)."""
from __future__ import annotations

from . import ledgers, localdb, match

SHOW_LIMIT = 20


def _matched(entry: dict, items: list[dict]) -> list[dict]:
    hits = []
    for r in items:
        text = (r.get("title") or "") + " " + (r.get("body") or "")[:200]
        m = match.find_any(entry["aliases"], text)
        if m:
            hits.append({**r, "alias": m[0], "pos": m[1]})
    return hits


def coverage(entry: dict, items: list[dict]) -> dict:
    hits = _matched(entry, items)
    with_body = [h for h in hits if (h.get("body") or "").strip()]
    return {"matched": len(hits),
            "sources": len({h.get("source") for h in hits}),
            "body_ratio": (len(with_body) / len(hits)) if hits else 0.0}


def arrival_news(entry: dict, items: list[dict], *, today: str) -> dict:
    import datetime as dt
    hits = _matched(entry, items)
    day = lambda r: localdb.kst_day(r.get("fetched_at") or "")
    count_today = sum(1 for h in hits if day(h) == today)
    t = dt.date.fromisoformat(today)
    baseline_7d = [sum(1 for h in hits if day(h) == (t - dt.timedelta(days=i)).isoformat())
                   for i in range(1, 8)]
    hits.sort(key=lambda h: h.get("fetched_at") or "", reverse=True)
    return {"total": len(hits), "hits": hits, "shown": hits[:SHOW_LIMIT],
            "folded": max(0, len(hits) - SHOW_LIMIT),
            "count_today": count_today, "baseline_7d": baseline_7d}


def status_board(entry: dict, prices_db) -> dict:
    closes = localdb.load_closes(prices_db, entry["ticker"])
    if not closes:
        return {"missing": True, "reason": f"{entry['ticker']}: 가격 데이터 없음"}
    close = closes[-1][1]
    peak = max(c for _d, c in closes)
    running_peak, mdd = closes[0][1], 0.0
    for _d, c in closes:
        running_peak = max(running_peak, c)
        mdd = min(mdd, c / running_peak - 1)
    return {"close": close, "peak": peak, "drawdown": close / peak - 1, "mdd": mdd,
            "basis": f"{entry['ticker']} 종가"}


def plan_check(plan: dict, *, close: float | None) -> dict:
    lo, hi = plan["band"]
    return {"plan_id": plan["id"], "band": plan["band"], "close": close,
            "out_of_band": (None if close is None else not (lo <= close <= hi)),
            "invalidation": plan["invalidation"], "by": plan["by"]}


def target_gates(entry: dict, gates: list[dict], *, today: str) -> list[dict]:
    mine = ledgers.gates_for_target(gates, entry["id"])
    return ledgers.due_around(mine, today=today, window_days=30)   # 종목 게이트는 한 달 창으로 상기


def frame_refs(entry: dict, frames: dict) -> list[dict]:
    refs = []
    for lens, frame in frames.items():
        for ax, poles in frame.items():
            for p in poles:
                blob = " ".join(str(p.get(k, "")) for k in ("id", "label", "evidence", "test"))
                if any(a in blob for a in entry["aliases"]) or entry["id"] in blob:
                    refs.append({"lens": lens, "axis": ax, "id": p["id"], "label": p["label"],
                                 "status": p.get("status", "active")})
    return refs
