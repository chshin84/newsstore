from datetime import datetime, timezone, timedelta
from newsstore.contracts.models import RawItem
from newsstore.enrich.scorer import run_score_pass

NOW = datetime(2026, 6, 29, tzinfo=timezone.utc)
CUT = NOW - timedelta(hours=1)


def _item(i, **kw):
    base = dict(id=i, feed_id="f", source="S", url=f"https://e/{i}", title="t",
                fetched_at=NOW, published_at=NOW, asset_hint="", body="b")
    base.update(kw)
    return RawItem(**base)


def _summarize(store, sid, text="sum"):
    """요약 패스 산출을 흉내(점수 패스의 1차 입력). 실파이프라인에선 --mode summary가 채움."""
    store.save_story_summary(sid, title="t", summary=text, latest="l",
                             developments=[{"text": text, "time": NOW, "source_count": 1}],
                             summary_count=1, now=NOW)


class _LLM:
    def generate_json(self, prompt, *, timeout=30.0):
        return {"risk": 2, "impact": 1, "risk_reason": "r", "impact_reason": "i"}


def _doc(store, sid):
    return store.db.collection("stories").document(sid).get().to_dict() or {}


def test_standing_story_scored_with_single_member(store):
    store.upsert_items([_item("a", asset_hint="kr_bond")])
    store.create_story("s1", title="한은 금리", vec=[1.0], member_id="a", entities=[], now=NOW)
    store.save_story_lenses("s1", ["kr_rates"], count=1)
    _summarize(store, "s1")
    n = run_score_pass(store, _LLM(), now=NOW, cutoff=CUT)
    assert n["scored"] == 1 and _doc(store, "s1")["risk"] == 2 and _doc(store, "s1")["impact"] == 1


def test_nonfinancial_single_member_gated(store):
    store.upsert_items([_item("b")])
    store.create_story("s2", title="econ", vec=[1.0], member_id="b", entities=[], now=NOW)
    store.save_story_lenses("s2", ["kr_econ"], count=1)
    _summarize(store, "s2")
    n = run_score_pass(store, _LLM(), now=NOW, cutoff=CUT)
    assert n["gated"] == 1 and "risk" not in _doc(store, "s2")   # development 멤버 1 → 게이트 차단


def test_emergent_two_members_scored_via_member_fallback(store):
    # 렌즈 없음(emergent) + 멤버 2 → 게이트 통과. 요약 없음 → get_story_members 폴백 경로 검증.
    store.upsert_items([_item("e1"), _item("e2")])
    store.create_story("s5", title="emergent", vec=[1.0], member_id="e1", entities=[], now=NOW)
    store.append_to_story("s5", vec=[1.0], member_id="e2", entities=[], now=NOW)
    # 실파이프라인에선 클러스터 패스가 items.story_id를 박는다 — 여기선 그걸 흉내(폴백 입력 가능케).
    store.save_enrichment("e1", kind="story", tags=[], embedding=None, story_id="s5")
    store.save_enrichment("e2", kind="story", tags=[], embedding=None, story_id="s5")
    n = run_score_pass(store, _LLM(), now=NOW, cutoff=CUT)
    assert n["scored"] == 1 and _doc(store, "s5")["risk"] == 2


def test_incremental_skips_then_rescores(store):
    store.upsert_items([_item("c", asset_hint="crypto")])
    store.create_story("s3", title="btc", vec=[1.0], member_id="c", entities=[], now=NOW)
    store.save_story_lenses("s3", ["crypto"], count=1)
    _summarize(store, "s3")
    assert run_score_pass(store, _LLM(), now=NOW, cutoff=CUT)["scored"] == 1
    assert run_score_pass(store, _LLM(), now=NOW, cutoff=CUT)["scored"] == 0   # 변화 없음 → 스킵
    store.append_to_story("s3", vec=[1.0], member_id="c2", entities=[], now=NOW)
    assert run_score_pass(store, _LLM(), now=NOW, cutoff=CUT)["scored"] == 1   # 새 멤버 → 재채점


class _Boom:
    def generate_json(self, prompt, *, timeout=30.0):
        from newsstore.enrich.gemini import LLMError
        raise LLMError("down")


def test_failsoft_llm_error_skips_only_that_story(store):
    store.upsert_items([_item("d", asset_hint="kr_bond")])
    store.create_story("s4", title="rates", vec=[1.0], member_id="d", entities=[], now=NOW)
    store.save_story_lenses("s4", ["kr_rates"], count=1)
    _summarize(store, "s4")
    n = run_score_pass(store, _Boom(), now=NOW, cutoff=CUT)   # LLM 장애 → 스킵, 패스 안 죽음
    assert n["skipped"] == 1 and n["scored"] == 0 and "risk" not in _doc(store, "s4")


def test_score_story_propagates_non_llm_bug():
    import pytest
    from newsstore.enrich.scorer import score_story

    class _Bug:                              # 코드 버그(비-LLMError)는 전파(FAIL-LOUD)
        def generate_json(self, prompt, *, timeout=30.0):
            raise ValueError("programming bug")
    with pytest.raises(ValueError):
        score_story({"title": "t", "summary": "s"}, members=None, client=_Bug())
