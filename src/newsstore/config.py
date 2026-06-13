from pathlib import Path
import yaml
from .models import FeedConfig

def load_feeds(path) -> list[FeedConfig]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    feeds = [FeedConfig(**entry) for entry in data["feeds"]]
    ids = [f.feed_id for f in feeds]
    dups = sorted({i for i in ids if ids.count(i) > 1})
    if dups:
        raise ValueError(f"duplicate feed_id in registry: {dups}")
    return feeds


def distinct_sources(feeds: list[FeedConfig]) -> list[str]:
    """Unique source labels in feeds.yaml order — SSOT for the site's source list."""
    seen: list[str] = []
    for f in feeds:
        if f.source not in seen:
            seen.append(f.source)
    return seen
