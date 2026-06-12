from __future__ import annotations
import sqlite3
from datetime import datetime
from ..models import RawItem

_SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_items (
  id TEXT PRIMARY KEY, feed_id TEXT, source TEXT, asset_hint TEXT, language TEXT,
  url TEXT, title TEXT, body TEXT, published_at TEXT, fetched_at TEXT
);
CREATE TABLE IF NOT EXISTS feed_state (
  feed_id TEXT PRIMARY KEY, etag TEXT, last_modified TEXT, last_fetched TEXT
);
"""

class SqliteStore:
    def __init__(self, path):
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)

    def upsert_items(self, items: list[RawItem]) -> int:
        new = 0
        for it in items:
            cur = self.conn.execute(
                "INSERT OR IGNORE INTO raw_items "
                "(id,feed_id,source,asset_hint,language,url,title,body,published_at,fetched_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (it.id, it.feed_id, it.source, it.asset_hint, it.language, it.url, it.title,
                 it.body,
                 it.published_at.isoformat() if it.published_at else None,
                 it.fetched_at.isoformat()),
            )
            new += cur.rowcount
        self.conn.commit()
        return new

    def get_feed_state(self, feed_id: str) -> dict:
        row = self.conn.execute(
            "SELECT etag,last_modified,last_fetched FROM feed_state WHERE feed_id=?",
            (feed_id,)).fetchone()
        if not row:
            return {}
        return {
            "etag": row["etag"],
            "last_modified": row["last_modified"],
            "last_fetched": datetime.fromisoformat(row["last_fetched"]) if row["last_fetched"] else None,
        }

    def set_feed_state(self, feed_id: str, **fields) -> None:
        cur = self.get_feed_state(feed_id)
        etag = fields.get("etag", cur.get("etag"))
        last_modified = fields.get("last_modified", cur.get("last_modified"))
        lf = fields.get("last_fetched", cur.get("last_fetched"))
        lf_s = lf.isoformat() if isinstance(lf, datetime) else lf
        self.conn.execute(
            "INSERT INTO feed_state (feed_id,etag,last_modified,last_fetched) VALUES (?,?,?,?) "
            "ON CONFLICT(feed_id) DO UPDATE SET etag=excluded.etag,"
            "last_modified=excluded.last_modified,last_fetched=excluded.last_fetched",
            (feed_id, etag, last_modified, lf_s))
        self.conn.commit()

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM raw_items").fetchone()[0]
