from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from ..models import RawItem
from ..enrich.cluster import add_vectors

SCHEMA_VERSION = 1

# Fresh DBs get the full target schema here; pre-existing DBs are upgraded by
# _migrate() via ALTER TABLE. Step-2 consumes raw_items WHERE processed=0.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_items (
  id TEXT PRIMARY KEY, feed_id TEXT, source TEXT, asset_hint TEXT, language TEXT,
  url TEXT, title TEXT, body TEXT, published_at TEXT, fetched_at TEXT,
  processed INTEGER NOT NULL DEFAULT 0, processed_at TEXT,
  kind TEXT, tags TEXT, embedding TEXT, story_id TEXT
);
CREATE TABLE IF NOT EXISTS feed_state (
  feed_id TEXT PRIMARY KEY, etag TEXT, last_modified TEXT, last_fetched TEXT
);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS stories (
  id TEXT PRIMARY KEY, title TEXT, centroid_sum TEXT, count INTEGER,
  member_ids TEXT, entities TEXT, first_seen TEXT, last_seen TEXT, status TEXT
);
"""

_ITEM_COLS = ("id", "feed_id", "source", "asset_hint", "language",
              "url", "title", "body", "published_at", "fetched_at")


def _migrate(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version < 1:
        # Legacy DBs created before the processed columns existed lack them;
        # add idempotently (fresh DBs already have them from _SCHEMA above).
        cols = {r[1] for r in conn.execute("PRAGMA table_info(raw_items)")}
        if "processed" not in cols:
            conn.execute("ALTER TABLE raw_items ADD COLUMN processed INTEGER NOT NULL DEFAULT 0")
        if "processed_at" not in cols:
            conn.execute("ALTER TABLE raw_items ADD COLUMN processed_at TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_unprocessed "
                     "ON raw_items(processed)")
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    # Step-2 enrichment 컬럼 (없으면 추가)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(raw_items)")}
    for col, decl in [("kind", "TEXT"), ("tags", "TEXT"), ("embedding", "TEXT"), ("story_id", "TEXT")]:
        if col not in cols:
            conn.execute(f"ALTER TABLE raw_items ADD COLUMN {col} {decl}")
    conn.commit()


def _row_to_item(row: sqlite3.Row) -> RawItem:
    def _dt(v):
        return datetime.fromisoformat(v) if v else None
    return RawItem(
        id=row["id"], feed_id=row["feed_id"], source=row["source"],
        asset_hint=row["asset_hint"] or "", language=row["language"] or "en",
        url=row["url"], title=row["title"], body=row["body"] or "",
        published_at=_dt(row["published_at"]), fetched_at=_dt(row["fetched_at"]),
    )


class SqliteStore:
    def __init__(self, path):
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        # WAL lets a reader (future Step-2) and the writer coexist; busy_timeout
        # avoids 'database is locked' if two passes briefly overlap.
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        _migrate(self.conn)

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

    def get_unprocessed(self, limit: int | None = None) -> list[RawItem]:
        """Oldest-first raw items not yet handed to Step-2 (processed=0)."""
        sql = (f"SELECT {','.join(_ITEM_COLS)} FROM raw_items "
               "WHERE processed=0 ORDER BY fetched_at")
        params: tuple = ()
        if limit is not None:
            sql += " LIMIT ?"
            params = (int(limit),)
        return [_row_to_item(r) for r in self.conn.execute(sql, params)]

    def mark_processed(self, ids: list[str], processed_at: datetime | None = None) -> int:
        """Mark ids as processed (idempotent). Returns rows actually changed."""
        if not ids:
            return 0
        ts = (processed_at or datetime.now(timezone.utc)).isoformat()
        placeholders = ",".join("?" * len(ids))
        cur = self.conn.execute(
            f"UPDATE raw_items SET processed=1, processed_at=? "
            f"WHERE id IN ({placeholders}) AND processed=0",
            (ts, *ids))
        self.conn.commit()
        return cur.rowcount

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM raw_items").fetchone()[0]

    def set_meta(self, key: str, value: dict) -> None:
        self.conn.execute(
            "INSERT INTO meta (key,value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, json.dumps(value)))
        self.conn.commit()

    def save_enrichment(self, item_id, *, kind, tags, embedding, story_id) -> None:
        self.conn.execute(
            "UPDATE raw_items SET kind=?, tags=?, embedding=?, story_id=? WHERE id=?",
            (kind, json.dumps(list(tags)),
             json.dumps(list(embedding)) if embedding is not None else None,
             story_id, item_id))
        self.conn.commit()

    def create_story(self, story_id, *, title, vec, member_id, entities, now) -> None:
        self.conn.execute(
            "INSERT INTO stories (id,title,centroid_sum,count,member_ids,entities,first_seen,last_seen,status) "
            "VALUES (?,?,?,?,?,?,?,?, 'open')",
            (story_id, title, json.dumps(list(vec)), 1, json.dumps([member_id]),
             json.dumps(list(entities)), now.isoformat(), now.isoformat()))
        self.conn.commit()

    def append_to_story(self, story_id, *, vec, member_id, entities, now) -> None:
        row = self.conn.execute(
            "SELECT centroid_sum,count,member_ids,entities FROM stories WHERE id=?",
            (story_id,)).fetchone()
        csum = add_vectors(json.loads(row["centroid_sum"]), list(vec))
        members = json.loads(row["member_ids"]) + [member_id]
        ents = list(dict.fromkeys(json.loads(row["entities"]) + list(entities)))
        self.conn.execute(
            "UPDATE stories SET centroid_sum=?, count=?, member_ids=?, entities=?, last_seen=? WHERE id=?",
            (json.dumps(csum), row["count"] + 1, json.dumps(members), json.dumps(ents),
             now.isoformat(), story_id))
        self.conn.commit()

    def get_open_stories(self, cutoff) -> list[dict]:
        out = []
        for r in self.conn.execute(
                "SELECT id,centroid_sum,count,last_seen FROM stories WHERE status='open'"):
            ls = datetime.fromisoformat(r["last_seen"])
            if ls.tzinfo is None:
                ls = ls.replace(tzinfo=timezone.utc)
            if ls >= cutoff:
                csum = json.loads(r["centroid_sum"])
                c = r["count"]
                out.append({"id": r["id"], "centroid": [x / c for x in csum]})
        return out

    def close_stale_stories(self, cutoff) -> int:
        n = 0
        for r in self.conn.execute("SELECT id,last_seen FROM stories WHERE status='open'"):
            ls = datetime.fromisoformat(r["last_seen"])
            if ls.tzinfo is None:
                ls = ls.replace(tzinfo=timezone.utc)
            if ls < cutoff:
                self.conn.execute("UPDATE stories SET status='closed' WHERE id=?", (r["id"],))
                n += 1
        self.conn.commit()
        return n

    def close(self) -> None:
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        self.close()
