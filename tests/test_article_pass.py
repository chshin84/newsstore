from datetime import datetime, timezone, timedelta
from newsstore.enrich.article import run_article_pass

NOW = datetime(2026, 6, 29, 12, tzinfo=timezone.utc)
CUT = NOW - timedelta(hours=1)


class _LLM:
    def generate_json(self, prompt, *, timeout=30.0):
        return {"headline": "H", "lead": "L", "article": ["b1", "b2"]}


def _doc(store, sid):
    return store.db.collection("stories").document(sid).get().to_dict() or {}


def test_generates_and_saves(store):
    store.create_story("s1", title="t", vec=[1.0], member_id="a", entities=[], now=NOW)
    store.save_story_summary("s1", title="t", summary="sum", latest="l",
                             developments=[{"text": "d", "time": NOW, "source_count": 1}],
                             summary_count=1, now=NOW)
    n = run_article_pass(store, _LLM(), now=NOW, cutoff=CUT)
    assert n["articled"] == 1 and _doc(store, "s1")["headline"] == "H"


def test_incremental_skips_then_regenerates(store):
    store.create_story("s2", title="t", vec=[1.0], member_id="a", entities=[], now=NOW)
    store.save_story_summary("s2", title="t", summary="sum", latest="l",
                             developments=[{"text": "d", "time": NOW, "source_count": 1}],
                             summary_count=1, now=NOW)
    assert run_article_pass(store, _LLM(), now=NOW, cutoff=CUT)["articled"] == 1
    assert run_article_pass(store, _LLM(), now=NOW, cutoff=CUT)["articled"] == 0   # 변화 없음 스킵
    store.append_to_story("s2", vec=[1.0], member_id="b", entities=[], now=NOW)
    assert run_article_pass(store, _LLM(), now=NOW, cutoff=CUT)["articled"] == 1   # 새 멤버 재생성


def test_nondestructive_keeps_developments_when_summary_added_later(store):
    # 비파괴 핵심: article 저장이 summary가 만든 developments를 되돌리지 않는다.
    store.create_story("s3", title="t", vec=[1.0], member_id="a", entities=[], now=NOW)
    store.save_story_summary("s3", title="t", summary="sum", latest="l",
                             developments=[{"text": "D1", "time": NOW, "source_count": 1}],
                             summary_count=1, now=NOW)
    store.append_to_story("s3", vec=[1.0], member_id="b", entities=[], now=NOW)
    run_article_pass(store, _LLM(), now=NOW, cutoff=CUT)
    # 이후 summary가 새 전개 추가 → article은 이미 저장됨. developments는 summary 소유라 살아있음.
    store.save_story_summary("s3", title="t", summary="sum2", latest="l",
                             developments=[{"text": "D1", "time": NOW, "source_count": 1},
                                           {"text": "D2", "time": NOW, "source_count": 1}],
                             summary_count=2, now=NOW)
    d = _doc(store, "s3")
    assert d["headline"] == "H" and len(d["developments"]) == 2   # 둘 다 생존


class _Boom:
    def generate_json(self, prompt, *, timeout=30.0):
        raise RuntimeError("down")


def test_failsoft(store):
    store.create_story("s4", title="t", vec=[1.0], member_id="a", entities=[], now=NOW)
    store.save_story_summary("s4", title="t", summary="s", latest="l",
                             developments=[{"text": "d", "time": NOW, "source_count": 1}],
                             summary_count=1, now=NOW)
    n = run_article_pass(store, _Boom(), now=NOW, cutoff=CUT)
    assert n["skipped"] == 1 and n["articled"] == 0 and "headline" not in _doc(store, "s4")
