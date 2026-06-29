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
        prior = list(d.get("member_ids", []))
        if member_id in prior:
            return  # 멱등: 같은 멤버 재처리(재시도·비원자 save+mark)는 count·centroid 이중 반영 금지.
        csum = add_vectors(list(d.get("centroid_sum", [])), list(vec))
        members = prior + [member_id]
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
                csum = list(d.get("centroid_sum", []))
                c = d.get("count", 1) or 1
                out.append({"id": snap.id, "title": d.get("title") or "",
                            "centroid_sum": csum,                  # 원본 합(클러스터러 어댑터용)
                            "centroid": [x / c for x in csum],     # 평균(기존 호출자 보존)
                            "count": c})
        return out

    def close_stale_stories(self, cutoff) -> int:
        col = self.db.collection("stories")
        stale = []
        for snap in col.where("status", "==", "open").stream():
            d = snap.to_dict() or {}
            if d.get("last_seen") and d["last_seen"] < cutoff:
                stale.append(snap.id)
        # N+1 set 대신 merge-batch(≤500 op/batch, mark_processed와 동일 컨벤션).
        for i in range(0, len(stale), 500):
            batch = self.db.batch()
            for sid in stale[i:i + 500]:
                batch.set(col.document(sid), {"status": "closed"}, merge=True)
            batch.commit()
        return len(stale)

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
                out.append({"id": snap.id, "count": d.get("count", 0),
                            "developments": d.get("developments", [])})  # prior(델타) 동봉
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

    def save_story_lenses(self, story_id, lenses: list, count: int | None = None) -> None:
        doc = {"lenses": list(lenses)}
        if count is not None:
            doc["lensed_count"] = count        # incremental: 이 멤버수까지 분류함
        self.db.collection("stories").document(story_id).set(doc, merge=True)

    def get_stories_for_lensing(self, cutoff) -> list[dict]:
        # incremental: 새 멤버가 생긴(count > lensed_count) 또는 미분류 스토리만. 48h창은 cutoff.
        out = []
        for snap in self.db.collection("stories").where("status", "==", "open").stream():
            d = snap.to_dict() or {}
            if not (d.get("last_seen") and d["last_seen"] >= cutoff):
                continue
            count = d.get("count", len(d.get("member_ids", [])))
            if count <= d.get("lensed_count", -1):      # 변화 없음 → 스킵
                continue
            out.append({"id": snap.id, "title": d.get("title", ""),
                        "member_ids": d.get("member_ids", []),
                        "count": count, "lenses": d.get("lenses", [])})
        return out

    # --- Phase 3 dual score 패스 ---
    def get_stories_for_scoring(self, cutoff) -> list[dict]:
        # incremental: 새 멤버가 생긴(count > scored_count) 또는 미채점 스토리만. 48h창은 cutoff.
        # get_stories_for_lensing 미러 + 게이트·입력 구성용 필드(lenses/summary/developments).
        out = []
        for snap in self.db.collection("stories").where("status", "==", "open").stream():
            d = snap.to_dict() or {}
            if not (d.get("last_seen") and d["last_seen"] >= cutoff):
                continue
            count = d.get("count", len(d.get("member_ids", [])))
            if count <= d.get("scored_count", -1):      # 변화 없음 → 스킵(중복 채점 차단)
                continue
            out.append({"id": snap.id, "title": d.get("title", ""), "count": count,
                        "lenses": d.get("lenses", []), "summary": d.get("summary", ""),
                        "developments": d.get("developments", [])})
        return out

    def save_story_score(self, story_id, *, risk, impact, risk_reason, impact_reason,
                         count=None, now=None) -> None:
        # merge=True: 점수 필드만 갱신(read 없음, cross-field batch 없음) → summary/lenses/cluster
        # 필드 보존(비파괴 by construction). save_story_lenses/save_story_summary 미러.
        doc = {"risk": int(risk), "impact": int(impact),
               "risk_reason": risk_reason, "impact_reason": impact_reason}
        if count is not None:
            doc["scored_count"] = int(count)            # incremental: 이 멤버수까지 채점함
        if now is not None:
            doc["scored_at"] = now
        self.db.collection("stories").document(story_id).set(doc, merge=True)

    # --- Phase 4 article(보고서 생성) 패스 ---
    def get_stories_for_article(self, cutoff) -> list[dict]:
        # incremental: count>articled_count 또는 미생성. get_stories_for_scoring 미러 +
        # 생성/헤드라인/ref 갱신에 필요한 필드(developments·risk·impact·*_ref·first_seen).
        out = []
        for snap in self.db.collection("stories").where("status", "==", "open").stream():
            d = snap.to_dict() or {}
            if not (d.get("last_seen") and d["last_seen"] >= cutoff):
                continue
            count = d.get("count", len(d.get("member_ids", [])))
            if count <= d.get("articled_count", -1):
                continue
            out.append({"id": snap.id, "title": d.get("title", ""), "count": count,
                        "lenses": d.get("lenses", []), "summary": d.get("summary", ""),
                        "developments": d.get("developments", []),
                        "risk": d.get("risk"), "impact": d.get("impact"),
                        "risk_ref": d.get("risk_ref"), "impact_ref": d.get("impact_ref"),
                        "score_ref_at": d.get("score_ref_at"), "first_seen": d.get("first_seen")})
        return out

    def save_story_article(self, story_id, *, headline, lead, article,
                           risk_ref=None, impact_ref=None, score_ref_at=None,
                           count=None, now=None) -> None:
        # merge=True + 자기 필드만(read 없음, cross-field batch 없음, developments 미포함)
        # → summary/lenses/score/cluster/developments 보존(비파괴 by construction).
        doc = {"headline": headline, "lead": lead, "article": list(article)}
        if risk_ref is not None:
            doc["risk_ref"] = int(risk_ref)
        if impact_ref is not None:
            doc["impact_ref"] = int(impact_ref)
        if score_ref_at is not None:
            doc["score_ref_at"] = score_ref_at
        if count is not None:
            doc["articled_count"] = int(count)
        if now is not None:
            doc["articled_at"] = now
        self.db.collection("stories").document(story_id).set(doc, merge=True)

    def get_story_member_signals(self, member_ids: list) -> dict:
        """멤버 기사 분류 신호를 **배치(get_all)**로 집계(per-member 읽기 금지).
        반환 {asset_hints, languages, tags(flat), keyword_text}."""
        col = self.db.collection(_ITEMS)
        refs = [col.document(i) for i in member_ids]
        ahints, langs, tags, texts = set(), [], [], []
        for s in (self.db.get_all(refs) if member_ids else []):
            d = (s.to_dict() or {})
            for a in str(d.get("asset_hint") or "").split(","):
                if a.strip():
                    ahints.add(a.strip())
            if d.get("language"):
                langs.append(d["language"])
            texts.append(d.get("title", "") + " " + (d.get("body") or "")[:200])
            tags.extend(t for t in (d.get("tags") or []) if isinstance(t, str))
        texts.extend(tags)
        return {"asset_hints": list(ahints), "languages": langs,
                "tags": tags, "keyword_text": " ".join(texts)}

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
