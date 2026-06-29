import pytest
from datetime import datetime, timezone, timedelta

NOW = datetime(2026, 6, 13, 7, 0, tzinfo=timezone.utc)


def test_create_append_centroid(store):
    store.create_story("st1", title="Iran deal", vec=[2.0, 0.0], member_id="a",
                       entities=["geopolitics"], now=NOW)
    store.append_to_story("st1", vec=[0.0, 2.0], member_id="b",
                          entities=["oil"], now=NOW)
    st = [x for x in store.get_open_stories(cutoff=NOW) if x["id"] == "st1"][0]
    assert st["centroid"] == [1.0, 1.0]    # sum [2,2] / count 2


def test_close_stale(store):
    store.create_story("old", title="t", vec=[1.0], member_id="a", entities=[], now=NOW)
    store.create_story("new", title="t", vec=[1.0], member_id="b", entities=[],
                       now=NOW + timedelta(hours=30))
    closed = store.close_stale_stories(cutoff=NOW + timedelta(hours=24))
    assert closed == 1
    open_ids = {x["id"] for x in store.get_open_stories(cutoff=NOW - timedelta(hours=1))}
    assert open_ids == {"new"}


def test_append_dedup_same_member(store):
    # 같은 member_id 재append(재처리·재시도·비원자 save+mark) → count·centroid 이중 반영 안 함(멱등)
    store.create_story("st1", title="t", vec=[2.0, 0.0], member_id="a", entities=["x"], now=NOW)
    store.append_to_story("st1", vec=[2.0, 0.0], member_id="a", entities=["x"], now=NOW)
    st = [x for x in store.get_open_stories(cutoff=NOW) if x["id"] == "st1"][0]
    assert st["count"] == 1                  # 이중 카운트 안 됨
    assert st["centroid_sum"] == [2.0, 0.0]  # centroid 이중합 안 됨


def test_append_dim_mismatch_raises(store):
    # append_to_story가 다른 차원 vec을 받으면 무음 절단 말고 터뜨린다 (원칙3)
    store.create_story("st1", title="t", vec=[1.0, 2.0], member_id="a", entities=[], now=NOW)
    with pytest.raises(ValueError):
        store.append_to_story("st1", vec=[1.0], member_id="b", entities=[], now=NOW)
