from newsstore.config import load_feeds

def test_registry_loads_and_is_unique():
    feeds = load_feeds("config/feeds.yaml")
    assert len(feeds) >= 20
    ids = [f.feed_id for f in feeds]
    assert len(ids) == len(set(ids)), "duplicate feed_id"
    for f in feeds:
        assert f.url.startswith("http")
        assert f.body_mode in {"full", "summary", "headline", "calendar"}
        assert f.poll_minutes >= 1
