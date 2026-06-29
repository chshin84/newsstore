def test_article_and_story_defaults():
    from newsstore.enrich.clustering_types import Article, Story
    a = Article(id="x", title="t", body="b", source="S", published_at="2026-06-29")
    assert a.tags == () and a.embedding is None
    s = Story(id="s", title="t")
    assert s.centroid_sum is None and s.status == "open" and s.member_ids == ()
