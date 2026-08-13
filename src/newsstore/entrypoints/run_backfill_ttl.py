"""일회성 백필: 이미 저장된 문서의 `expire_at`을 현행 TTL 계약으로 다시 계산한다.

`firestore_store._TTL`을 바꾸면 그 뒤에 쓰이는 문서만 새 기간을 받는다. 이미 Firestore에
있는 문서는 옛 `expire_at`을 그대로 들고 있다가 옛 기간에 사라진다. 이 스크립트가 그
간극을 메운다 — 보존 기간을 늘리든 줄이든 기존분을 현행 계약으로 끌어온다.

**더하지 않고 다시 계산한다.** `expire_at += 305일` 같은 증분은 멱등하지 않아서, 두 번
돌리면 610일이 더해지고 중간에 끊겨 재실행하면 일부만 두 번 더해져 값이 뒤섞인다.
`fetched_at + _TTL`로 다시 계산하면 몇 번을 돌려도 결과가 같고, 신규 수집분과 정확히
같은 계약이 된다. 그래서 이 스크립트는 재실행이 안전하다.

`items`와 `item_vectors`를 **한 배치에서 함께** 고친다 — 벡터는 원본의 `expire_at`을
미러링하는 계약이라(`docs/firestore-contract.md`), 한쪽만 늘리면 벡터가 먼저 사라져
계약이 깨진다. 배치가 원자적이므로 '항목은 맞고 벡터는 틀린' 중간 상태가 남지 않는다.
그래서 이미 맞는 항목은 건너뛰어도 안전하다(재실행이 싸다).

원본이 이미 만료돼 사라진 고아 벡터는 방문하지 않는다 — 원본이 없으면 함께 사라지는
것이 계약이라 옛 기간에 만료되는 편이 맞다.

로컬(Docker)에서 실행한다: Cloud Run task-timeout 제약이 없다.
  MSYS_NO_PATHCONV=1 docker compose run --rm collect \
    python -m newsstore.entrypoints.run_backfill_ttl
쓰기 없이 규모만 재려면 `--dry-run`을 붙인다.
"""
from __future__ import annotations
import argparse
import logging
import os
from datetime import datetime

# 기간은 store가 SSOT다 — 여기서 다시 적으면 두 곳이 반드시 어긋난다.
from ..store.firestore_store import _TTL, _ITEMS, _VECTORS
from ..store.factory import make_store

log = logging.getLogger("newsstore.backfill_ttl")

# 페이지당 items 수. 배치 op는 항목 1 + 벡터 1이라 최대 400으로 Firestore 500 한도 아래.
_PAGE = 200


def _new_stats() -> dict:
    return {"scanned": 0, "items_updated": 0, "vectors_updated": 0,
            "already_ok": 0, "no_fetched_at": 0, "oldest_fetched_at": None}


def backfill_ttl(store, *, page: int = _PAGE, dry_run: bool = False) -> dict:
    """전 `items`를 문서 이름 순으로 페이징하며 `expire_at`을 `fetched_at + _TTL`로 맞춘다.

    stream()을 통째로 걸지 않고 페이징하는 이유는 규모다 — 십만 건대 단일 스트림은 오래
    열려 있다가 끊길 수 있고, 끊기면 어디까지 했는지 알 수 없다. 페이지마다 커서를 새로
    잡으면 각 쿼리가 짧고, 중간에 죽어도 재실행이 이미 맞은 항목을 건너뛰며 따라잡는다.
    """
    db = store.db
    items = db.collection(_ITEMS)
    vectors = db.collection(_VECTORS)
    stats = _new_stats()
    cursor = None

    while True:
        q = items.order_by("__name__").select(["fetched_at", "expire_at"]).limit(page)
        if cursor is not None:
            q = q.start_after(cursor)
        snaps = list(q.stream())
        if not snaps:
            break
        cursor = snaps[-1]
        stats["scanned"] += len(snaps)

        targets: list[tuple[str, datetime]] = []
        for s in snaps:
            d = s.to_dict() or {}
            fetched = d.get("fetched_at")
            if fetched is None:
                # 계약상 모든 item에 있어야 한다 — 없으면 만료 시각을 도출할 수 없으니
                # 조용히 넘기지 말고 세어서 끝에 드러낸다.
                stats["no_fetched_at"] += 1
                continue
            if stats["oldest_fetched_at"] is None or fetched < stats["oldest_fetched_at"]:
                stats["oldest_fetched_at"] = fetched
            new_expire = fetched + _TTL
            if d.get("expire_at") == new_expire:
                stats["already_ok"] += 1
                continue
            targets.append((s.id, new_expire))

        if targets:
            # batch.update는 없는 문서를 만나면 배치 전체를 실패시킨다 — 벡터는 story에만
            # 있으므로 존재하는 것만 골라 넣는다. 투영으로 768차원 본문 전송을 피한다.
            refs = [vectors.document(i) for i, _ in targets]
            have = {r.id for r in db.get_all(refs, field_paths=["expire_at"]) if r.exists}
            stats["items_updated"] += len(targets)
            stats["vectors_updated"] += sum(1 for i, _ in targets if i in have)
            if not dry_run:
                batch = db.batch()
                for item_id, new_expire in targets:
                    batch.update(items.document(item_id), {"expire_at": new_expire})
                    if item_id in have:
                        batch.update(vectors.document(item_id), {"expire_at": new_expire})
                batch.commit()

        log.info("page done: scanned=%d items_updated=%d vectors_updated=%d already_ok=%d",
                 stats["scanned"], stats["items_updated"], stats["vectors_updated"],
                 stats["already_ok"])
        if len(snaps) < page:
            break

    return stats


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="expire_at을 현행 TTL 계약으로 재계산 (일회성·멱등)")
    ap.add_argument("--page", type=int, default=_PAGE, help="페이지당 items 수")
    ap.add_argument("--dry-run", action="store_true",
                    help="쓰기 없이 규모만 잰다(무엇을 몇 건 고칠지 보고)")
    args = ap.parse_args(argv)
    logging.basicConfig(level=os.environ.get("NEWSSTORE_LOG_LEVEL", "INFO"),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    log.info("TTL 계약 = %d일%s", _TTL.days, " (DRY RUN — 쓰지 않는다)" if args.dry_run else "")
    with make_store() as store:
        stats = backfill_ttl(store, page=args.page, dry_run=args.dry_run)

    log.info("backfill_ttl 완료: scanned=%d items_updated=%d vectors_updated=%d "
             "already_ok=%d no_fetched_at=%d oldest_fetched_at=%s",
             stats["scanned"], stats["items_updated"], stats["vectors_updated"],
             stats["already_ok"], stats["no_fetched_at"], stats["oldest_fetched_at"])
    if stats["no_fetched_at"]:
        # 계약 위반은 성공으로 끝내지 않는다 — 남은 문서는 만료 시각을 도출할 수 없다.
        log.error("fetched_at이 없는 문서 %d건은 건너뛰었다 — expire_at을 도출할 수 없다",
                  stats["no_fetched_at"])
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
