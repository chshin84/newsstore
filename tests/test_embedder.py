import pytest
from datetime import datetime, timezone
from newsstore.contracts.models import RawItem
from newsstore.enrich.embedder import embed_text, embed_items, EMBED_DIM, BODY_CAP

NOW = datetime(2026, 6, 14, tzinfo=timezone.utc)


def _item(t, b=""):
    return RawItem(id="a", feed_id="f", source="S", url="https://e/a", title=t, body=b, fetched_at=NOW)


class _FakeClient:
    def __init__(self, vec): self.vec = vec; self.seen = []
    def generate_json(self, *a, **k): ...
    def embed(self, text, *, timeout=30.0):
        self.seen.append(text)
        return list(self.vec)


def test_embed_text_joins_title_and_capped_body():
    txt = embed_text(_item("T", "B" * 1000))
    assert txt.startswith("T")
    assert len(txt) <= len("T") + 1 + BODY_CAP


def test_embed_items_returns_vectors():
    c = _FakeClient([0.1] * EMBED_DIM)
    out = embed_items([_item("T", "B")], c)
    assert out == [[0.1] * EMBED_DIM]
    assert c.seen == ["T B"]


def test_embed_items_rejects_wrong_dim():
    c = _FakeClient([0.1] * 3)               # 잘못된 차원 → fail-loud
    with pytest.raises(ValueError):
        embed_items([_item("T")], c)
