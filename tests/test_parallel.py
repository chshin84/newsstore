import logging
import time
import pytest
from newsstore.collect.collector import CollectorTimeoutError
from newsstore.entrypoints._parallel import run_sources_parallel


def test_all_sources_succeed():
    results = run_sources_parallel({
        "a": lambda: {"a1": 1},
        "b": lambda: {"b1": 2},
    }, timeout=5)
    assert results["a"] == ({"a1": 1}, None)
    assert results["b"] == ({"b1": 2}, None)


def test_one_source_raises_others_still_return():
    def boom():
        raise RuntimeError("dead")
    results = run_sources_parallel({
        "ok": lambda: {"x": 1},
        "bad": boom,
    }, timeout=5)
    assert results["ok"] == ({"x": 1}, None)
    assert results["bad"] == ({}, "error")


def test_source_own_deadline_exceeded_is_marked_distinctly_from_generic_error():
    def budget_exceeded():
        raise CollectorTimeoutError("budget exceeded")
    results = run_sources_parallel({"ok": lambda: {"x": 1}, "slow_src": budget_exceeded}, timeout=5)
    assert results["slow_src"] == ({}, "deadline")   # "error"와 구분돼야 진단 가치가 있다


def test_slow_source_times_out_without_blocking_fast_one():
    def slow():
        time.sleep(1.0)
        return {"never": "seen"}
    def fast():
        return {"y": 1}
    t0 = time.time()
    results = run_sources_parallel({"slow": slow, "fast": fast}, timeout=0.1)
    elapsed = time.time() - t0
    assert results["fast"] == ({"y": 1}, None)
    assert results["slow"] == ({}, "timeout")
    assert elapsed < 0.5   # 함수 자체는 slow를 기다리지 않고 빨리 반환한다(설계 문서 "2단 백스톱" 참고)


def test_multiple_slow_sources_share_one_timeout_budget_not_compounded():
    def slow(n):
        def _f():
            time.sleep(n)
            return {"never": "seen"}
        return _f
    t0 = time.time()
    results = run_sources_parallel({"s1": slow(0.3), "s2": slow(0.3), "s3": slow(0.3)}, timeout=0.1)
    elapsed = time.time() - t0
    assert results["s1"] == ({}, "timeout")
    assert results["s2"] == ({}, "timeout")
    assert results["s3"] == ({}, "timeout")
    assert elapsed < 0.3   # NOT ~0.3 (3 x 0.1 compounded) — must share one 0.1s budget


def test_late_exception_after_timeout_is_still_logged(caplog):
    """Fail-loud 검증: 오케스트레이터가 포기하고 넘어간 뒤에도, 그 스레드가 나중에 실제로
    예외를 던지면 조용히 사라지지 않고 반드시 로그로 남아야 한다."""
    def slow_then_fails():
        time.sleep(0.2)
        raise RuntimeError("late network error")
    with caplog.at_level(logging.ERROR, logger="newsstore.entrypoints.parallel"):
        run_sources_parallel({"slow": slow_then_fails}, timeout=0.05)
        time.sleep(0.4)   # slow_then_fails가 실제로 끝나 done_callback이 발동할 시간을 준다
    assert any("late network error" in r.message or "뒤늦게" in r.message for r in caplog.records)
