from newsstore.enrich.clustering import EventClusterer, cluster_articles
from newsstore.enrich.clustering_types import Article, Story


class _LLM:
    def __init__(self, verdict="DIFFERENT", boom=False):
        self.verdict, self.boom, self.calls = verdict, boom, 0

    def complete(self, prompt, *, timeout=30.0):
        self.calls += 1
        if self.boom:
            raise RuntimeError("down")
        return self.verdict


def _art(i, vec):
    return Article(id=i, title=f"t{i}", body="b", source="S", published_at="2026-06-29",
                   embedding=tuple(vec))


def test_assign_deterministic_join_identical():
    llm = _LLM()
    c = EventClusterer(embed=lambda t: [[0.0, 0.0]], llm=llm)
    s = Story(id="s1", title="x", centroid_sum=(1.0, 0.0))
    assert c.assign(_art("a", [1.0, 0.0]), [s]) == "s1" and llm.calls == 0


def test_assign_deterministic_new_orthogonal():
    llm = _LLM()
    c = EventClusterer(embed=lambda t: [[0.0, 0.0]], llm=llm)
    s = Story(id="s1", title="x", centroid_sum=(1.0, 0.0))
    assert c.assign(_art("a", [0.0, 1.0]), [s]) is None and llm.calls == 0


def test_assign_gray_band_same_joins():
    llm = _LLM("SAME")
    c = EventClusterer(embed=lambda t: [[0.0, 0.0]], llm=llm)
    s = Story(id="s1", title="x", centroid_sum=(1.0, 0.0))
    assert c.assign(_art("a", [0.83, 1.0]), [s]) == "s1" and llm.calls == 1


def test_assign_gray_band_llm_error_failsoft_new():
    llm = _LLM(boom=True)
    c = EventClusterer(embed=lambda t: [[0.0, 0.0]], llm=llm)
    s = Story(id="s1", title="x", centroid_sum=(1.0, 0.0))
    assert c.assign(_art("a", [0.83, 1.0]), [s]) is None


def test_cluster_articles_merges_same_event():
    llm = _LLM()
    out = cluster_articles([_art("a", [1.0, 0.0]), _art("b", [1.0, 0.0])],
                           embed=lambda t: [[0.0, 0.0]] * len(t), llm=llm)
    assert out["a"] == out["b"]
