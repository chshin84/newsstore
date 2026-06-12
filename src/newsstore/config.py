from pathlib import Path
import yaml
from .models import FeedConfig

def load_feeds(path) -> list[FeedConfig]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return [FeedConfig(**entry) for entry in data["feeds"]]
