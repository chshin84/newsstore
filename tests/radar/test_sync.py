"""sync는 SDK가 아니라 REST(runQuery)로 에뮬레이터를 친다 — 프로덕션 동일 경로(스펙 §9).
시드는 SDK(fsclient)로 심어도 되지만 읽기는 반드시 sync 코드로 한다."""
import datetime as dt

import httpx
import pytest

from newsstore.radar import localdb, sync


def _seed(fsclient, n, t0):
    for i in range(n):
        fsclient.collection("items").document(f"s{i}-{t0.isoformat()}").set({
            "feed_id": "f1", "source": "src", "asset_hint": "kr_stock", "language": "ko",
            "url": f"http://x/{i}", "title": f"제목 {i}", "body": "본문",
            "published_at": None, "fetched_at": t0 + dt.timedelta(minutes=i),
            "kind": "story", "tags": [], "processed": False,
        })


def test_backfill_incremental_idempotent(fsclient, tmp_path):
    t0 = dt.datetime(2026, 7, 1, tzinfo=dt.timezone.utc)
    _seed(fsclient, 7, t0)
    db = localdb.connect_items(str(tmp_path / "local.db"))
    n1 = sync.run_sync(db, page_size=3)
    assert n1 == 7 and localdb.count_items(db) == 7
    sync.run_sync(db, page_size=3)                            # 멱등(겹침 24h upsert)
    assert localdb.count_items(db) == 7
    _seed(fsclient, 2, t0 + dt.timedelta(days=30))
    sync.run_sync(db, page_size=3)
    assert localdb.count_items(db) == 9


def test_tie_timestamps_not_lost(fsclient, tmp_path):
    t0 = dt.datetime(2026, 7, 1, tzinfo=dt.timezone.utc)
    for i in range(5):                                        # 동일 fetched_at 5건(수집 런 동률)
        fsclient.collection("items").document(f"tie{i}").set({
            "feed_id": "f", "source": "s", "asset_hint": "kr_stock", "language": "ko",
            "url": f"u{i}", "title": f"t{i}", "body": "", "published_at": None,
            "fetched_at": t0, "kind": "story", "tags": [], "processed": False})
    db = localdb.connect_items(str(tmp_path / "local.db"))
    sync.run_sync(db, page_size=2)                            # 페이지 크기 < 동률 그룹
    assert localdb.count_items(db) == 5                       # __name__ 커서로 동률 유실 없음


def test_backfill_zero_docs_crashes(fsclient, tmp_path):
    db = localdb.connect_items(str(tmp_path / "local.db"))
    with pytest.raises(sync.SyncError, match="0건"):
        sync.run_sync(db)


def test_http_403_is_crash_not_empty(tmp_path, monkeypatch):
    db = localdb.connect_items(str(tmp_path / "local.db"))
    class FakeResp:
        status_code = 403
        def raise_for_status(self):
            raise httpx.HTTPStatusError("403", request=None, response=None)
        def json(self):
            return []
    class FakeClient:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def post(self, *a, **k): return FakeResp()
    monkeypatch.setattr(sync.httpx, "Client", lambda *a, **k: FakeClient())
    with pytest.raises(httpx.HTTPStatusError):                 # 403 ≠ 빈 결과(가짜 0 금지)
        sync.run_sync(db)


def test_connection_error_crashes(tmp_path, monkeypatch):
    db = localdb.connect_items(str(tmp_path / "local.db"))
    monkeypatch.setenv("FIRESTORE_EMULATOR_HOST", "localhost:1")
    with pytest.raises(Exception):
        sync.run_sync(db)


def test_partial_page_failure_keeps_watermark_prefix(fsclient, tmp_path, monkeypatch):
    t0 = dt.datetime(2026, 7, 1, tzinfo=dt.timezone.utc)
    _seed(fsclient, 6, t0)
    db = localdb.connect_items(str(tmp_path / "local.db"))
    calls = {"n": 0}
    orig = sync._run_query_page
    def boom(*a, **k):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("network")
        return orig(*a, **k)
    monkeypatch.setattr(sync, "_run_query_page", boom)
    with pytest.raises(RuntimeError):
        sync.run_sync(db, page_size=3)
    assert localdb.get_watermark(db) is not None               # 완결 1페이지까지만 전진(prefix)
    assert localdb.count_items(db) == 3
