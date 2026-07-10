"""로컬 SQLite 2종 — local.db(Firestore 캐시)·prices.db(야후 캐시). 전부 upsert 멱등.
'오늘'은 KST 달력일 규약 — kst_day가 UTC 타임스탬프를 KST 일자로 변환한다."""
from __future__ import annotations

import datetime as dt
import sqlite3

KST = dt.timezone(dt.timedelta(hours=9))
ITEM_COLS = ("id", "feed_id", "source", "asset_hint", "language", "url", "title",
             "body", "published_at", "fetched_at", "kind")


def kst_day(ts: str) -> str:
    if not ts:
        return ""
    d = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return d.astimezone(KST).date().isoformat()


def today_kst() -> str:
    return dt.datetime.now(tz=KST).date().isoformat()


def connect_items(path: str) -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.execute(f"""CREATE TABLE IF NOT EXISTS items (
        {ITEM_COLS[0]} TEXT PRIMARY KEY,
        {", ".join(c + " TEXT" for c in ITEM_COLS[1:])})""")
    db.execute("CREATE TABLE IF NOT EXISTS sync_state (key TEXT PRIMARY KEY, value TEXT)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_items_fetched ON items(fetched_at)")
    return db


def upsert_items(db, rows: list[dict]) -> None:
    db.executemany(
        f"INSERT OR REPLACE INTO items ({','.join(ITEM_COLS)}) VALUES ({','.join('?' * len(ITEM_COLS))})",
        [tuple(r.get(c) for c in ITEM_COLS) for r in rows])
    db.commit()


def load_items(db) -> list[dict]:
    return [dict(zip(ITEM_COLS, row)) for row in
            db.execute(f"SELECT {','.join(ITEM_COLS)} FROM items")]


def count_items(db) -> int:
    return db.execute("SELECT COUNT(*) FROM items").fetchone()[0]


def get_watermark(db) -> str | None:
    row = db.execute("SELECT value FROM sync_state WHERE key='watermark'").fetchone()
    return row[0] if row else None


def set_watermark(db, ts: str) -> None:
    db.execute("INSERT OR REPLACE INTO sync_state (key, value) VALUES ('watermark', ?)", (ts,))
    db.commit()


def connect_prices(path: str) -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.execute("""CREATE TABLE IF NOT EXISTS prices (
        ticker TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL,
        adj_close REAL, volume REAL, source TEXT, fetched_at TEXT,
        flagged TEXT, PRIMARY KEY (ticker, date))""")
    db.execute("CREATE TABLE IF NOT EXISTS prices_meta (key TEXT PRIMARY KEY, value TEXT)")
    return db


def upsert_prices(db, rows: list[dict], *, source: str) -> None:
    db.executemany(
        """INSERT INTO prices (ticker,date,open,high,low,close,adj_close,volume,source,fetched_at,flagged)
           VALUES (?,?,?,?,?,?,?,?,?,datetime('now'),NULL)
           ON CONFLICT(ticker,date) DO UPDATE SET open=excluded.open, high=excluded.high,
             low=excluded.low, close=excluded.close, adj_close=excluded.adj_close,
             volume=excluded.volume, source=excluded.source, fetched_at=excluded.fetched_at""",
        [(r["ticker"], r["date"], r["open"], r["high"], r["low"], r["close"],
          r["adj_close"], r["volume"], source) for r in rows])
    db.commit()


def count_prices(db, ticker: str) -> int:
    return db.execute("SELECT COUNT(*) FROM prices WHERE ticker=?", (ticker,)).fetchone()[0]


def max_price_date(db, ticker: str) -> str | None:
    return db.execute("SELECT MAX(date) FROM prices WHERE ticker=?", (ticker,)).fetchone()[0]


def flag_price(db, ticker: str, date: str, reason: str) -> None:
    db.execute("UPDATE prices SET flagged=? WHERE ticker=? AND date=?", (reason, ticker, date))
    db.commit()


def load_closes(db, ticker: str, *, include_flagged: bool = False) -> list[tuple[str, float]]:
    q = "SELECT date, close FROM prices WHERE ticker=?"
    if not include_flagged:
        q += " AND flagged IS NULL"
    return db.execute(q + " ORDER BY date", (ticker,)).fetchall()


def get_meta(db, key: str) -> str | None:
    row = db.execute("SELECT value FROM prices_meta WHERE key=?", (key,)).fetchone()
    return row[0] if row else None


def set_meta(db, key: str, value: str) -> None:
    db.execute("INSERT OR REPLACE INTO prices_meta (key, value) VALUES (?, ?)", (key, value))
    db.commit()
