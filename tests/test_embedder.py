"""embed 모듈 단위 테스트 — google-genai 없이 돈다(fake 클라이언트·lazy import)."""
import pytest


# --- call_with_retry: 일시/영구 오류 구분 (ca8840a call_with_retry 개조 계약) ---

def test_retry_transient_then_success():
    from newsstore.embed.gemini import call_with_retry
    calls = []
    def fn():
        calls.append(1)
        if len(calls) < 2:
            raise TimeoutError("slow")
        return [0.1]
    assert call_with_retry(fn, base_delay=0.0) == [0.1]
    assert len(calls) == 2


def test_retry_non_transient_raises_permanent_immediately():
    from newsstore.embed.gemini import call_with_retry, PermanentEmbedError
    calls = []
    def fn():
        calls.append(1)
        e = RuntimeError("bad request")
        e.code = 400
        raise e
    with pytest.raises(PermanentEmbedError) as ei:
        call_with_retry(fn, base_delay=0.0,
                        is_transient=lambda e: not (isinstance(getattr(e, "code", None), int)
                                                    and 400 <= e.code < 500 and e.code not in (408, 429)))
    assert len(calls) == 1                     # 재시도 없이 즉시 영구 실패
    assert ei.value.code == 400


def test_retry_exhausted_raises_llmerror():
    from newsstore.embed.gemini import call_with_retry, LLMError, PermanentEmbedError
    def fn():
        raise TimeoutError("always")
    with pytest.raises(LLMError) as ei:
        call_with_retry(fn, attempts=2, base_delay=0.0)
    assert not isinstance(ei.value, PermanentEmbedError)   # 소진 = 재시도 가능 실패
