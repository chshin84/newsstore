from __future__ import annotations
from datetime import datetime, timezone, timedelta
from ..contracts.models import RawItem
from ..contracts.classify import classify_kind   # 순수 triage(키워드 매칭) — contracts 공유
from ..contracts.embedding import EMBED_MODEL

_ITEMS = "items"
_FEED_STATE = "feed_state"
_BARS = "price_bars"
_VECTORS = "item_vectors"

# content 데이터의 보존 기간(60일). Firestore TTL 정책이 각 문서의 expire_at을
# 가리켜 만료시킨다(비용 통제). feed_state에는 절대 넣지 않는다 — 증분 수집 커서가
# 유실되면 재수집이 어긋난다.
_TTL = timedelta(days=60)


def _bar_expire_at(dt_str) -> datetime:
    """price_bars TTL — 바 날짜(datetime 필드) + 30일. 시·분은 만료에 무의미(코스 30일)라
    날짜 부분만 파싱한다. 파싱 불가면 수집 시각 기준으로 폴백(조용히 안 지워지게)."""
    if isinstance(dt_str, str) and len(dt_str) >= 10:
        try:
            d = datetime.strptime(dt_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return d + _TTL
        except ValueError:
            pass
    return datetime.now(timezone.utc) + _TTL


def _to_doc(item: RawItem) -> dict:
    # 수집 시점 kind triage: 신선 항목도 즉시 spam/digest/sports로 숨김 가능(', More' 등).
    # 백엔드가 kind의 단일 통제점 — 규칙 필터(비-LLM)라 수집 경로에서 한 번만 박는다.
    kind = classify_kind(item.title, item.body)
    doc = {
        "feed_id": item.feed_id, "source": item.source,
        "asset_hint": item.asset_hint, "language": item.language,
        "url": item.url, "title": item.title, "body": item.body,
        "symbol": item.symbol,
        "published_at": item.published_at, "fetched_at": item.fetched_at,
        "kind": kind,
        # TTL: 수집 시각 기준 30일 뒤 만료. 원본은 이때까지 보존된다.
        "expire_at": item.fetched_at + _TTL,
    }
    if kind == "story":
        # 임베딩 대기 플래그 — Firestore는 '필드 없음'을 쿼리할 수 없어 플래그의 존재
        # 자체가 '대상이며 미완'을 뜻한다. 임베딩 패스가 완료 시 DELETE_FIELD로 걷는다.
        doc["embed_pending"] = True
    return doc


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

    # ── 팩터·펀더멘털 계약(다운스트림 seam) — 제네릭 컬렉션 적재 ──
    # 계약의 14개 컬렉션은 구조가 같다(심볼별 날짜 문서 / 현재값 스냅샷)이라 컬렉션명을
    # 받는 제네릭 메서드로 통일한다. TTL은 컨베이어 모델대로 수집 시각 + 30일(백필 행도
    # 지금 수집하면 30일 산다). 계약 SSOT: docs/firestore-contract.md.

    def save_docs(self, collection: str, docs: list[dict]) -> int:
        """collection에 문서 배치 set(각 doc는 'id' 보유). 반환=쓴 수.
        TTL expire_at = 수집 시각 + 30일(store 단일 통제점). set이라 멱등(같은 id 덮어씀)."""
        if not docs:
            return 0
        exp = datetime.now(timezone.utc) + _TTL
        col = self.db.collection(collection)
        n = 0
        for i in range(0, len(docs), 500):           # Firestore batch ≤500 op
            batch = self.db.batch()
            for d in docs[i:i + 500]:
                doc = {k: v for k, v in d.items() if k != "id"}
                doc["expire_at"] = exp
                batch.set(col.document(d["id"]), doc)
                n += 1
            batch.commit()
        return n

    def filter_new_ids_in(self, collection: str, ids: list[str]) -> list[str]:
        """collection에 아직 없는 id만(입력 순서 보존) — 백필 히스토리에서 새 행만 write."""
        if not ids:
            return []
        col = self.db.collection(collection)
        refs = [col.document(i) for i in ids]
        existing = {s.id for s in self.db.get_all(refs) if s.exists}
        return [i for i in ids if i not in existing]

    def save_snapshot(self, collection: str, doc_id: str, data: dict) -> None:
        """현재값 스냅샷 한 문서 덮어쓰기(profiles·index_members·index_changes). TTL 주입."""
        doc = dict(data)
        doc["expire_at"] = datetime.now(timezone.utc) + _TTL
        self.db.collection(collection).document(doc_id).set(doc)

    def get_snapshot(self, collection: str, doc_id: str) -> dict:
        snap = self.db.collection(collection).document(doc_id).get()
        return (snap.to_dict() or {}) if snap.exists else {}

    def get_docs(self, collection: str, *, field: str | None = None, value=None) -> list[dict]:
        """collection 문서 조회(field 지정 시 where 필터, 아니면 전체). 소비자·테스트용."""
        col = self.db.collection(collection)
        stream = col.where(field, "==", value).stream() if field is not None else col.stream()
        return [s.to_dict() or {} for s in stream]

    def filter_new_bar_ids(self, ids: list[str]) -> list[str]:
        """price_bars에 아직 없는 바 id만(입력 순서 보존) — 새 바만 write해 5분 주기 write 비용을
        묶는다(뉴스 filter_new_ids와 동일 패턴)."""
        if not ids:
            return []
        col = self.db.collection(_BARS)
        refs = [col.document(i) for i in ids]
        existing = {s.id for s in self.db.get_all(refs) if s.exists}
        return [i for i in ids if i not in existing]

    def save_bars(self, bars: list[dict]) -> int:
        """price_bars/{id} 배치 적재(바 1개=문서 1개, 완전 스트림). 반환=쓴 수.
        각 bar는 'id'와 'datetime'을 가진다. TTL expire_at은 바 날짜에서 store가 주입(단일 통제점).
        호출자가 새 바만(filter_new_bar_ids) 넘기지만 set은 멱등이라 재적재도 안전."""
        if not bars:
            return 0
        col = self.db.collection(_BARS)
        n = 0
        for i in range(0, len(bars), 500):           # Firestore batch ≤500 op
            batch = self.db.batch()
            for b in bars[i:i + 500]:
                doc = {k: v for k, v in b.items() if k != "id"}
                doc["expire_at"] = _bar_expire_at(b.get("datetime"))
                batch.set(col.document(b["id"]), doc)
                n += 1
            batch.commit()
        return n

    def get_bars(self, key: str) -> list[dict]:
        """price_bars에서 한 심볼(key)의 바를 datetime 오름차순으로. 소비자·테스트용."""
        out = []
        for snap in self.db.collection(_BARS).where("key", "==", key).stream():
            out.append(snap.to_dict() or {})
        out.sort(key=lambda d: d.get("datetime") or "")
        return out

    # ── 임베딩 계약(spec 2026-07-16) — item_vectors + embed_pending 대기 큐 ──────

    def get_pending_embed_items(self, limit: int) -> list[dict]:
        """items where embed_pending==true 를 limit까지(단일 equality — 복합 인덱스 불필요)."""
        q = self.db.collection(_ITEMS).where("embed_pending", "==", True).limit(limit)
        out = []
        for snap in q.stream():
            d = snap.to_dict() or {}
            out.append({"item_id": snap.id, "title": d.get("title") or "",
                        "body": d.get("body") or "", "expire_at": d.get("expire_at")})
        return out

    def save_vectors(self, entries: list[dict]) -> int:
        """item_vectors/{item_id} set + 원본 embed_pending 해제를 청크 batch(250건×2op)로
        커밋 — 벡터 저장과 플래그 해제가 원자적이라 부분 상태가 없다. 원본이 TTL로
        사라져 batch가 롤백되면 그 청크만 항목 단위로 재커밋해 부재 항목만 건너뛴다
        (만료 경합 격리 — 벡터 고아 방지). embed_model·embedded_at은 store가 주입
        (단일 통제점, 계약 SSOT: contracts/embedding)."""
        if not entries:
            return 0
        from google.api_core.exceptions import FailedPrecondition, NotFound   # lazy(클라이언트 주입 유지)
        from google.cloud.firestore import DELETE_FIELD

        vec_col = self.db.collection(_VECTORS)
        items_col = self.db.collection(_ITEMS)
        now = datetime.now(timezone.utc)
        _MISSING = (NotFound, FailedPrecondition)   # update-of-missing 표면화 타입(에뮬레이터/실서버 편차 흡수)

        def _ops(batch, e):
            batch.set(vec_col.document(e["item_id"]), {
                "vector": e["vector"], "embed_model": EMBED_MODEL,
                "embedded_at": now, "expire_at": e["expire_at"]})
            batch.update(items_col.document(e["item_id"]),
                         {"embed_pending": DELETE_FIELD})

        n = 0
        for i in range(0, len(entries), 50):         # 768차원 벡터는 커서 250건이면 Firestore 커밋 10MiB 초과("Transaction too big") — 50건으로 축소
            chunk = entries[i:i + 250]
            batch = self.db.batch()
            for e in chunk:
                _ops(batch, e)
            try:
                batch.commit()
                n += len(chunk)
            except _MISSING:
                # 만료 경합: batch는 원자적이라 전체 롤백됨 — 이 청크만 항목 단위로
                # 재커밋해 부재 항목만 건너뛴다(한 건이 나머지 249건을 못 날리게).
                for e in chunk:
                    b2 = self.db.batch()
                    _ops(b2, e)
                    try:
                        b2.commit()
                        n += 1
                    except _MISSING:
                        continue     # 원본 만료 — 이 항목만 스킵(벡터 고아 방지)
        return n

    def clear_embed_pending(self, ids: list[str]) -> None:
        """영구 실패 처분 — 벡터 없이 플래그만 걷는다(좀비 재시도 차단). 없는 id는 스킵."""
        from google.api_core.exceptions import FailedPrecondition, NotFound
        from google.cloud.firestore import DELETE_FIELD
        col = self.db.collection(_ITEMS)
        for i in ids:
            try:
                col.document(i).update({"embed_pending": DELETE_FIELD})
            except (NotFound, FailedPrecondition):   # update-of-missing 편차 흡수 — save_vectors와 통일
                continue

    # feed_state 지속 필드: 증분 수집 커서(etag·last_modified·last_fetched) + 피드 건강
    # (last_success·consecutive_failures·last_error·last_error_at). 건강은 대시보드 표시와
    # 실패 판정(만성 죽음 식별)에 쓴다 — 같은 문서라 쓰기 횟수는 안 늘어난다.
    _STATE_FIELDS = ("etag", "last_modified", "last_fetched",
                     "last_success", "consecutive_failures", "last_error", "last_error_at")

    def get_feed_state(self, feed_id: str) -> dict:
        snap = self.db.collection(_FEED_STATE).document(feed_id).get()
        if not snap.exists:
            return {}
        d = snap.to_dict() or {}
        return {k: d.get(k) for k in self._STATE_FIELDS}

    def set_feed_state(self, feed_id: str, **fields) -> None:
        cur = self.get_feed_state(feed_id)        # read-modify-write (no merge=)
        cur.update(fields)
        # feed_state에는 expire_at을 넣지 않는다(ETag·커서 유실 시 증분 수집 어긋남).
        self.db.collection(_FEED_STATE).document(feed_id).set(
            {k: cur.get(k) for k in self._STATE_FIELDS})

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
