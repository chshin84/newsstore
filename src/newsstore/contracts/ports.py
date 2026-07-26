from __future__ import annotations
from datetime import datetime
from typing import Protocol, TypedDict
from .models import RawItem


# ── Store 반환 shape 계약(EXPLICIT) — 산문 docstring 대신 타입으로 박는다 ──────────
# (from __future__ annotations로 런타임 평가 안 함 — 순수 문서/타입체크용.)

class FeedState(TypedDict, total=False):
    """get_feed_state 반환: 비었거나 폴링 캐시 필드 + 피드 건강 필드.
    이 클래스가 feed_state 문서의 필드 집합 SSOT다 — store의 `_STATE_FIELDS`가 여기서
    도출되므로, 필드를 더하거나 빼려면 이 선언 한 곳만 고치면 된다."""
    etag: str
    last_modified: str
    last_fetched: datetime
    # 피드 건강 — 수집 성공 시 리셋하고(collector `_mark_ok`) 실패 시 누적한다(`_mark_fail`).
    # entrypoints/_health.py가 consecutive_failures로 '만성 죽음'을 가려 시스템 장애 판정에서 뺀다.
    last_success: datetime
    consecutive_failures: int
    last_error: str | None          # 성공 시 None으로 리셋한다(값 없음이 아니라 명시적 None)
    last_error_at: datetime | None


class PendingItem(TypedDict):
    """get_pending_embed_items 반환 — 임베딩 입력(title·body)과 TTL 미러링(expire_at).
    키는 기존 관례 `id`가 아니라 `item_id`다 — item_vectors가 items를 참조하는 외래 키
    성격이라 명시적으로 구분하며, 문서 경로 item_vectors/{item_id}와 정합한다."""
    item_id: str
    title: str
    body: str
    expire_at: datetime


class VectorEntry(TypedDict):
    """save_vectors 입력 — 호출자는 이 셋만 제공, embed_model·embed_task_type·embedded_at은
    store가 주입한다(계약 상수의 SSOT는 contracts/embedding)."""
    item_id: str
    vector: list[float]
    expire_at: datetime


class JobHealth(TypedDict, total=False):
    """get_job_health 반환 — 잡별 최근 실행 상태다(비어 있으면 '한 번도 안 돎').
    대시보드(web/dashboard.html)가 판정에 실제로 쓰는 것은 last_status·fetched_at·detail 셋이다."""
    job: str
    last_status: str                # "ok" | "running" | "fail"
    fetched_at: datetime
    last_run_at: datetime
    last_finished_at: datetime
    last_success_at: datetime
    detail: str


class Store(Protocol):
    def upsert_items(self, items: list[RawItem]) -> int:
        """Insert items, skipping ids already present. Returns count of NEW items."""
        ...
    def upsert_items_batched(self, items: list[RawItem]) -> int:
        """청크 배치로 존재검사한 뒤 신규만 커밋한다(배치 내 중복 url은 1건으로 접는다).
        네이버·FMP 경로가 이걸 쓴다 — per-item get 대신 read를 라운드트립 수로 줄인다.
        반환=새로 쓴 수."""
        ...
    def get_feed_state(self, feed_id: str) -> FeedState:
        """비었거나 FeedState의 필드들을 담은 dict를 반환한다(shape은 FeedState가 SSOT)."""
        ...
    def set_feed_state(self, feed_id: str, **fields) -> None: ...
    def count(self) -> int: ...

    def filter_new_ids(self, ids: list[str]) -> list[str]:
        """`items`에 아직 없는 id만(입력 순서 보존)."""
        ...

    def set_meta(self, key: str, value: dict) -> None:
        """Write a small public-read metadata doc for the site (e.g. 'sources')."""
        ...

    # 잡 헬스 계약 — entrypoints/_health.py의 job_health 컨텍스트가 매 실행 상태를 남긴다.
    def get_job_health(self, job: str) -> JobHealth:
        """job_health/{job} 문서를 읽는다 — 문서가 없으면 {}를 돌려준다."""
        ...
    def set_job_health(self, job: str, **fields) -> None:
        """job_health/{job}를 부분 갱신한다(read-modify-write이므로 준 필드만 덮어쓴다).
        문서 키와 같은 `job` 필드는 store가 채운다."""
        ...

    # 임베딩 계약(spec 2026-07-16) — item_vectors 컬렉션 + items.embed_pending 플래그.
    def get_pending_embed_items(self, limit: int) -> list[PendingItem]:
        """items where embed_pending==true 를 limit까지(대기 큐 조회)."""
        ...
    def save_vectors(self, entries: list[VectorEntry]) -> int:
        """item_vectors set + 원본 embed_pending 해제(같은 batch). embed_model·embed_task_type·
        embedded_at은 store가 주입(단일 통제점). 원본이 TTL로 사라진 항목은 건너뛴다(격리). 반환=쓴 수."""
        ...
    def clear_embed_pending(self, ids: list[str]) -> None:
        """재시도 무의미(영구 실패) 기사의 플래그 처분 — 벡터 없이 플래그만 제거."""
        ...
