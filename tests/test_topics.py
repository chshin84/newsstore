from newsstore.enrich import topics


def test_load_and_registry():
    t = topics.load_topics()
    ids = topics.valid_ids(t)
    assert "kr_rates" in ids and "watch_samsung" in ids and "sector_tech" in ids
    assert topics.lens_type(t, "kr_rates") == "standing"
    assert topics.lens_type(t, "kr_policy") == "development"
    assert topics.lens_type(t, "sector_tech") == "sector"
    assert topics.lens_type(t, "watch_samsung") == "watch"
    assert topics.lens_type(t, "risk") == "risk"


def test_hint_vocab_integrity():
    # 모든 topics/entities hint가 taxonomy.yaml 어휘에 실재(드리프트 가드)
    import yaml
    tax = yaml.safe_load(open("config/taxonomy.yaml", encoding="utf-8"))
    tv, ev = set(tax["topics"]), set(tax["entities"])
    t = topics.load_topics()
    for lens in t["lenses"]:
        h = lens.get("hints", {})
        assert set(h.get("topics", [])) <= tv, f"{lens['id']} topics drift: {h.get('topics')}"
        assert set(h.get("entities", [])) <= ev, f"{lens['id']} entities drift"


def test_watch_and_sector_count():
    t = topics.load_topics()
    watch = [l for l in t["lenses"] if l["type"] == "watch"]
    assert len(watch) <= 10
    sectors = [l for l in t["lenses"] if l["type"] == "sector"]
    assert len(sectors) <= 11   # GICS vocab
