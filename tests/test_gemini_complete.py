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


def test_embed_dim_default_derived_from_embedder():
    # 임베딩 차원의 SSOT는 embedder.EMBED_DIM — 생성자 기본값이 독립 리터럴(768)로
    # 이중 정의되면 한쪽만 바꿨을 때 런타임 ValueError로만 발견된다(드리프트 가드).
    from newsstore.enrich.embedder import EMBED_DIM
    c = GeminiClient(api_key="dummy-key-for-ctor-test")
    assert c._embed_dim == EMBED_DIM
