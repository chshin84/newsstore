from datetime import datetime, timezone

from newsstore.contracts.models import RawItem
from newsstore.enrich import cluster_adapter

_NOW = datetime(2026, 6, 29, tzinfo=timezone.utc)


class _Client:
    def __init__(self, verdict="DIFFERENT"):
        self.verdict = verdict

    def embed(self, text, *, timeout=30.0):
        return [0.0, 0.0]

    def complete(self, prompt, *, timeout=30.0):
        return self.verdict


def _item(i):
    return RawItem(id=i, feed_id="f", source="S", url=f"https://e/{i}", title=f"t{i}",
                   body="b", fetched_at=_NOW)


def _row(sid, csum):
    return {"id": sid, "title": "x", "centroid_sum": list(csum),
            "centroid": list(csum), "count": 1}


def test_to_stories_maps_centroid_sum():
    [s] = cluster_adapter.to_stories([_row("s1", [1.0, 0.0])])
    assert s.id == "s1" and tuple(s.centroid_sum) == (1.0, 0.0)


def test_to_stories_skips_rows_without_centroid_sum():
    assert cluster_adapter.to_stories([{"id": "s1", "title": "x"}]) == []


def test_assign_join_identical():
    cl = cluster_adapter.build_clusterer(_Client())
    open_stories = cluster_adapter.to_stories([_row("s1", [1.0, 0.0])])
    assert cluster_adapter.assign(cl, _item("a"), [1.0, 0.0], open_stories) == "s1"


def test_assign_new_orthogonal():
    cl = cluster_adapter.build_clusterer(_Client())
    open_stories = cluster_adapter.to_stories([_row("s1", [1.0, 0.0])])
    assert cluster_adapter.assign(cl, _item("a"), [0.0, 1.0], open_stories) is None
