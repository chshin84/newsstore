from __future__ import annotations
from datetime import datetime, timezone
from ..models import RawItem

_ITEMS = "items"
_FEED_STATE = "feed_state"


def _to_doc(item: RawItem) -> dict:
    return {
        "feed_id": item.feed_id, "source": item.source,
        "asset_hint": item.asset_hint, "language": item.language,
        "url": item.url, "title": item.title, "body": item.body,
        "published_at": item.published_at, "fetched_at": item.fetched_at,
        "processed": False, "processed_at": None, "tags": [],
    }


def _from_doc(doc_id: str, d: dict) -> RawItem:
    return RawItem(
        id=doc_id, feed_id=d.get("feed_id", ""), source=d.get("source", ""),
        asset_hint=d.get("asset_hint") or "", language=d.get("language") or "en",
        url=d.get("url", ""), title=d.get("title", ""), body=d.get("body") or "",
        published_at=d.get("published_at"), fetched_at=d.get("fetched_at"),
    )


class FirestoreStore:
    """Store Protocol over Firestore. Client is injected (real Client in prod,
    MockFirestore in tests) so the class has no hard google dependency."""

    def __init__(self, client):
        self.db = client

    def upsert_items(self, items: list[RawItem]) -> int:
        new = 0
        col = self.db.collection(_ITEMS)
        for it in items:
            ref = col.document(it.id)
            if ref.get().exists:          # already stored -> never overwrite
                continue
            ref.set(_to_doc(it))
            new += 1
        return new

    def count(self) -> int:
        return sum(1 for _ in self.db.collection(_ITEMS).stream())

    def set_meta(self, key: str, value: dict) -> None:
        self.db.collection("meta").document(key).set(value)

    def create_story(self, story_id, *, title, vec, member_id, entities, now) -> None:
        self.db.collection("stories").document(story_id).set({
            "title": title, "centroid_sum": list(vec), "count": 1,
            "member_ids": [member_id], "entities": list(entities),
            "first_seen": now, "last_seen": now, "status": "open",
        })

    def append_to_story(self, story_id, *, vec, member_id, entities, now) -> None:
        ref = self.db.collection("stories").document(story_id)
        d = ref.get().to_dict() or {}
        csum = [a + b for a, b in zip(d.get("centroid_sum", []), vec)]
        members = list(d.get("member_ids", [])) + [member_id]
        ents = list(dict.fromkeys(list(d.get("entities", [])) + list(entities)))
        d.update({"centroid_sum": csum, "count": d.get("count", 0) + 1,
                  "member_ids": members, "entities": ents, "last_seen": now})
        ref.set(d)

    def get_open_stories(self, cutoff) -> list[dict]:
        out = []
        for snap in self.db.collection("stories").where("status", "==", "open").stream():
            d = snap.to_dict() or {}
            if d.get("last_seen") and d["last_seen"] >= cutoff:
                c = d.get("count", 1) or 1
                out.append({"id": snap.id, "centroid": [x / c for x in d.get("centroid_sum", [])]})
        return out

    def close_stale_stories(self, cutoff) -> int:
        n = 0
        col = self.db.collection("stories")
        for snap in col.where("status", "==", "open").stream():
            d = snap.to_dict() or {}
            if d.get("last_seen") and d["last_seen"] < cutoff:
                d["status"] = "closed"
                col.document(snap.id).set(d)
                n += 1
        return n

    def get_feed_state(self, feed_id: str) -> dict:
        snap = self.db.collection(_FEED_STATE).document(feed_id).get()
        if not snap.exists:
            return {}
        d = snap.to_dict() or {}
        return {"etag": d.get("etag"), "last_modified": d.get("last_modified"),
                "last_fetched": d.get("last_fetched")}

    def set_feed_state(self, feed_id: str, **fields) -> None:
        cur = self.get_feed_state(feed_id)        # read-modify-write (no merge=)
        cur.update(fields)
        self.db.collection(_FEED_STATE).document(feed_id).set({
            "etag": cur.get("etag"),
            "last_modified": cur.get("last_modified"),
            "last_fetched": cur.get("last_fetched"),
        })

    def get_unprocessed(self, limit: int | None = None) -> list[RawItem]:
        # processed==False + order_by(fetched_at) needs a composite index in
        # real Firestore (created in the deploy plan); MockFirestore needs none.
        q = (self.db.collection(_ITEMS)
             .where("processed", "==", False)
             .order_by("fetched_at"))
        if limit is not None:
            q = q.limit(int(limit))
        return [_from_doc(s.id, s.to_dict() or {}) for s in q.stream()]

    def mark_processed(self, ids: list[str], processed_at: datetime | None = None) -> int:
        if not ids:
            return 0
        ts = processed_at or datetime.now(timezone.utc)
        changed = 0
        col = self.db.collection(_ITEMS)
        # TODO: batch the reads with self.db.get_all([...]) once off MockFirestore (real client only)
        for _id in ids:
            ref = col.document(_id)
            snap = ref.get()
            if snap.exists:
                d = snap.to_dict()
                if d.get("processed") is False:
                    d["processed"] = True
                    d["processed_at"] = ts
                    ref.set(d)              # full-doc write, no merge=
                    changed += 1
        return changed

    def save_enrichment(self, item_id, *, kind, tags, embedding, story_id) -> None:
        ref = self.db.collection(_ITEMS).document(item_id)
        d = ref.get().to_dict() or {}
        d.update({"kind": kind, "tags": list(tags),
                  "embedding": list(embedding) if embedding is not None else None,
                  "story_id": story_id})
        ref.set(d)

    def close(self) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        self.close()
