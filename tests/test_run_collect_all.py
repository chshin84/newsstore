from datetime import datetime, timezone
import pytest
from newsstore.entrypoints.run_collect_all import _run_once
from newsstore.entrypoints._health import JobDegraded


class _HStore:
    def __init__(self):
        self.h = {}
        self.feed_states = {}
        self.pending = []

    def get_job_health(self, job): return dict(self.h.get(job, {}))
    def set_job_health(self, job, **fields):
        cur = self.h.setdefault(job, {"job": job}); cur.update(fields)
    def get_feed_state(self, feed_id): return self.feed_states.get(feed_id, {})
    def get_pending_embed_items(self, limit): return self.pending
    def count(self): return 0


def test_run_once_all_sources_ok_calls_embed_and_records_ok():
    store = _HStore()
    embed_calls = []
    def fake_embed_pass(store_, client_):
        embed_calls.append(1)
        return {"pending": 0, "embedded": 0, "permanent": 0, "retryable": 0}

    detail = _run_once(
        store,
        rss_task=lambda: {"f1": 1},
        naver_task=lambda: {"naver:q": 2},
        fmp_task=lambda: {"fmp:e": 3},
        api_key="k",
        gemini_client_factory=lambda k: object(),
        embed_pass_fn=fake_embed_pass,
    )
    assert embed_calls == [1]
    assert store.h["collect_all"]["last_status"] == "ok"
    assert "rss=ok" in detail and "naver=ok" in detail and "fmp=ok" in detail and "embed=ok" in detail


def test_run_once_one_source_raises_others_still_processed_and_degraded():
    store = _HStore()
    def boom(): raise RuntimeError("dead")
    embed_calls = []
    def fake_embed_pass(store_, client_):
        embed_calls.append(1)
        return {"pending": 0, "embedded": 0, "permanent": 0, "retryable": 0}

    with pytest.raises(JobDegraded):
        _run_once(
            store,
            rss_task=lambda: {"f1": 1},
            naver_task=boom,
            fmp_task=lambda: {"fmp:e": 3},
            api_key="k",
            gemini_client_factory=lambda k: object(),
            embed_pass_fn=fake_embed_pass,
        )
    assert embed_calls == [1]                          # 네이버가 죽어도 임베딩은 여전히 호출됨
    assert store.h["collect_all"]["last_status"] == "fail"
    assert "naver=error" in store.h["collect_all"]["detail"]


def test_run_once_embed_failure_alone_degrades_job():
    store = _HStore()
    def failing_embed_pass(store_, client_):
        raise RuntimeError("gemini down")

    with pytest.raises(JobDegraded):
        _run_once(
            store,
            rss_task=lambda: {"f1": 1},
            naver_task=lambda: {"naver:q": 1},
            fmp_task=lambda: {"fmp:e": 1},
            api_key="k",
            gemini_client_factory=lambda k: object(),
            embed_pass_fn=failing_embed_pass,
        )
    assert "embed=fail" in store.h["collect_all"]["detail"]


def test_run_once_missing_key_with_pending_degrades():
    """옛 tests/test_run_collect_embed.py::test_missing_key_with_pending_exits_1의 대체 —
    run_collect.py 삭제(Task 8)로 그 파일도 삭제되므로 이 시나리오를 여기서 이어받는다."""
    store = _HStore()
    store.pending = ["p1"]

    def should_not_be_called(store_, client_):
        raise AssertionError("embed_pass_fn should not be called when api_key is missing")

    with pytest.raises(JobDegraded):
        _run_once(
            store,
            rss_task=lambda: {"f1": 1},
            naver_task=lambda: {"naver:q": 1},
            fmp_task=lambda: {"fmp:e": 1},
            api_key=None,
            gemini_client_factory=lambda k: object(),
            embed_pass_fn=should_not_be_called,
        )
    assert "embed=fail(no_key)" in store.h["collect_all"]["detail"]


def test_run_once_missing_key_without_pending_is_ok():
    """옛 tests/test_run_collect_embed.py::test_missing_key_without_pending_exits_0의 대체."""
    store = _HStore()
    store.pending = []

    def should_not_be_called(store_, client_):
        raise AssertionError("embed_pass_fn should not be called when api_key is missing")

    detail = _run_once(
        store,
        rss_task=lambda: {"f1": 1},
        naver_task=lambda: {"naver:q": 1},
        fmp_task=lambda: {"fmp:e": 1},
        api_key=None,
        gemini_client_factory=lambda k: object(),
        embed_pass_fn=should_not_be_called,
    )
    assert "embed=skip(no_key_no_pending)" in detail
    assert store.h["collect_all"]["last_status"] == "ok"


def test_run_once_summary_fail_rate_degrades_without_task_exception():
    """naver_task는 예외 없이 정상 반환하지만(error=None), summary 안의 -1 비율이
    FAIL_RATE_ALERT(0.5) 이상이고 healthy_attempted(10)가 MIN_ATTEMPTED_FOR_ALERT(10)
    이상이라 _summary_verdict가 시스템 장애로 판정해야 한다 — 기존 테스트들은 전부
    태스크가 예외를 던지는 경로(error 마커)만 다뤘던 리뷰 지적의 커버리지 보강."""
    store = _HStore()  # feed_states 비어있음 → 만성(chronic) 없음, 전부 new_failed로 집계
    naver_summary = {f"naver:q{i}": (-1 if i < 5 else 1) for i in range(10)}  # 10건 중 5건 실패=50%
    embed_calls = []
    def fake_embed_pass(store_, client_):
        embed_calls.append(1)
        return {"pending": 0, "embedded": 0, "permanent": 0, "retryable": 0}

    with pytest.raises(JobDegraded):
        _run_once(
            store,
            rss_task=lambda: {"f1": 1},
            naver_task=lambda: naver_summary,
            fmp_task=lambda: {"fmp:e": 1},
            api_key="k",
            gemini_client_factory=lambda k: object(),
            embed_pass_fn=fake_embed_pass,
        )
    assert embed_calls == [1]                          # 시스템 장애율 판정이어도 임베딩은 여전히 호출됨
    assert store.h["collect_all"]["last_status"] == "fail"
    assert "naver=fail(" in store.h["collect_all"]["detail"]


def test_build_fmp_fetchers_url_params_and_no_apikey_leak():
    """옛 tests/test_fmp_news.py::test_build_fetchers_url_params_and_no_apikey_leak을
    build_fmp_fetchers(이름 변경)로 이관 — Task 8에서 원본 테스트는 삭제한다."""
    from newsstore.entrypoints.run_collect_all import build_fmp_fetchers

    calls = []
    class FakeResp:
        def raise_for_status(self): pass
        def json(self): return []
    class FakeClient:
        def get(self, url, params=None): calls.append((url, params)); return FakeResp()

    fetchers = build_fmp_fetchers(FakeClient(), ["stock-latest", "fmp-articles"])
    fetchers["stock-latest"]("2026-07-16", "2026-07-19", 0)
    fetchers["fmp-articles"]("2026-07-16", "2026-07-19", 1)
    assert calls[0][0].endswith("/news/stock-latest")
    assert calls[0][1] == {"from": "2026-07-16", "to": "2026-07-19", "limit": 250, "page": 0}
    assert calls[1][0].endswith("/fmp-articles")           # /news/ 아님
    assert "from" not in calls[1][1] and calls[1][1] == {"limit": 250, "page": 1}
    # 비밀 비노출: apikey가 URL·params 어디에도 없어야 한다(헤더 전용)
    for url, params in calls:
        assert "apikey" not in url and "apikey" not in (params or {})
