from datetime import datetime, timezone
from newsstore.contracts.models import RawItem
from newsstore.store.firestore_store import FirestoreStore

NOW = datetime(2026, 6, 12, 7, 0, tzinfo=timezone.utc)


def _item(i):
    return RawItem(id=i, feed_id="f1", source="S", url=f"https://e/{i}",
                   title=f"t{i}", body="b", fetched_at=NOW)


def test_upsert_dedups_by_id(store):
    assert store.upsert_items([_item("a"), _item("b")]) == 2
    assert store.upsert_items([_item("a"), _item("c")]) == 1   # only "c" is new
    assert store.count() == 3


def test_context_manager_yields_store(store):
    with store as s:
        assert s.upsert_items([_item("a")]) == 1


def test_feed_state_roundtrip(store):
    assert store.get_feed_state("f1") == {}
    store.set_feed_state("f1", etag='W/"x"', last_modified="Mon", last_fetched=NOW)
    st = store.get_feed_state("f1")
    assert st["etag"] == 'W/"x"' and st["last_fetched"] == NOW


def test_set_feed_state_merges_existing_fields(store):
    store.set_feed_state("f1", etag="e1", last_fetched=NOW)
    store.set_feed_state("f1", last_modified="Tue")   # must not wipe etag
    st = store.get_feed_state("f1")
    assert st["etag"] == "e1" and st["last_modified"] == "Tue"


def test_get_unprocessed_and_mark_processed(store):
    store.upsert_items([_item("a"), _item("b"), _item("c")])
    assert {i.id for i in store.get_unprocessed()} == {"a", "b", "c"}
    assert len(store.get_unprocessed(limit=2)) == 2
    one = store.get_unprocessed(limit=1)[0]                 # round-trips to a RawItem
    assert one.fetched_at == NOW and one.feed_id == "f1"
    assert store.mark_processed(["a", "b"], processed_at=NOW) == 2
    assert {i.id for i in store.get_unprocessed()} == {"c"}
    assert store.mark_processed([]) == 0


def test_upsert_preserves_processed_on_resee(store):
    store.upsert_items([_item("a")])
    assert store.mark_processed(["a"], processed_at=NOW) == 1
    assert store.upsert_items([_item("a")]) == 0            # re-seen, not re-written
    assert store.get_unprocessed() == []                    # still processed


def test_filter_new_ids_returns_only_unstored(store):
    from datetime import datetime, timezone
    from newsstore.contracts.models import RawItem
    now = datetime(2026, 6, 12, 7, 0, tzinfo=timezone.utc)
    stored = RawItem(id="aaa", feed_id="f", source="S", url="https://e/a", title="t", fetched_at=now)
    store.upsert_items([stored])
    out = store.filter_new_ids(["aaa", "bbb", "ccc"])
    assert out == ["bbb", "ccc"]          # 저장된 aaa 제외, 순서 보존
    assert store.filter_new_ids([]) == []


def test_save_and_read_story_lenses(store):
    from datetime import datetime, timezone, timedelta
    now = datetime(2026, 6, 29, tzinfo=timezone.utc)
    store.create_story("s1", title="t", vec=[1.0], member_id="a", entities=[], now=now)
    store.save_story_lenses("s1", ["kr_rates", "risk"])
    rows = store.get_stories_for_lensing(cutoff=now - timedelta(hours=1))
    assert rows and rows[0]["id"] == "s1" and rows[0]["lenses"] == ["kr_rates", "risk"]


def test_get_story_member_signals_batches(store):
    from datetime import datetime, timezone
    from newsstore.contracts.models import RawItem
    now = datetime(2026, 6, 12, tzinfo=timezone.utc)
    store.upsert_items([RawItem(id="m1", feed_id="f", source="S", url="https://e/m1",
                                title="삼성 메모리", body="b", fetched_at=now,
                                asset_hint="kr_market,kr_corp", language="ko")])
    sig = store.get_story_member_signals(["m1"])
    assert set(sig["asset_hints"]) == {"kr_market", "kr_corp"}
    assert sig["languages"] == ["ko"] and "삼성 메모리" in sig["keyword_text"]
    assert store.get_story_member_signals([]) == {"asset_hints": [], "languages": [],
                                                  "tags": [], "keyword_text": ""}


def test_save_story_score_roundtrip_nondestructive_incremental(store):
    from datetime import datetime, timezone, timedelta
    now = datetime(2026, 6, 29, tzinfo=timezone.utc)
    cut = now - timedelta(hours=1)
    store.create_story("s1", title="t", vec=[1.0], member_id="a", entities=[], now=now)
    store.save_story_lenses("s1", ["kr_rates"], count=1)
    store.save_story_summary("s1", title="t", summary="sum", latest="l",
                             developments=[{"text": "d", "time": now, "source_count": 1}],
                             summary_count=1, now=now)
    rows = store.get_stories_for_scoring(cutoff=cut)
    assert rows and rows[0]["id"] == "s1"
    assert rows[0]["lenses"] == ["kr_rates"] and rows[0]["summary"] == "sum"
    assert rows[0]["count"] == 1 and rows[0]["developments"][0]["text"] == "d"

    store.save_story_score("s1", risk=2, impact=1, risk_reason="r", impact_reason="i",
                           count=1, now=now)
    d = store.db.collection("stories").document("s1").get().to_dict()
    assert d["risk"] == 2 and d["impact"] == 1 and d["risk_reason"] == "r"
    # 비파괴: 점수 저장이 summary/lenses/cluster 필드를 보존
    assert d["summary"] == "sum" and d["lenses"] == ["kr_rates"] and d["member_ids"] == ["a"]
    # incremental: scored_count=1 == count → 재조회에서 빠짐
    assert all(r["id"] != "s1" for r in store.get_stories_for_scoring(cutoff=cut))


def test_save_story_article_roundtrip_nondestructive_incremental(store):
    from datetime import datetime, timezone, timedelta
    now = datetime(2026, 6, 29, tzinfo=timezone.utc)
    cut = now - timedelta(hours=1)
    store.create_story("s1", title="t", vec=[1.0], member_id="a", entities=[], now=now)
    store.save_story_lenses("s1", ["kr_rates"], count=1)
    store.save_story_summary("s1", title="t", summary="sum", latest="l",
                             developments=[{"text": "d", "time": now, "source_count": 1}],
                             summary_count=1, now=now)
    store.save_story_score("s1", risk=2, impact=1, risk_reason="r", impact_reason="i",
                           count=1, now=now)
    rows = store.get_stories_for_article(cutoff=cut)
    assert rows and rows[0]["id"] == "s1"
    assert rows[0]["risk"] == 2 and rows[0]["impact"] == 1
    assert rows[0]["count"] == 1 and rows[0]["developments"][0]["text"] == "d"

    store.save_story_article("s1", headline="H", lead="L", article=["b1", "b2"],
                             risk_ref=1, impact_ref=0, score_ref_at=now, count=1, now=now)
    d = store.db.collection("stories").document("s1").get().to_dict()
    assert d["headline"] == "H" and d["lead"] == "L" and d["article"] == ["b1", "b2"]
    assert d["risk_ref"] == 1 and d["impact_ref"] == 0
    # 비파괴: article 저장이 summary/lenses/score/developments/cluster 보존
    assert d["summary"] == "sum" and d["lenses"] == ["kr_rates"] and d["risk"] == 2
    assert d["developments"][0]["text"] == "d" and d["member_ids"] == ["a"]
    # incremental: articled_count=1 == count → 재조회에서 빠짐
    assert all(r["id"] != "s1" for r in store.get_stories_for_article(cutoff=cut))


def test_get_open_stories_includes_title_and_centroid_sum(store):
    from datetime import datetime, timezone, timedelta
    now = datetime(2026, 6, 29, tzinfo=timezone.utc)
    store.create_story("s1", title="Fed move", vec=[1.0, 2.0], member_id="a",
                       entities=["Fed"], now=now)
    store.append_to_story("s1", vec=[3.0, 0.0], member_id="b", entities=[], now=now)
    [row] = store.get_open_stories(cutoff=now - timedelta(hours=1))
    assert row["title"] == "Fed move" and row["centroid_sum"] == [4.0, 2.0]
    assert row["centroid"] == [2.0, 1.0] and row["count"] == 2
