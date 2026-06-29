from datetime import datetime, timezone, timedelta
from newsstore.contracts.models import RawItem
from newsstore.enrich.lens_pass import run_lens_pass

NOW = datetime(2026, 6, 29, tzinfo=timezone.utc)


def _item(i, **kw):
    base = dict(id=i, feed_id="f", source="S", url=f"https://e/{i}", title="t",
                fetched_at=NOW, asset_hint="")
    base.update(kw)
    return RawItem(**base)


def test_lens_pass_assigns_from_member_asset_hint(store):
    store.upsert_items([_item("a", asset_hint="kr_bond", language="ko")])
    store.create_story("s1", title="한은 기준금리 동결", vec=[1.0], member_id="a", entities=[], now=NOW)
    n = run_lens_pass(store, now=NOW, cutoff=NOW - timedelta(hours=1))
    rows = {r["id"]: r for r in store.get_stories_for_lensing(cutoff=NOW - timedelta(hours=1))}
    assert "kr_rates" in rows["s1"]["lenses"] and n == 1


def test_lens_pass_empty_story_no_lenses(store):
    store.upsert_items([_item("b", asset_hint="", language="en")])
    store.create_story("s2", title="generic", vec=[1.0], member_id="b", entities=[], now=NOW)
    run_lens_pass(store, now=NOW, cutoff=NOW - timedelta(hours=1))
    rows = {r["id"]: r for r in store.get_stories_for_lensing(cutoff=NOW - timedelta(hours=1))}
    assert rows["s2"]["lenses"] == []          # 신호 없음 → 미배정


class _FakeLLM:
    def generate_json(self, prompt, *, timeout=30.0):
        return {"lenses": ["risk", "oil_energy"]}


def test_lens_pass_uses_llm_when_client(store):
    # asset_hint prior(oil_energy)에 더해 LLM이 의미로 risk까지 — 키워드가 놓칠 것 포착
    store.upsert_items([_item("c", asset_hint="energy", language="en")])
    store.create_story("s3", title="Hormuz tanker strike", vec=[1.0], member_id="c", entities=[], now=NOW)
    run_lens_pass(store, now=NOW, cutoff=NOW - timedelta(hours=1), client=_FakeLLM())
    rows = {r["id"]: r for r in store.get_stories_for_lensing(cutoff=NOW - timedelta(hours=1))}
    assert set(rows["s3"]["lenses"]) == {"risk", "oil_energy"}
