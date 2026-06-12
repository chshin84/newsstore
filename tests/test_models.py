from datetime import datetime, timezone
from newsstore.models import FeedConfig, RawItem, make_id

def test_make_id_is_stable_and_url_based():
    a = make_id("https://x.com/a?utm=1")
    b = make_id("https://x.com/a?utm=1")
    assert a == b and len(a) == 40

def test_make_id_falls_back_to_title_when_no_link():
    assert make_id("", fallback="Some Title") == make_id("", fallback="Some Title")
    assert make_id("", fallback="A") != make_id("", fallback="B")

def test_feedconfig_defaults():
    f = FeedConfig(feed_id="bz_news", url="https://e/x.rss", source="Benzinga")
    assert f.poll_minutes == 60 and f.body_mode == "summary" and f.language == "en"

def test_rawitem_roundtrips():
    now = datetime(2026, 6, 12, tzinfo=timezone.utc)
    it = RawItem(id="abc", feed_id="bz_news", source="Benzinga", url="https://e/a",
                 title="T", body="B", published_at=now, fetched_at=now)
    assert it.id == "abc" and it.published_at == now
