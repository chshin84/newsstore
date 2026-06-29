"""플랜 A — 스토리 요약 패스 순수 로직 테스트(에뮬레이터 불필요, fake LLMClient)."""
from datetime import datetime, timezone, timedelta

from newsstore.enrich.summarizer import (
    build_summary_prompt, validate_summary, summarize_story, run_summary_pass,
    _excerpt_len, SUMMARY_MAX_MEMBERS,
)
from newsstore.enrich.gemini import LLMError
from newsstore.enrich.milestone import MILESTONE_PRIOR_MAX  # noqa: F401

T0 = datetime(2026, 6, 13, 7, 0, tzinfo=timezone.utc)


def _members(n):
    return [{"title": f"title{i}", "body": "x" * 300, "source": f"S{i}",
             "published_at": T0 + timedelta(hours=i)} for i in range(n)]


class FakeLLM:
    def __init__(self, resp):
        self.resp = resp
        self.calls = []

    def generate_json(self, prompt, *, timeout=30.0):
        self.calls.append(prompt)
        if isinstance(self.resp, Exception):
            raise self.resp
        return self.resp

    def embed(self, text, *, timeout=30.0):
        return [0.0]


class FakeStore:
    def __init__(self, stories, members):
        self.stories = stories
        self.members = members
        self.saved = {}

    def get_stories_needing_summary(self, limit):
        return self.stories[:limit]

    def get_story_members(self, sid):
        return self.members.get(sid, [])

    def save_story_summary(self, sid, *, title, summary, latest, developments,
                           summary_count, now):
        self.saved[sid] = {"title": title, "summary": summary, "latest": latest,
                           "developments": developments, "summary_count": summary_count}


# --- build_summary_prompt / _excerpt_len ---

def test_excerpt_len_adapts():
    assert _excerpt_len(2) == 200
    assert _excerpt_len(100) == 80


def test_build_prompt_numbers_orders_truncates():
    p = build_summary_prompt(_members(3))
    assert "0. [S0] title0" in p
    assert "2. [S2] title2" in p
    assert p.index("0. [S0]") < p.index("2. [S2]")        # asc order preserved
    assert "x" * 200 in p and "x" * 201 not in p          # body capped at 200 for small n


# --- validate_summary ---

def test_build_prompt_omitted_note():
    p = build_summary_prompt(_members(3), omitted=0)
    assert "생략" not in p
    p2 = build_summary_prompt(_members(3), omitted=5)
    assert "이전 5건은 생략" in p2


def test_validate_good():
    raw = {"title": "T", "summary": "S",
           "developments": [{"text": "d", "first_idx": 1, "source_count": 2}]}
    v = validate_summary(raw, n_members=3)
    assert v["title"] == "T" and len(v["developments"]) == 1


def test_validate_missing_title_is_none():
    assert validate_summary({"summary": "s", "developments": []}, n_members=3) is None


def test_validate_non_list_developments_is_none():
    assert validate_summary({"title": "T", "summary": "S", "developments": "nope"},
                            n_members=3) is None


def test_validate_drops_out_of_range_idx():
    raw = {"title": "T", "summary": "S", "developments": [
        {"text": "a", "first_idx": 9, "source_count": 1},
        {"text": "b", "first_idx": 0, "source_count": 1}]}
    v = validate_summary(raw, n_members=3)
    assert [d["first_idx"] for d in v["developments"]] == [0]


def test_validate_clamps_source_count():
    raw = {"title": "T", "summary": "S",
           "developments": [{"text": "a", "first_idx": 0, "source_count": 999}]}
    v = validate_summary(raw, n_members=3)
    assert v["developments"][0]["source_count"] == 3


def test_validate_truncates_long_title():
    raw = {"title": "T" * 200, "summary": "S", "developments": []}
    v = validate_summary(raw, n_members=3)
    assert len(v["title"]) <= 80


# --- summarize_story ---

def test_summarize_fills_time_sorts_desc_latest():
    m = _members(3)
    resp = {"title": "T", "summary": "S", "developments": [
        {"text": "old", "first_idx": 0, "source_count": 1},
        {"text": "new", "first_idx": 2, "source_count": 1}]}
    res = summarize_story(m, FakeLLM(resp), now=T0)
    times = [d["time"] for d in res["developments"]]
    assert times == sorted(times, reverse=True)            # invariant: time DESC
    assert res["latest"] == "new"                          # newest development
    assert res["developments"][0]["time"] == m[2]["published_at"]


def test_summarize_count_is_total_not_fed():
    m = _members(5)
    resp = {"title": "T", "summary": "S",
            "developments": [{"text": "a", "first_idx": 0, "source_count": 1}]}
    res = summarize_story(m, FakeLLM(resp), now=T0, max_members=2)
    assert res["summary_count"] == 5                        # D3: total fetched, not fed


def test_summarize_drops_null_published_dev():
    m = _members(2)
    m[1]["published_at"] = None
    resp = {"title": "T", "summary": "S",
            "developments": [{"text": "a", "first_idx": 1, "source_count": 1}]}
    res = summarize_story(m, FakeLLM(resp), now=T0)
    assert res["developments"] == [] and res["latest"] == ""


def test_summarize_validate_fail_returns_none():
    assert summarize_story(_members(2), FakeLLM({"bad": "x"}), now=T0) is None


def test_summarize_empty_members_none():
    assert summarize_story([], FakeLLM({"title": "T", "summary": "S", "developments": []}),
                           now=T0) is None


# --- run_summary_pass ---

def test_run_pass_summarizes_and_saves():
    resp = {"title": "T", "summary": "S",
            "developments": [{"text": "a", "first_idx": 0, "source_count": 1}]}
    store = FakeStore([{"id": "s1", "count": 3}], {"s1": _members(3)})
    tot = run_summary_pass(store, FakeLLM(resp), limit=10, now=T0)
    assert tot == {"summarized": 1, "skipped": 0}
    assert store.saved["s1"]["summary_count"] == 3


def test_run_pass_llmerror_skips():
    store = FakeStore([{"id": "s1", "count": 3}], {"s1": _members(3)})
    tot = run_summary_pass(store, FakeLLM(LLMError("boom")), limit=10, now=T0)
    assert tot == {"summarized": 0, "skipped": 1}


def test_run_pass_empty_members_skips():
    store = FakeStore([{"id": "s1", "count": 0}], {"s1": []})
    tot = run_summary_pass(store, FakeLLM({"title": "T", "summary": "S", "developments": []}),
                           limit=10, now=T0)
    assert tot["skipped"] == 1 and tot["summarized"] == 0


# --- Phase 2: milestone(is_new) + delta_time ---

def _prior(text, h):
    return {"text": text, "time": T0 + timedelta(hours=h),
            "source_count": 1, "delta_time": T0 + timedelta(hours=h)}


def test_prompt_includes_prior_and_is_new_when_prior_given():
    p = build_summary_prompt(_members(3), prior_developments=[_prior("known", 0)])
    assert "known" in p and "is_new" in p


def test_prompt_unchanged_without_prior():
    assert "is_new" not in build_summary_prompt(_members(3))        # 하위호환


def test_validate_passes_is_new_true():
    raw = {"title": "T", "summary": "S",
           "developments": [{"text": "d", "first_idx": 0, "source_count": 1, "is_new": True}]}
    v = validate_summary(raw, n_members=3)
    assert v["developments"][0]["is_new"] is True


def test_validate_non_true_is_new_normalized_false():
    raw = {"title": "T", "summary": "S",
           "developments": [{"text": "d", "first_idx": 0, "source_count": 1, "is_new": "x"}]}
    v = validate_summary(raw, n_members=3)
    assert v["developments"][0]["is_new"] is False


def test_summarize_adds_delta_time_recap_to_frontier():
    m = _members(6)
    resp = {"title": "T", "summary": "S",
            "developments": [{"text": "recap", "first_idx": 5, "source_count": 1, "is_new": False}]}
    prior = [_prior("p1", 0), _prior("p2", 2)]
    res = summarize_story(m, FakeLLM(resp), now=T0, prior_developments=prior)
    assert res["developments"][0]["delta_time"] == T0 + timedelta(hours=2)   # 프런티어
    assert "is_new" not in res["developments"][0]                            # 저장 안 함


def test_summarize_no_prior_delta_time_is_time():
    m = _members(3)
    resp = {"title": "T", "summary": "S",
            "developments": [{"text": "a", "first_idx": 2, "source_count": 1}]}
    res = summarize_story(m, FakeLLM(resp), now=T0)
    assert res["developments"][0]["delta_time"] == m[2]["published_at"]


def test_run_pass_passes_prior_developments():
    resp = {"title": "T", "summary": "S",
            "developments": [{"text": "recap", "first_idx": 0, "source_count": 1, "is_new": False}]}
    prior = [_prior("p1", 0), _prior("p2", 2)]
    store = FakeStore([{"id": "s1", "count": 5, "developments": prior}], {"s1": _members(5)})
    run_summary_pass(store, FakeLLM(resp), limit=10, now=T0)
    assert store.saved["s1"]["developments"][0]["delta_time"] == T0 + timedelta(hours=2)
