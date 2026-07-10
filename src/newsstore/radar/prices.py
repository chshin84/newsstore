"""watchlist 일봉 적재 — yfinance 단일 소스(Stooq 봇차단 실측 기각, 스펙 §3.2).

sanity 경계(스펙 §3.2):
- 행 수준: high<low·close<=0·NaN(yfinance 결측일 실계약)은 flagged 격리(비파괴).
- 배치 수준: '신규 날짜 행 0건'(겹침 재수신은 신규가 아니다)을 달력일 기준으로 세어
  1일차는 결측 표기(휴장 가능), 3일 연속이면 크래시. 같은 날 재실행은 비증가(멱등).
"""
from __future__ import annotations

import datetime as dt
import json

from . import localdb


class PricesError(RuntimeError):
    pass


def default_fetch(ticker: str, start: str) -> list[dict]:
    import yfinance as yf
    hist = yf.Ticker(ticker).history(start=start, auto_adjust=False)
    rows = []
    for idx, r in hist.iterrows():
        rows.append({"date": idx.strftime("%Y-%m-%d"), "open": float(r["Open"]),
                     "high": float(r["High"]), "low": float(r["Low"]),
                     "close": float(r["Close"]),
                     "adj_close": float(r.get("Adj Close", r["Close"])),
                     "volume": float(r.get("Volume") or 0)})
    return rows


def _is_bad(r: dict) -> bool:
    vals = (r["open"], r["high"], r["low"], r["close"])
    if any(v != v for v in vals):                 # NaN(자기 자신과 다름)
        return True
    return r["high"] < r["low"] or r["close"] <= 0


def ingest(db, entries: list[dict], *, fetch=default_fetch, today: str | None = None) -> dict:
    today = today or localdb.today_kst()
    report: dict = {}
    for e in entries:
        t = e["ticker"]
        last = localdb.max_price_date(db, t)
        start = ((dt.date.fromisoformat(last) - dt.timedelta(days=7)).isoformat()
                 if last else "2024-01-01")
        rows = fetch(t, start)
        for r in rows:
            r["ticker"] = t
        if rows:
            localdb.upsert_prices(db, rows, source="yfinance")
            for r in rows:
                if _is_bad(r):
                    localdb.flag_price(db, t, r["date"], "sanity: NaN/high<low/close<=0")
        new_dates = [r["date"] for r in rows if not last or r["date"] > last]
        if not new_dates:
            if last and last >= today:                            # 이미 당일 데이터 보유 — 최신 상태
                localdb.set_meta(db, f"zero:{t}", json.dumps({"streak": 0, "last": today}))
                report[t] = {"status": "current", "rows": 0}
                continue
            state = json.loads(localdb.get_meta(db, f"zero:{t}") or '{"streak": 0, "last": ""}')
            if state["last"] != today:                            # 같은 날 재실행 비증가
                state = {"streak": state["streak"] + 1, "last": today}
                localdb.set_meta(db, f"zero:{t}", json.dumps(state))
            if state["streak"] >= 3:
                raise PricesError(f"{t}: 신규 날짜 0행 {state['streak']}일 연속 — 소스 파손 의심(3일 임계)")
            report[t] = {"status": "missing", "reason": f"신규 날짜 0행({state['streak']}일차 — 휴장 가능)"}
            continue
        localdb.set_meta(db, f"zero:{t}", json.dumps({"streak": 0, "last": today}))
        report[t] = {"status": "ok", "rows": len(new_dates)}
    return report
