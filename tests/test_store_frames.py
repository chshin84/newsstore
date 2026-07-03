"""frames/{lens_id} 계약(에뮬레이터) — 이월·스냅샷·빈 프레임."""
from datetime import datetime, timezone

NOW = datetime(2026, 7, 4, 7, 0, tzinfo=timezone.utc)
F1 = {"risks": [{"id": "r1", "text": "빅테크 capex 감속"}],
      "premiums": [{"id": "p1", "text": "HBM 수요 서프라이즈"}],
      "watchpoints": [{"id": "w1", "text": "메타 실적"}]}


def test_get_frame_empty_on_first_run(store):
    assert store.get_frame("kr_equity") == {}          # 첫 런: 없음 → {} (None 금지)


def test_save_and_get_frame_roundtrip(store):
    store.save_frame("kr_equity", dict(F1), now=NOW)
    got = store.get_frame("kr_equity")
    assert got["risks"][0]["id"] == "r1" and got["updated_at"] == NOW
    assert got["watchpoints"][0]["text"] == "메타 실적"


def test_save_frame_snapshots_previous_to_history(store):
    store.save_frame("fx", dict(F1), now=NOW)
    f2 = {"risks": [{"id": "r2", "text": "달러 초강세 재개"}], "premiums": [], "watchpoints": []}
    store.save_frame("fx", f2, now=NOW.replace(hour=8))
    snaps = list(store.db.collection("frames_history").document("fx")
                 .collection("snapshots").stream())
    assert len(snaps) == 1                             # 이전 판 1개 보관(첫 저장은 이전 판 없음)
    assert (snaps[0].to_dict() or {})["risks"][0]["id"] == "r1"
    assert store.get_frame("fx")["risks"][0]["id"] == "r2"   # 현행은 신판
