"""플랜 A — 요약 패스용 신규 Store 메서드(에뮬레이터)."""
from datetime import datetime, timezone, timedelta

NOW = datetime(2026, 6, 13, 7, 0, tzinfo=timezone.utc)


def _mk_story(store, sid, *, count, last_seen, summary_count=None):
    doc = {"title": "t", "centroid_sum": [1.0], "count": count,
           "member_ids": [f"m{i}" for i in range(count)], "entities": [],
           "first_seen": NOW, "last_seen": last_seen, "status": "open"}
    if summary_count is not None:
        doc["summary_count"] = summary_count
    store.db.collection("stories").document(sid).set(doc)


def test_needing_summary_filters_new_members(store):
    _mk_story(store, "a", count=3, summary_count=3, last_seen=NOW)                       # no new
    _mk_story(store, "b", count=5, summary_count=2, last_seen=NOW + timedelta(hours=1))  # new
    _mk_story(store, "c", count=2, last_seen=NOW + timedelta(hours=2))                   # never summarized
    got = store.get_stories_needing_summary(limit=10)
    ids = {s["id"] for s in got}
    assert ids == {"b", "c"}                       # invariant: count>summary_count only
    assert "a" not in ids


def test_needing_summary_respects_limit_recent_first(store):
    for i in range(5):
        _mk_story(store, f"s{i}", count=2, last_seen=NOW + timedelta(hours=i))
    got = store.get_stories_needing_summary(limit=2)
    assert len(got) == 2
    assert {s["id"] for s in got} == {"s4", "s3"}  # most recent last_seen


def test_get_story_members_filtered_and_sorted(store):
    col = store.db.collection("items")
    col.document("i1").set({"story_id": "s1", "title": "old", "body": "b", "source": "X",
                            "published_at": NOW})
    col.document("i2").set({"story_id": "s1", "title": "new", "body": "b", "source": "Y",
                            "published_at": NOW + timedelta(hours=2)})
    col.document("i3").set({"story_id": "s2", "title": "other", "body": "b", "source": "Z",
                            "published_at": NOW})
    got = store.get_story_members("s1")
    assert [m["title"] for m in got] == ["old", "new"]      # asc, only s1
    assert got[0]["source"] == "X"


def test_save_story_summary_preserves_existing_fields(store):
    _mk_story(store, "s", count=4, last_seen=NOW)
    store.save_story_summary("s", title="T", summary="Sum", latest="L",
                             developments=[{"text": "d", "time": NOW, "source_count": 1}],
                             summary_count=4, now=NOW)
    d = store.db.collection("stories").document("s").get().to_dict()
    assert d["summary"] == "Sum" and d["summary_count"] == 4 and d["latest"] == "L"
    assert d["count"] == 4 and len(d["member_ids"]) == 4    # cluster fields preserved


def test_resummary_cycle_on_new_member(store):
    """D3: 요약 후 새 멤버가 붙으면(count>summary_count) 다시 대상에 포함, 안 붙으면 제외."""
    store.create_story("s", title="t", vec=[1.0, 0.0], member_id="a", entities=[], now=NOW)
    store.save_story_summary("s", title="T", summary="S", latest="L", developments=[],
                             summary_count=1, now=NOW)
    assert "s" not in {x["id"] for x in store.get_stories_needing_summary(limit=10)}  # count==summary_count
    store.append_to_story("s", vec=[0.0, 1.0], member_id="b", entities=[],
                          now=NOW + timedelta(hours=1))                                # count→2
    assert "s" in {x["id"] for x in store.get_stories_needing_summary(limit=10)}       # 2>1 → 재요약 대상


def test_append_to_story_preserves_summary(store):
    """D7 레이스 가드: append가 필드 merge라 사전 기록된 summary를 지우지 않는다."""
    store.create_story("s", title="t", vec=[1.0, 0.0], member_id="a", entities=[], now=NOW)
    store.save_story_summary("s", title="T", summary="Sum", latest="L",
                             developments=[{"text": "d", "time": NOW, "source_count": 1}],
                             summary_count=1, now=NOW)
    store.append_to_story("s", vec=[0.0, 1.0], member_id="b", entities=[], now=NOW)
    d = store.db.collection("stories").document("s").get().to_dict()
    assert d["summary"] == "Sum"                            # not wiped by append
    assert d["count"] == 2 and "b" in d["member_ids"]       # cluster field updated
