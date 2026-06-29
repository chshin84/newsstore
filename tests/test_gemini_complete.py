import types as _t

import pytest

# GeminiClient.complete는 실 SDK seam(google.genai lazy import) — 로직 테스트는 SDK 없이 도므로
# SDK 미설치 환경(lean test 이미지)에선 skip. complete의 계약(llm.complete→str)은 fake로
# clustering/cluster_adapter/processor 테스트에서 검증된다(embed/generate_json과 동일 취급).
pytest.importorskip("google.genai")

from newsstore.enrich.gemini import GeminiClient


def _client(responses):
    c = GeminiClient.__new__(GeminiClient)
    c._model = "m"; c._embed_model = "e"; c._embed_dim = 768
    seq = iter(responses)

    def generate_content(*, model, contents, config):
        return _t.SimpleNamespace(text=next(seq))

    c._client = _t.SimpleNamespace(models=_t.SimpleNamespace(generate_content=generate_content))
    return c


def test_complete_returns_plain_text():
    assert _client(["SAME\nx"]).complete("p").startswith("SAME")


def test_complete_none_guard_retries():
    assert _client([None, "DIFFERENT"]).complete("p").startswith("DIFFERENT")
