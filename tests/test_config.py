import pytest
from newsstore.collect.feeds import load_feeds, distinct_sources

def test_load_feeds(tmp_path):
    p = tmp_path / "feeds.yaml"
    p.write_text(
        "feeds:\n"
        "  - feed_id: bz_news\n"
        "    url: https://www.benzinga.com/news/feed\n"
        "    source: Benzinga\n"
        "    asset_hint: us_stock\n"
        "    poll_minutes: 5\n"
        "    body_mode: summary\n",
        encoding="utf-8",
    )
    feeds = load_feeds(p)
    assert len(feeds) == 1
    assert feeds[0].feed_id == "bz_news" and feeds[0].poll_minutes == 5

def test_unknown_key_is_rejected(tmp_path):
    # a typo'd key (body_mod) must fail loudly, not silently fall back to a default
    p = tmp_path / "feeds.yaml"
    p.write_text("feeds:\n  - {feed_id: a, url: https://e/a, source: S, body_mod: full}\n",
                 encoding="utf-8")
    with pytest.raises(Exception):
        load_feeds(p)

def test_duplicate_feed_id_is_rejected(tmp_path):
    p = tmp_path / "feeds.yaml"
    p.write_text("feeds:\n"
                 "  - {feed_id: dup, url: https://e/a, source: S}\n"
                 "  - {feed_id: dup, url: https://e/b, source: S}\n",
                 encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate feed_id"):
        load_feeds(p)


def test_distinct_sources_preserves_order_and_dedups():
    from newsstore.collect.feeds import FeedConfig
    feeds = [FeedConfig(feed_id="a", url="u", source="Bloomberg"),
             FeedConfig(feed_id="b", url="u", source="인포맥스"),
             FeedConfig(feed_id="c", url="u", source="Bloomberg")]
    assert distinct_sources(feeds) == ["Bloomberg", "인포맥스"]
