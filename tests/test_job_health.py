"""잡 헬스 하트비트(entrypoints/_health.job_health) — 성공/실패/시작 상태 기록. 스토어 주입(fake)."""
import pytest

from newsstore.entrypoints._health import job_health


class _HStore:
    """job_health read-modify-write 최소 fake (FirestoreStore.set/get_job_health 계약 미러)."""
    def __init__(self):
        self.h = {}
        self.calls = []            # set 호출 순서의 last_status(시작=running 검증용)

    def get_job_health(self, job):
        return dict(self.h.get(job, {}))

    def set_job_health(self, job, **fields):
        self.calls.append(fields.get("last_status"))
        cur = self.h.setdefault(job, {"job": job})
        cur.update(fields)


def test_ok_path_records_success_and_detail():
    s = _HStore()
    with job_health(s, "collector") as h:
        h["detail"] = "new=5"
    st = s.h["collector"]
    assert st["last_status"] == "ok"
    assert st["detail"] == "new=5"
    assert st["last_success_at"] is not None
    assert st["last_run_at"] is not None and st["last_finished_at"] is not None


def test_start_marks_running_before_work():
    s = _HStore()
    with job_health(s, "prices"):
        # 본문 실행 시점엔 이미 running이 기록돼 있어야(하드 kill이어도 흔적이 남게).
        assert s.h["prices"]["last_status"] == "running"
    assert s.calls[0] == "running" and s.calls[-1] == "ok"


def test_fail_path_records_fail_and_reraises():
    s = _HStore()
    with pytest.raises(RuntimeError, match="boom"):
        with job_health(s, "factors") as h:
            h["detail"] = "partial"
            raise RuntimeError("boom")
    st = s.h["factors"]
    assert st["last_status"] == "fail"
    assert "boom" in st["detail"] and "partial" in st["detail"]   # 부분 진행 + 에러 둘 다
    assert "last_success_at" not in st                            # 실패는 성공 시각을 안 남김


from newsstore.entrypoints._health import classify_systemic_failure, JobDegraded


class _FeedStateStore:
    """classify_systemic_failure 검증용 — get_feed_state만 필요."""
    def __init__(self, states): self._states = states
    def get_feed_state(self, feed_id): return self._states.get(feed_id, {})


def test_classify_systemic_failure_separates_chronic_from_new():
    # f1은 만성 죽음(연속실패 5 이상), f2는 방금 실패(새로운 장애).
    store = _FeedStateStore({"f1": {"consecutive_failures": 5}, "f2": {"consecutive_failures": 1}})
    summary = {"ok1": 3, "f1": -1, "f2": -1}
    new_failed, chronic = classify_systemic_failure(summary, store)
    assert new_failed == ["f2"]
    assert chronic == {"f1"}


def test_job_health_records_fail_when_degraded_raised_inside_block():
    class _HStore:
        def __init__(self): self.h = {}
        def get_job_health(self, job): return dict(self.h.get(job, {}))
        def set_job_health(self, job, **fields):
            cur = self.h.setdefault(job, {"job": job}); cur.update(fields)

    s = _HStore()
    with pytest.raises(JobDegraded):
        with job_health(s, "collect_all") as h:
            h["detail"] = "rss=fail naver=ok fmp=ok embed=ok"
            raise JobDegraded(h["detail"])
    st = s.h["collect_all"]
    assert st["last_status"] == "fail"
    assert "rss=fail" in st["detail"]
