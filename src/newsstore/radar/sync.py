"""Firestore → local.db 증분 동기화 (REST runQuery·공개 읽기·무인증).

- 워터마크 = fetched_at(수집기가 전 문서 필수 세팅 — published_at은 nullable이라 부적합).
- 커서: orderBy (fetched_at ASC, __name__ ASC) + startAt(before=false) — 동률 그룹 유실 없음.
- 페이지 단위 체크포인트: 워터마크는 '마지막 완결 페이지의 max(fetched_at)'까지만 전진
  (max는 문자열이 아니라 datetime 비교 — 소수부 생략 직렬화의 사전순 함정 회피).
- FAIL-LOUD: 초회 백필 0건 크래시, HTTP 상태 오류는 raise_for_status로 즉시 크래시.
"""
from __future__ import annotations

import datetime as dt
import os

import httpx

from . import localdb

OVERLAP = dt.timedelta(hours=24)


class SyncError(RuntimeError):
    pass


def _base_url() -> str:
    emu = os.environ.get("FIRESTORE_EMULATOR_HOST")
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "test")
    host = f"http://{emu}" if emu else "https://firestore.googleapis.com"
    return f"{host}/v1/projects/{project}/databases/(default)/documents"


def _ts_key(ts: str) -> dt.datetime:
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _decode(v: dict):
    if "stringValue" in v: return v["stringValue"]
    if "timestampValue" in v: return v["timestampValue"]
    if "integerValue" in v: return int(v["integerValue"])
    if "doubleValue" in v: return v["doubleValue"]
    if "booleanValue" in v: return v["booleanValue"]
    return None


def _to_row(doc: dict) -> dict:
    fields = doc.get("fields", {})
    row = {c: _decode(fields[c]) for c in localdb.ITEM_COLS[1:] if c in fields}
    row["id"] = doc["name"].rsplit("/", 1)[-1]
    return row


def _run_query_page(client: httpx.Client, after_ts: str | None,
                    cursor: tuple[str, str] | None, page_size: int) -> list[dict]:
    q: dict = {
        "from": [{"collectionId": "items"}],
        "orderBy": [{"field": {"fieldPath": "fetched_at"}, "direction": "ASCENDING"},
                    {"field": {"fieldPath": "__name__"}, "direction": "ASCENDING"}],
        "limit": page_size,
    }
    if after_ts:
        q["where"] = {"fieldFilter": {"field": {"fieldPath": "fetched_at"},
                                      "op": "GREATER_THAN",
                                      "value": {"timestampValue": after_ts}}}
    if cursor:
        q["startAt"] = {"values": [{"timestampValue": cursor[0]},
                                   {"referenceValue": cursor[1]}],
                        "before": False}
    r = client.post(f"{_base_url()}:runQuery", json={"structuredQuery": q}, timeout=30)
    r.raise_for_status()
    return [e["document"] for e in r.json() if "document" in e]


def run_sync(db, *, page_size: int = 300) -> int:
    wm = localdb.get_watermark(db)
    first_run = wm is None and localdb.count_items(db) == 0
    after = None
    if wm:
        after = (_ts_key(wm) - OVERLAP).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    total = 0
    cursor = None
    with httpx.Client() as client:
        while True:
            docs = _run_query_page(client, after, cursor, page_size)
            if not docs:
                break
            rows = [_to_row(d) for d in docs]
            localdb.upsert_items(db, rows)
            stamps = [r["fetched_at"] for r in rows if r.get("fetched_at")]
            if stamps:
                localdb.set_watermark(db, max(stamps, key=_ts_key))
            total += len(rows)
            cursor = (docs[-1]["fields"]["fetched_at"]["timestampValue"], docs[-1]["name"])
            if len(docs) < page_size:
                break
    if first_run and total == 0:
        raise SyncError("초회 백필 결과 0건 — 필드명 드리프트 또는 rules 변경 의심(빈 성공 금지)")
    return total
