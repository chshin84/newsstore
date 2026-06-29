from __future__ import annotations
import json
import logging
import time
from typing import Any, Callable

log = logging.getLogger("newsstore.enrich.gemini")


class LLMError(RuntimeError):
    """LLM 호출 실패(타임아웃/레이트리밋/빈 응답/비JSON)를 호출자가 처리할 구조화 에러."""


def call_with_retry(call_fn: Callable[[], Any], *, attempts: int = 3,
                    base_delay: float = 0.5,
                    is_transient: Callable[[BaseException], bool] | None = None) -> Any:
    """지수 백오프 retry + None 가드. 모두 실패하면 LLMError.

    (비기능: advisor-nonfunctional — retry/None가드/구조화에러. timeout은 call_fn 내부 SDK에서.)
    is_transient(e)가 False면 그 에러는 재시도하지 않고 즉시 실패(4xx 404/400 등 비일시적).
    """
    last: BaseException | None = None
    for i in range(attempts):
        try:
            r = call_fn()
        except Exception as e:               # transient: timeout/ratelimit/5xx
            last = e
            if is_transient is not None and not is_transient(e):
                log.warning("LLM call non-transient error, not retrying: %s", e)
                break
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

    # Gemini Developer API(GEMINI_API_KEY 경로) 모델명 — 라이브 models.list로 검증한 값.
    # gemini-embedding-001은 기본 3072차원 → output_dimensionality=embed_dim(768)로 받음.
    # (Vertex의 text-embedding-004/text-multilingual-embedding은 ADC 경로라 이 키에 없음)
    def __init__(self, api_key: str, *, model: str = "gemini-3.1-flash-lite-preview",
                 embed_model: str = "gemini-embedding-001", embed_dim: int = 768):
        from google import genai            # lazy
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._embed_model = embed_model
        self._embed_dim = embed_dim

    @staticmethod
    def _is_transient(e: BaseException) -> bool:
        """4xx(404/400 등)는 비일시적 → 재시도 X. 429/타임아웃/5xx/네트워크는 재시도."""
        code = getattr(e, "code", None) or getattr(e, "status_code", None)
        if isinstance(code, int) and 400 <= code < 500:
            return code in (408, 429)
        return True

    def complete(self, prompt: str, *, timeout: float = DEFAULT_TIMEOUT) -> str:
        """평문 생성(JSON mime 없이). gray-band LLM(llm.complete)용. None 가드 재사용."""
        from google.genai import types

        def _call():
            r = self._client.models.generate_content(
                model=self._model, contents=prompt,
                config=types.GenerateContentConfig(
                    http_options=types.HttpOptions(timeout=int(timeout * 1000))))
            return getattr(r, "text", None)

        return call_with_retry(_call, is_transient=self._is_transient)

    def generate_json(self, prompt: str, *, timeout: float = DEFAULT_TIMEOUT) -> dict:
        from google.genai import types

        def _call():
            r = self._client.models.generate_content(
                model=self._model, contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    http_options=types.HttpOptions(timeout=int(timeout * 1000))))
            raw = getattr(r, "text", None)
            if raw is None:
                return None                      # None 가드 → call_with_retry가 재시도
            return json.loads(raw)               # 파싱을 콜 안에서 → 일시적 malformed JSON도 재시도

        # 파싱 실패(ValueError)는 call_with_retry가 재시도 후 소진 시 LLMError로 변환.
        return call_with_retry(_call, is_transient=self._is_transient)

    def embed(self, text: str, *, timeout: float = DEFAULT_TIMEOUT) -> list[float]:
        from google.genai import types

        def _call():
            r = self._client.models.embed_content(
                model=self._embed_model, contents=text,
                config=types.EmbedContentConfig(output_dimensionality=self._embed_dim))
            embs = getattr(r, "embeddings", None)
            return embs[0].values if embs else None

        return list(call_with_retry(_call, is_transient=self._is_transient))
