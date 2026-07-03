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


def test_needing_summary_skips_single_member(store):
    # count<2는 사이트가 표시 안 함 → 요약 LLM 콜 낭비 방지 (단일기사 스토리 스킵)
    _mk_story(store, "single", count=1, last_seen=NOW)
    assert "single" not in {s["id"] for s in store.get_stories_needing_summary(limit=10)}


def test_needing_summary_respects_limit_oldest_first(store):
    # limit은 런당 LLM 콜 상한. 오래 굶은 것부터(last_seen asc) 소진해야 버스트에서도
    # 모든 대상이 유한 런 안에 처리된다(공정성) — 최신 우선은 꼬리 굶주림을 만든다.
    for i in range(5):
        _mk_story(store, f"s{i}", count=2, last_seen=NOW + timedelta(hours=i))
    got = store.get_stories_needing_summary(limit=2)
    assert len(got) == 2
    assert {s["id"] for s in got} == {"s0", "s1"}


def test_needing_summary_burst_does_not_starve(store):
    # 회귀 가드(starvation): last_seen 상위 N 고정 스캔창은 뉴스 버스트로 창 밖에 밀린
    # 대상이 last_seen 순위 동결로 영구히 스캔되지 않았다. 전수 스캔이면 반드시 잡힌다.
    _mk_story(store, "starved", count=3, summary_count=1, last_seen=NOW)
    for i in range(12):                              # 요약 불필요한 최신 활동 12건이 창을 채움
        _mk_story(store, f"hot{i}", count=3, summary_count=3,
                  last_seen=NOW + timedelta(hours=i + 1))
    got = {s["id"] for s in store.get_stories_needing_summary(limit=10)}
    assert "starved" in got


def test_needing_summary_skips_closed(store):
    doc = {"title": "t", "centroid_sum": [1.0], "count": 3, "summary_count": 1,
           "member_ids": ["a", "b", "c"], "entities": [], "first_seen": NOW,
           "last_seen": NOW, "status": "closed"}
    store.db.collection("stories").document("closed1").set(doc)
    assert "closed1" not in {s["id"] for s in store.get_stories_needing_summary(limit=10)}


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


# --- Phase 2: prior developments 반환 + delta_time 저장 ---

def test_needing_summary_returns_prior_developments(store):
    _mk_story(store, "a", count=5, summary_count=2, last_seen=NOW)
    devs = [{"text": "p1", "time": NOW, "source_count": 1, "delta_time": NOW}]
    store.save_story_summary("a", title="T", summary="S", latest="p1",
                             developments=devs, summary_count=2, now=NOW)
    got = {s["id"]: s for s in store.get_stories_needing_summary(limit=10)}
    assert got["a"]["developments"][0]["text"] == "p1"          # prior 동봉
    assert got["a"]["developments"][0]["delta_time"] == NOW


def test_save_story_summary_persists_delta_time(store):
    _mk_story(store, "s", count=2, last_seen=NOW)
    store.save_story_summary("s", title="T", summary="S", latest="L",
                             developments=[{"text": "d", "time": NOW,
                                            "source_count": 1, "delta_time": NOW}],
                             summary_count=2, now=NOW)
    d = store.db.collection("stories").document("s").get().to_dict()
    assert d["developments"][0]["delta_time"] == NOW
    assert d["count"] == 2                                       # cluster field 보존
