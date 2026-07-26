"""embed 전용 Gemini 클라이언트 — ca8840a enrich/gemini.py의 embed 경로 축소 복원.

개조점(스펙 2026-07-16): ① generate_json·complete 미복원(YAGNI) ② 백오프에 지터
추가(동시 50이 429에서 일제 재시도하는 폭주 방지) ③ 비일시 오류를 PermanentEmbedError
(code 보존)로 구분해 호출자가 영구/재시도를 가른다.
"""
from __future__ import annotations
import logging
import random
import re
import time
from typing import Any, Callable

from ..contracts.embedding import EMBED_MODEL, EMBED_DIM, EMBED_TASK_TYPE

log = logging.getLogger("newsstore.embed.gemini")


class LLMError(RuntimeError):
    """임베딩 호출 실패(타임아웃/레이트리밋/빈 응답) — 재시도 가능 부류."""


class PermanentEmbedError(LLMError):
    """비일시 오류(4xx 비429 등) — 재시도 무의미. code로 원인 구분(400=입력, 401/403=인증)."""
    def __init__(self, msg: str, *, code: int | None = None):
        super().__init__(msg)
        self.code = code


def _status_code(e: BaseException) -> int | None:
    code = getattr(e, "code", None) or getattr(e, "status_code", None)
    return code if isinstance(code, int) else None


_KEY_RE = re.compile(r"(key=)[^&\s]+")


def redact(text: str) -> str:
    """예외/URL 문자열에서 API 키를 가린다 — 로그·에러 메시지에 비밀 금지(SECRETS)."""
    return _KEY_RE.sub(r"\1[redacted]", text)


def call_with_retry(call_fn: Callable[[], Any], *, attempts: int = 3,
                    base_delay: float = 0.5,
                    is_transient: Callable[[BaseException], bool] | None = None) -> Any:
    """지수 백오프(+지터) retry + None 가드. 비일시 오류는 즉시 PermanentEmbedError,
    재시도 소진은 LLMError — 호출자(embedder)가 영구/재시도 처분을 가른다."""
    last: BaseException | None = None
    for i in range(attempts):
        try:
            r = call_fn()
        except Exception as e:               # transient: timeout/ratelimit/5xx
            last = e
            if is_transient is not None and not is_transient(e):
                raise PermanentEmbedError(f"non-transient embed error: {redact(str(e))}",
                                          code=_status_code(e)) from e
            log.warning("embed call failed (attempt %d/%d): %s", i + 1, attempts,
                        redact(str(e)))
        else:
            if r is not None:
                return r
            last = LLMError("empty response")
            log.warning("embed empty response (attempt %d/%d)", i + 1, attempts)
        if i + 1 < attempts:
            time.sleep(base_delay * (2 ** i) * (1 + random.random()))   # 지터
    raise LLMError(f"embed call failed after {attempts} attempts") from last


class GeminiEmbedClient:
    """실 Gemini(google-genai). API key는 env GEMINI_API_KEY(로그/프롬프트 비노출).

    SDK는 lazy import라 google-genai 미설치 환경에서도 이 모듈 import는 가능
    (로직 테스트는 fake 클라이언트 사용)."""
    DEFAULT_TIMEOUT = 30.0

    def __init__(self, api_key: str):
        from google import genai             # lazy
        self._client = genai.Client(api_key=api_key)

    @staticmethod
    def _is_transient(e: BaseException) -> bool:
        """4xx(400/401/403/404 등)는 비일시적 → 재시도 X. 429/408/타임아웃/5xx/네트워크는 재시도."""
        code = _status_code(e)
        if code is not None and 400 <= code < 500:
            return code in (408, 429)
        return True

    def embed(self, text: str, *, timeout: float = DEFAULT_TIMEOUT) -> list[float]:
        from google.genai import types

        def _call():
            r = self._client.models.embed_content(
                model=EMBED_MODEL, contents=text,
                config=types.EmbedContentConfig(
                    output_dimensionality=EMBED_DIM,
                    # 저장 문서용 임베딩임을 명시한다 — 미지정이면 기본 타입이 쓰여
                    # 다운스트림이 쿼리 임베딩을 맞출 근거가 없다(계약 SSOT: contracts/embedding).
                    task_type=EMBED_TASK_TYPE,
                    # 실효 타임아웃(ms) — 행(hang)이 워커 50개를 무한 점유하면 런이
                    # 스케줄러 주기(값은 운영 문서 참조)를 넘겨 겹실행 전제
                    # (스펙 §임베딩 패스)가 무너진다.
                    http_options=types.HttpOptions(timeout=int(timeout * 1000))))
            embs = getattr(r, "embeddings", None)
            return embs[0].values if embs else None

        return list(call_with_retry(_call, is_transient=self._is_transient))
