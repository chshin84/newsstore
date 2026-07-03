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


def test_asset_hint_vocab_exists_in_feeds():
    # 스펙(phase1 §7·§8) 드리프트 가드의 나머지 절반: 렌즈의 asset_hint 어휘는 feeds.yaml이
    # 실제 발행하는 어휘여야 한다 — 아무 피드도 안 내는 힌트는 영원히 매칭 불가(죽은 어휘)로
    # 조용히 썩는다(과거 kr_fx). 역방향(피드 어휘 전부가 렌즈에 매핑)은 요구하지 않는다.
    from newsstore.collect.feeds import load_feeds
    feed_hints = set()
    for f in load_feeds("config/feeds.yaml"):
        for h in (f.asset_hint or "").split(","):
            if h.strip():
                feed_hints.add(h.strip())
    t = topics.load_topics()
    lens_hints = {h for l in t["lenses"] for h in l.get("hints", {}).get("asset_hint", [])}
    dead = lens_hints - feed_hints
    assert not dead, f"topics.yaml 렌즈 asset_hint 중 feeds.yaml이 발행하지 않는 어휘: {sorted(dead)}"


def test_watch_and_sector_count():
    t = topics.load_topics()
    watch = [l for l in t["lenses"] if l["type"] == "watch"]
    assert len(watch) <= 10
    sectors = [l for l in t["lenses"] if l["type"] == "sector"]
    assert len(sectors) <= 11   # GICS vocab


def test_lens_labels():
    t = topics.load_topics()
    labels = topics.lens_labels(t)
    assert labels["us_equity"] == "미국 주식"          # UI 라벨(SSOT=label.ko)
    assert labels["watch_nvidia"] == "엔비디아"
    assert set(labels) == topics.valid_ids(t)          # 모든 렌즈 포함(누락 없음)
