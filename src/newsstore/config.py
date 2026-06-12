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
