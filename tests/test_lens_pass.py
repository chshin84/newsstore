from datetime import datetime, timezone, timedelta
from newsstore.contracts.models import RawItem
from newsstore.enrich.lens_pass import run_lens_pass

NOW = datetime(2026, 6, 29, tzinfo=timezone.utc)


def _item(i, **kw):
    base = dict(id=i, feed_id="f", source="S", url=f"https://e/{i}", title="t",
                fetched_at=NOW, asset_hint="")
    base.update(kw)
    return RawItem(**base)


def _lenses(store, sid):       # 분류 결과는 스토리 doc에서 직접(get_stories_for_lensing은 incremental 필터)
    return (store.db.collection("stories").document(sid).get().to_dict() or {}).get("lenses", [])


def test_lens_pass_assigns_from_member_asset_hint(store):
    store.upsert_items([_item("a", asset_hint="kr_bond", language="ko")])
    store.create_story("s1", title="한은 기준금리 동결", vec=[1.0], member_id="a", entities=[], now=NOW)
    n = run_lens_pass(store, now=NOW, cutoff=NOW - timedelta(hours=1))
    assert "kr_rates" in _lenses(store, "s1") and n == 1


def test_lens_pass_empty_story_no_lenses(store):
    store.upsert_items([_item("b", asset_hint="", language="en")])
    store.create_story("s2", title="generic", vec=[1.0], member_id="b", entities=[], now=NOW)
    run_lens_pass(store, now=NOW, cutoff=NOW - timedelta(hours=1))
    assert _lenses(store, "s2") == []          # 신호 없음 → 미배정


class _FakeLLM:
    def generate_json(self, prompt, *, timeout=30.0):
        return {"lenses": ["risk", "oil_energy"]}


def test_lens_pass_incremental_skips_unchanged(store):
    store.upsert_items([_item("d", asset_hint="crypto", language="en")])
    store.create_story("s4", title="bitcoin", vec=[1.0], member_id="d", entities=[], now=NOW)
    cut = NOW - timedelta(hours=1)
    assert run_lens_pass(store, now=NOW, cutoff=cut) == 1     # 첫 분류
    assert run_lens_pass(store, now=NOW, cutoff=cut) == 0     # 변화 없음 → 스킵(incremental)
    store.append_to_story("s4", vec=[1.0], member_id="d2", entities=[], now=NOW)
    assert run_lens_pass(store, now=NOW, cutoff=cut) == 1     # 새 멤버 → 재분류


def test_lens_pass_uses_llm_when_client(store):
    # asset_hint prior(oil_energy)에 더해 LLM이 의미로 risk까지 — 키워드가 놓칠 것 포착
    store.upsert_items([_item("c", asset_hint="energy", language="en")])
    store.create_story("s3", title="Hormuz tanker strike", vec=[1.0], member_id="c", entities=[], now=NOW)
    run_lens_pass(store, now=NOW, cutoff=NOW - timedelta(hours=1), client=_FakeLLM())
    assert set(_lenses(store, "s3")) == {"risk", "oil_energy"}
