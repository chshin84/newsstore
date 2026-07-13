from __future__ import annotations
from datetime import datetime, timezone, timedelta
from ..contracts.models import RawItem
from ..contracts.classify import classify_kind   # 순수 triage(키워드 매칭) — contracts 공유

_ITEMS = "items"
_FEED_STATE = "feed_state"

# content 데이터의 보존 기간(1개월). Firestore TTL 정책이 각 문서의 expire_at을
# 가리켜 만료시킨다(비용 통제). feed_state에는 절대 넣지 않는다 — 증분 수집 커서가
# 유실되면 재수집이 어긋난다.
_TTL = timedelta(days=30)


def _to_doc(item: RawItem) -> dict:
    return {
        "feed_id": item.feed_id, "source": item.source,
        "asset_hint": item.asset_hint, "language": item.language,
        "url": item.url, "title": item.title, "body": item.body,
        "published_at": item.published_at, "fetched_at": item.fetched_at,
        # 수집 시점 kind triage: 신선 항목도 즉시 spam/digest/sports로 숨김 가능(', More' 등).
        # 백엔드가 kind의 단일 통제점 — 규칙 필터(비-LLM)라 수집 경로에서 한 번만 박는다.
        "kind": classify_kind(item.title, item.body),
        # TTL: 수집 시각 기준 30일 뒤 만료. 원본은 이때까지 보존된다.
        "expire_at": item.fetched_at + _TTL,
    }


class FirestoreStore:
    """Store Protocol over Firestore. Client is injected (real Client in prod,
    emulator-backed Client in tests) so the class has no hard google dependency."""

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
        # 집계 쿼리(1000건당 1 read) — 전 문서 stream()은 문서수 비례 read 과금에
        # 본문까지 통째 전송한다(run_collect가 매 실행 호출 → 비용 단조 증가).
        result = self.db.collection(_ITEMS).count().get()
        return int(result[0][0].value)

    def set_meta(self, key: str, value: dict) -> None:
        self.db.collection("meta").document(key).set(value)

    def save_price(self, key: str, data: dict) -> None:
        """prices/{key} 최신 스냅샷 set(가격 앵커 — 뉴스 vs 가격 반응). 통째 덮어쓰기.
        TTL expire_at은 호출자가 안 넣어도 store가 보장(단일 통제점)."""
        doc = dict(data)
        doc["expire_at"] = datetime.now(timezone.utc) + _TTL
        self.db.collection("prices").document(key).set(doc)

    def get_price(self, key: str) -> dict:
        snap = self.db.collection("prices").document(key).get()
        return (snap.to_dict() or {}) if snap.exists else {}

    def save_fundamental(self, symbol: str, data: dict) -> None:
        """fundamentals/{symbol} 최신 스냅샷 set(income/balance/cashflow). 통째 덮어쓰기.
        TTL expire_at은 호출자가 안 넣어도 store가 보장(단일 통제점)."""
        doc = dict(data)
        doc["expire_at"] = datetime.now(timezone.utc) + _TTL
        self.db.collection("fundamentals").document(symbol).set(doc)

    def get_fundamental(self, symbol: str) -> dict:
        snap = self.db.collection("fundamentals").document(symbol).get()
        return (snap.to_dict() or {}) if snap.exists else {}

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
        # feed_state에는 expire_at을 넣지 않는다(ETag·커서 유실 시 증분 수집 어긋남).
        self.db.collection(_FEED_STATE).document(feed_id).set({
            "etag": cur.get("etag"),
            "last_modified": cur.get("last_modified"),
            "last_fetched": cur.get("last_fetched"),
        })

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
