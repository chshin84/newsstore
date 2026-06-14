from __future__ import annotations
import json
import logging
import time
from typing import Any, Callable, Protocol

log = logging.getLogger("newsstore.enrich.llm")


class LLMError(RuntimeError):
    """LLM 호출 실패(타임아웃/레이트리밋/빈 응답/비JSON)를 호출자가 처리할 구조화 에러."""


class LLMClient(Protocol):
    def generate_json(self, prompt: str, *, timeout: float) -> dict: ...
    def embed(self, text: str, *, timeout: float) -> list[float]: ...


def call_with_retry(call_fn: Callable[[], Any], *, attempts: int = 3,
                    base_delay: float = 0.5) -> Any:
    """지수 백오프 retry + None 가드. 모두 실패하면 LLMError.

    (비기능: advisor-nonfunctional — retry/None가드/구조화에러. timeout은 call_fn 내부 SDK에서.)
    """
    last: BaseException | None = None
    for i in range(attempts):
        try:
            r = call_fn()
        except Exception as e:               # transient: timeout/ratelimit/5xx
            last = e
            log.warning("LLM call failed (attempt %d/%d): %s", i + 1, attempts, e)
        else:
            if r is not None:
                return r
            last = LLMError("empty response")
            log.warning("LLM empty response (attempt %d/%d)", i + 1, attempts)
        if i + 1 < attempts:
            time.sleep(base_delay * (2 ** i))
    raise LLMError(f"LLM call failed after {attempts} attempts") from last


class GeminiClient:
    """실 Gemini(google-genai). API key는 env GEMINI_API_KEY(로그/프롬프트 비노출).

    저수준 SDK 호출을 call_with_retry로 감싸 비기능 요건을 입힌다. SDK는 lazy import라
    google-genai 미설치 환경에서도 이 모듈 import는 가능(로직 테스트는 fake LLMClient 사용).
    """
    DEFAULT_TIMEOUT = 30.0

    def __init__(self, api_key: str, *, model: str = "gemini-2.0-flash",
                 embed_model: str = "text-multilingual-embedding-002"):
        from google import genai            # lazy
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._embed_model = embed_model

    def generate_json(self, prompt: str, *, timeout: float = DEFAULT_TIMEOUT) -> dict:
        from google.genai import types

        def _call():
            r = self._client.models.generate_content(
                model=self._model, contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    http_options=types.HttpOptions(timeout=int(timeout * 1000))))
            return getattr(r, "text", None)

        raw = call_with_retry(_call)
        try:
            return json.loads(raw)
        except (TypeError, ValueError) as e:
            raise LLMError(f"non-JSON response: {e}") from e

    def embed(self, text: str, *, timeout: float = DEFAULT_TIMEOUT) -> list[float]:
        def _call():
            r = self._client.models.embed_content(model=self._embed_model, contents=text)
            embs = getattr(r, "embeddings", None)
            return embs[0].values if embs else None

        return list(call_with_retry(_call))
