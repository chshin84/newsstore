from __future__ import annotations
from ..contracts.vectors import add_vectors
from .cluster import cosine, centroid


class InMemoryVectorIndex:
    """열린 스토리 centroid를 메모리에 들고 브루트포스 코사인으로 최근접 검색.

    entries: [{'id','centroid_sum','count'}]. 현 규모(~1k)·로컬·테스트 기본 어댑터.
    미래 대규모는 contracts.ports.VectorIndex를 구현하는 FirestoreVectorIndex(find_nearest)로 드롭인.
    """

    def __init__(self, entries=None):
        self._e = [dict(x) for x in (entries or [])]

    @classmethod
    def from_open_stories(cls, store, cutoff) -> "InMemoryVectorIndex":
        es = [{"id": s["id"], "count": s["count"],
               "centroid_sum": [c * s["count"] for c in s["centroid"]]}
              for s in store.get_open_stories(cutoff=cutoff)]
        return cls(es)

    def nearest(self, vec, *, threshold):
        best_id, best = None, -1.0
        for e in self._e:
            s = cosine(vec, centroid(e["centroid_sum"], e["count"]))
            if s > best:
                best, best_id = s, e["id"]
        return best_id if best >= threshold else None

    def add_story(self, story_id, vec):
        self._e.append({"id": story_id, "centroid_sum": list(vec), "count": 1})

    def add_member(self, story_id, vec):
        for e in self._e:
            if e["id"] == story_id:
                e["centroid_sum"] = add_vectors(e["centroid_sum"], list(vec))
                e["count"] += 1
                return
        raise KeyError(story_id)
