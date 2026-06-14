import pytest
from newsstore.enrich.llm import call_with_retry, LLMError


def test_retry_succeeds_after_transient():
    calls = {"n": 0}
    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise TimeoutError("transient")
        return {"ok": True}
    assert call_with_retry(flaky, attempts=3, base_delay=0) == {"ok": True}
    assert calls["n"] == 3


def test_retry_exhausts_raises_llmerror():
    def always():
        raise TimeoutError("nope")
    with pytest.raises(LLMError):
        call_with_retry(always, attempts=2, base_delay=0)


def test_none_response_raises_llmerror():
    # 실 SDK는 빈 결과에 None 반환 가능 → AttributeError 대신 구조화 에러
    with pytest.raises(LLMError):
        call_with_retry(lambda: None, attempts=1, base_delay=0)


def test_no_retry_when_not_transient():
    # 비일시적 에러(4xx 404/400)는 재시도 낭비 없이 즉시 실패 (advisor-nonfunctional)
    calls = {"n": 0}
    def boom():
        calls["n"] += 1
        raise ValueError("404 not found")
    with pytest.raises(LLMError):
        call_with_retry(boom, attempts=3, base_delay=0, is_transient=lambda e: False)
    assert calls["n"] == 1
