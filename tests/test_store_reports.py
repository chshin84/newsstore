"""reports/{doc_id} + get_stories_for_report 계약(에뮬레이터)."""
from datetime import datetime, timezone, timedelta

NOW = datetime(2026, 7, 4, 7, 0, tzinfo=timezone.utc)


def _mk_story(store, sid, *, lenses, last_seen, count=3, risk=1, impact=2):
    store.db.collection("stories").document(sid).set({
        "title": f"t-{sid}", "summary": f"s-{sid}", "lenses": lenses, "count": count,
        "risk": risk, "impact": impact, "member_ids": [], "entities": [],
        "developments": [], "first_seen": last_seen, "last_seen": last_seen, "status": "open"})


def test_report_roundtrip_and_overwrite(store):
    store.save_report("kr_equity", {"topic": "kr_equity", "headline": "h1", "review": {"passed": True}})
    store.save_report("kr_equity", {"topic": "kr_equity", "headline": "h2", "review": {"passed": False}})
    got = store.get_report("kr_equity")
    assert got["headline"] == "h2"                      # per-run 통째 덮어쓰기(스펙 §6)
    assert got["review"]["passed"] is False
    assert store.get_report("없는문서") == {}


def test_stories_for_report_filters_lens_window_status(store):
    cut = NOW - timedelta(hours=72)
    _mk_story(store, "in", lenses=["kr_equity", "sector_tech"], last_seen=NOW)
    _mk_story(store, "other-lens", lenses=["fx"], last_seen=NOW)
    _mk_story(store, "stale", lenses=["kr_equity"], last_seen=cut - timedelta(hours=1))
    store.db.collection("stories").document("closed").set(
        {"lenses": ["kr_equity"], "last_seen": NOW, "status": "closed"})
    got = store.get_stories_for_report("kr_equity", cutoff=cut)
    assert [s["id"] for s in got] == ["in"]
    assert got[0]["lenses"] == ["kr_equity", "sector_tech"]   # 층화 cap이 sector 라벨을 씀
    assert got[0]["impact"] == 2 and got[0]["summary"] == "s-in"
