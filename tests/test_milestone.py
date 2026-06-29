"""Phase 2 — delta_time 배정 순수 로직(LLM·store 없음)."""
from datetime import datetime, timezone, timedelta
from newsstore.enrich.milestone import assign_delta_times, prior_texts, MILESTONE_PRIOR_MAX

T0 = datetime(2026, 6, 20, 7, 0, tzinfo=timezone.utc)


def _dev(text, h, *, is_new=None, delta_h=None):
    d = {"text": text, "time": T0 + timedelta(hours=h), "source_count": 1}
    if is_new is not None:
        d["is_new"] = is_new
    if delta_h is not None:
        d["delta_time"] = T0 + timedelta(hours=delta_h)
    return d


def test_no_prior_all_get_time():
    devs = [_dev("a", 0, is_new=True), _dev("b", 2, is_new=False)]
    out = assign_delta_times(devs, prior_developments=[])
    assert [d["delta_time"] for d in out] == [T0, T0 + timedelta(hours=2)]
    assert all("is_new" not in d for d in out)            # is_new는 내부 신호, 저장 안 함


def test_is_new_true_with_prior_uses_time():
    prior = [_dev("old", 0, delta_h=0)]
    out = assign_delta_times([_dev("fresh", 5, is_new=True)], prior_developments=prior)
    assert out[0]["delta_time"] == T0 + timedelta(hours=5)


def test_recap_inherits_frontier():
    prior = [_dev("p1", 0, delta_h=0), _dev("p2", 2, delta_h=2)]   # frontier = T0+2h
    out = assign_delta_times([_dev("recap", 9, is_new=False)], prior_developments=prior)
    assert out[0]["delta_time"] == T0 + timedelta(hours=2)         # not its own 9h


def test_recap_of_old_still_frontier_approximation():
    prior = [_dev("p1", 0, delta_h=0), _dev("p2", 2, delta_h=2)]
    out = assign_delta_times([_dev("recap-of-p1", 9, is_new=False)], prior_developments=prior)
    assert out[0]["delta_time"] == T0 + timedelta(hours=2)         # 근사: 프런티어 미초과 불변식


def test_legacy_prior_without_delta_time_backfills_time():
    prior = [{"text": "p", "time": T0, "source_count": 1}]          # no delta_time → frontier None
    out = assign_delta_times([_dev("x", 3, is_new=False)], prior_developments=prior)
    assert out[0]["delta_time"] == T0 + timedelta(hours=3)          # frontier None → time


def test_missing_is_new_with_prior_is_recap():
    prior = [_dev("p", 0, delta_h=0)]
    out = assign_delta_times([_dev("x", 5)], prior_developments=prior)   # is_new 누락
    assert out[0]["delta_time"] == T0                               # 보수적 recap → frontier


def test_missing_is_new_no_prior_advances():
    out = assign_delta_times([_dev("x", 5), _dev("y", 6)], prior_developments=[])
    assert [d["delta_time"] for d in out] == [T0 + timedelta(hours=5), T0 + timedelta(hours=6)]


def test_non_bool_is_new_treated_as_recap():
    prior = [_dev("p", 0, delta_h=0)]
    out = assign_delta_times([{"text": "x", "time": T0 + timedelta(hours=5),
                               "source_count": 1, "is_new": "yes"}], prior_developments=prior)
    assert out[0]["delta_time"] == T0                               # "yes"!=True → recap


def test_prior_texts_caps_and_recent_first():
    # MILESTONE_PRIOR_MAX+3 items (i=0..MILESTONE_PRIOR_MAX+2); sorted time DESC → texts[0]=max idx
    prior = [_dev(f"d{i}", i, delta_h=i) for i in range(MILESTONE_PRIOR_MAX + 3)]
    texts = prior_texts(prior)
    assert len(texts) == MILESTONE_PRIOR_MAX
    assert texts[0] == f"d{MILESTONE_PRIOR_MAX + 2}"               # 최신(time desc) 먼저
