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


# --- embedder: 입력 조립 + 항목별 3분류(성공/영구/재시도) ---

class FakeEmbed:
    """스크립트대로 응답하는 fake 클라이언트. script[i] = 벡터(list) 또는 예외."""
    def __init__(self, script):
        self.script = dict(script)
        self.calls = []
    def embed(self, text, *, timeout=30.0):
        self.calls.append(text)
        r = self.script[text]
        if isinstance(r, BaseException):
            raise r
        return r


def _pi(i, title, body=""):
    return {"item_id": i, "title": title, "body": body, "expire_at": None}


def test_embed_text_caps_body_at_500():
    from newsstore.embed.embedder import embed_text, BODY_CAP
    t = embed_text(_pi("a", "T", "x" * 900))
    assert t == "T " + "x" * BODY_CAP


def test_embed_items_three_way_classification():
    from newsstore.embed.embedder import embed_items
    from newsstore.embed.gemini import LLMError, PermanentEmbedError
    items = [_pi("ok1", "good"),
             _pi("retry1", "flaky"), _pi("perm1", "reject"), _pi("empty1", "", "")]
    fake = FakeEmbed({
        "good": [0.1] * 768,
        "flaky": LLMError("exhausted"),                          # 재시도 소진 → 재시도 가능
        "reject": PermanentEmbedError("bad input", code=400),    # 400 → 영구
    })
    out = embed_items(items, fake)
    assert [r.item_id for r in out] == ["ok1", "retry1", "perm1", "empty1"]  # 순서 보존
    by = {r.item_id: r for r in out}
    assert by["ok1"].outcome == "ok" and len(by["ok1"].vector) == 768
    assert by["retry1"].outcome == "retryable"
    assert by["perm1"].outcome == "permanent"
    assert by["empty1"].outcome == "permanent"       # 빈 입력 — API 호출 없이 즉시 처분
    assert "" not in fake.calls                      # 빈 입력은 호출 안 함


def test_embed_items_dim_mismatch_aborts_pass():
    """차원 불일치는 설정 드리프트(전 항목 공통) — 항목 처분 없이 패스 전체 실패로 승격."""
    from newsstore.embed.embedder import embed_items
    from newsstore.embed.gemini import PermanentEmbedError
    fake = FakeEmbed({"short": [0.1] * 10})
    with pytest.raises(PermanentEmbedError):
        embed_items([_pi("x", "short")], fake)


def test_embed_items_auth_error_aborts_pass():
    """401/403은 항목 문제가 아니라 설정 드리프트 — 패스 전체 실패로 승격(플래그 보존)."""
    from newsstore.embed.embedder import embed_items
    from newsstore.embed.gemini import PermanentEmbedError
    fake = FakeEmbed({"a": PermanentEmbedError("unauthorized", code=401)})
    with pytest.raises(PermanentEmbedError):
        embed_items([_pi("x", "a")], fake)
