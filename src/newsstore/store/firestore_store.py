from __future__ import annotations
from datetime import datetime, timezone
from ..contracts.models import RawItem
from ..contracts.vectors import add_vectors

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
        csum = add_vectors(list(d.get("centroid_sum", [])), list(vec))
        members = list(d.get("member_ids", [])) + [member_id]
        ents = list(dict.fromkeys(list(d.get("entities", [])) + list(entities)))
        # 필드 한정 merge(풀-doc set 아님): 요약 패스가 쓴 summary 필드를 read↔set 레이스로
        # 되돌리지 않게(플랜 A D7). 자기 소유 cluster 필드만 갱신.
        ref.set({"centroid_sum": csum, "count": d.get("count", 0) + 1,
                 "member_ids": members, "entities": ents, "last_seen": now}, merge=True)

    def get_open_stories(self, cutoff) -> list[dict]:
        out = []
        for snap in self.db.collection("stories").where("status", "==", "open").stream():
            d = snap.to_dict() or {}
            if d.get("last_seen") and d["last_seen"] >= cutoff:
                c = d.get("count", 1) or 1
                out.append({"id": snap.id, "centroid": [x / c for x in d.get("centroid_sum", [])],
                            "count": c})
        return out

    def close_stale_stories(self, cutoff) -> int:
        n = 0
        col = self.db.collection("stories")
        for snap in col.where("status", "==", "open").stream():
            d = snap.to_dict() or {}
            if d.get("last_seen") and d["last_seen"] < cutoff:
                col.document(snap.id).set({"status": "closed"}, merge=True)
                n += 1
        return n

    # --- Step-3 요약 패스 (플랜 A) ---
    def get_stories_needing_summary(self, limit: int) -> list[dict]:
        # last_seen desc 상위 limit개 스캔 → 코드측에서 count>summary_count만(부등호+정렬
        # 한 쿼리 불가). 새 멤버가 붙으면 last_seen이 갱신돼 상위로 떠오르므로 스캔창=대상창.
        out = []
        q = (self.db.collection("stories")
             .order_by("last_seen", direction="DESCENDING")
             .limit(int(limit)))
        for snap in q.stream():
            d = snap.to_dict() or {}
            if d.get("count", 0) > d.get("summary_count", 0):
                out.append({"id": snap.id, "count": d.get("count", 0)})
        return out

    def get_story_members(self, story_id: str) -> list[dict]:
        # items(story_id, published_at) 복합 인덱스 사용(READY). published_at 없는 멤버는
        # order_by가 정렬값으로 포함하되, grounding은 summarizer가 None 가드로 드롭.
        q = (self.db.collection(_ITEMS)
             .where("story_id", "==", story_id)
             .order_by("published_at"))
        out = []
        for s in q.stream():
            d = s.to_dict() or {}
            out.append({"title": d.get("title", ""), "body": d.get("body") or "",
                        "source": d.get("source", ""), "published_at": d.get("published_at")})
        return out

    def save_story_summary(self, story_id, *, title, summary, latest, developments,
                           summary_count, now) -> None:
        # merge=True: 요약 필드만 갱신, member_ids/centroid_sum/count 등 cluster 소유 필드 보존.
        self.db.collection("stories").document(story_id).set({
            "title": title, "summary": summary, "latest": latest,
            "developments": list(developments), "summary_count": int(summary_count),
            "summary_at": now,
        }, merge=True)

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
        """processed 플래그를 merge-batch로 기록(읽기 없음). 반환 = 쓴 수.
        Firestore batch는 ≤500 op이라 청크. (구버전의 '변경된 수' 멱등 카운트 의미는 폐기)"""
        if not ids:
            return 0
        ts = processed_at or datetime.now(timezone.utc)
        col = self.db.collection(_ITEMS)
        n = 0
        for i in range(0, len(ids), 500):
            batch = self.db.batch()
            for _id in ids[i:i + 500]:
                batch.set(col.document(_id),
                          {"processed": True, "processed_at": ts}, merge=True)
                n += 1
            batch.commit()
        return n

    def save_enrichment(self, item_id, *, kind, tags, embedding, story_id) -> None:
        # merge=True: 읽기 없이 enrich 필드만 갱신(기존 필드 보존). 왕복 절감.
        self.db.collection(_ITEMS).document(item_id).set({
            "kind": kind, "tags": list(tags),
            "embedding": list(embedding) if embedding is not None else None,
            "story_id": story_id,
        }, merge=True)

    def filter_new_ids(self, ids: list[str]) -> list[str]:
        if not ids:
            return []
        col = self.db.collection(_ITEMS)
        refs = [col.document(i) for i in ids]
        existing = {s.id for s in self.db.get_all(refs) if s.exists}
        return [i for i in ids if i not in existing]

    def close(self) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        self.close()
