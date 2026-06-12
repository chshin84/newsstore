from newsstore.config import load_feeds

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
