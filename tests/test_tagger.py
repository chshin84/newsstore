from datetime import datetime, timezone
from newsstore.contracts.models import RawItem
from newsstore.enrich.gemini import LLMError
from newsstore.enrich.tagger import validate_tags, build_prompt, tag_items, MAX_TICKERS

TAX = {"entities": ["Fed", "ECB"], "topics": ["rates", "inflation"]}
NOW = datetime(2026, 6, 14, tzinfo=timezone.utc)


def _item(t, b=""):
    return RawItem(id="a", feed_id="f", source="S", url="https://e/a", title=t, body=b, fetched_at=NOW)


def test_validate_keeps_only_vocab_entities_topics():
    raw = {"tickers": ["NVDA"], "entities": ["Fed", "BOGUS"], "topics": ["rates", "xxx"]}
    out = validate_tags(raw, TAX)
    assert out["entities"] == ["Fed"]
    assert out["topics"] == ["rates"]
    assert out["tickers"] == ["NVDA"]


def test_validate_caps_tickers():
    raw = {"tickers": [f"T{i}" for i in range(MAX_TICKERS + 3)], "entities": [], "topics": []}
    assert len(validate_tags(raw, TAX)["tickers"]) == MAX_TICKERS


def test_validate_rejects_bad_ticker_format():
    raw = {"tickers": ["NVDA", "not a ticker!", "AAPL"], "entities": [], "topics": []}
    assert validate_tags(raw, TAX)["tickers"] == ["NVDA", "AAPL"]


def test_validate_missing_keys_default_empty():
    assert validate_tags({}, TAX) == {"tickers": [], "entities": [], "topics": []}


def test_build_prompt_injects_vocab_ssot():
    p = build_prompt([_item("NVDA up")], TAX)
    assert "Fed" in p and "rates" in p and "NVDA up" in p


class _FakeClient:
    def __init__(self, resp): self.resp = resp; self.calls = 0
    def generate_json(self, prompt, *, timeout=30.0):
        self.calls += 1
        return self.resp
    def embed(self, text, *, timeout=30.0): ...


def test_tag_items_validates_and_preserves_order():
    resp = {"results": [
        {"tickers": ["NVDA"], "entities": ["Fed"], "topics": ["rates", "junk"]},
        {"tickers": [], "entities": ["BOGUS"], "topics": ["inflation"]},
    ]}
    out = tag_items([_item("a"), _item("b")], _FakeClient(resp), TAX)
    assert out[0] == {"tickers": ["NVDA"], "entities": ["Fed"], "topics": ["rates"]}
    assert out[1] == {"tickers": [], "entities": [], "topics": ["inflation"]}


def test_tag_items_fewer_results_fills_empty():
    # LLM이 결과를 적게 주면 빈 태그로 정렬 보존(fail-soft)
    out = tag_items([_item("a"), _item("b")], _FakeClient({"results": []}), TAX)
    assert out == [{"tickers": [], "entities": [], "topics": []}] * 2


class _RaisingClient:
    def generate_json(self, prompt, *, timeout=30.0):
        raise LLMError("non-JSON response")
    def embed(self, text, *, timeout=30.0): ...

def test_tag_items_failsoft_on_llmerror():
    # 한 배치 태깅이 LLMError(malformed JSON 등)여도 전체를 죽이지 말고 빈 태그로 진행
    out = tag_items([_item("a"), _item("b")], _RaisingClient(), TAX)
    assert out == [{"tickers": [], "entities": [], "topics": []}] * 2
