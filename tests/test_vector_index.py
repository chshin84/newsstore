import pytest
from newsstore.enrich.vector_index import InMemoryVectorIndex


def test_nearest_above_threshold_returns_id():
    idx = InMemoryVectorIndex()
    idx.add_story("s1", [1.0, 0.0])
    assert idx.nearest([0.99, 0.01], threshold=0.9) == "s1"
    assert idx.nearest([0.0, 1.0], threshold=0.9) is None


def test_add_member_moves_centroid():
    idx = InMemoryVectorIndex()
    idx.add_story("s1", [2.0, 0.0])      # centroid [2,0]
    idx.add_member("s1", [0.0, 2.0])     # sum [2,2] / count 2 = centroid [1,1]
    assert idx.nearest([1.0, 1.0], threshold=0.99) == "s1"


def test_add_member_unknown_story_raises():
    with pytest.raises(KeyError):
        InMemoryVectorIndex().add_member("nope", [1.0])


def test_from_open_stories_seeds_centroids():
    class FakeStore:
        def get_open_stories(self, cutoff):
            return [{"id": "s1", "centroid": [1.0, 0.0], "count": 3}]
    idx = InMemoryVectorIndex.from_open_stories(FakeStore(), cutoff=None)
    assert idx.nearest([1.0, 0.0], threshold=0.99) == "s1"
