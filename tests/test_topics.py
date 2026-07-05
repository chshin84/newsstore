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


def test_report_lenses_are_assets_only():
    # 리포트 대상 = 금융 자산(type=standing)만 — 리스크·경제·정치·정책 리포트 제외(사용자 결정).
    # 비자산 뉴스는 리포트로 만들지 않고 context로 자산 리포트에 녹인다(context_lens_ids).
    t = topics.load_topics()
    ids = topics.report_lens_ids(t)
    assert "kr_equity" in ids and "fx" in ids and "crypto" in ids and "kr_realestate" in ids
    assert "risk" not in ids                               # 리스크 제외
    assert "kr_econ" not in ids and "us_econ" not in ids   # 경제 제외
    assert "kr_policy" not in ids and "us_policy" not in ids  # 정치·정책 제외
    assert all(topics.lens_type(t, i) == "standing" for i in ids)  # 전부 자산(standing)
    assert not any(i.startswith(("watch_", "sector_")) for i in ids)
    # 불변식: 대상 렌즈는 전부 report_group을 가진다(fail-loud — 누락 시 여기서 터짐)
    for lid in ids:
        assert topics.load_topics() and any(
            l["id"] == lid and l.get("report_group") for l in t["lenses"]), f"{lid}: report_group 누락"


def test_watch_tickers_yahoo_symbol_mapping():
    # 종목 히스토리 수집 대상 — 한국 티커(숫자)는 .KS, 미국은 그대로.
    t = topics.load_topics()
    by = {w["ticker"]: w for w in topics.watch_tickers(t)}
    assert by["005930"]["symbol"] == "005930.KS" and by["005930"]["label"] == "삼성전자"
    assert by["NVDA"]["symbol"] == "NVDA"
    assert len(by) >= 10                                # 10개 watch 종목


def test_price_key_mapping_for_crossvalidation():
    # 렌즈→가격키 매핑(교차검증). 가격 있는 자산만, 없으면 None(스킵).
    t = topics.load_topics()
    assert topics.price_key_for(t, "fx") == "usdkrw"
    assert topics.price_key_for(t, "us_equity") == "sp500"
    assert topics.price_key_for(t, "oil_energy") == "wti"
    assert topics.price_key_for(t, "precious_metals") == "gold"
    assert topics.price_key_for(t, "kr_realestate") is None      # 가격 없음 → 스킵
    # 매핑된 가격키는 config/prices.yaml에 실재해야 한다(드리프트 가드)
    from newsstore.collect.prices import load_price_symbols
    from pathlib import Path
    pkeys = {s.key for s in load_price_symbols(str(Path(__file__).resolve().parents[1] / "config" / "prices.yaml"))}
    for l in t["lenses"]:
        pk = l.get("price_key")
        assert pk is None or pk in pkeys, f"{l['id']}: price_key {pk!r}가 prices.yaml에 없음"


def test_context_lens_ids_includes_nonasset_for_foldin():
    # context = 시장프레임·백드롭 입력 풀 — 비자산(리스크·경제·정치·정책) 스토리를 자산 리포트로
    # 녹이려면(#2) 이 풀에 남아야 한다. watch·sector만 제외.
    t = topics.load_topics()
    ctx = topics.context_lens_ids(t)
    assert {"risk", "kr_econ", "us_econ", "kr_policy", "us_policy"} <= set(ctx)  # 비자산 포함
    assert set(topics.report_lens_ids(t)) <= set(ctx)     # 리포트 대상 ⊆ context
    assert not any(i.startswith(("watch_", "sector_")) for i in ctx)


def test_report_groups_assets_only():
    # 그룹 → 렌즈 목록(yaml 등장 순서 보존). UI 앵커 도출용. 자산 그룹만(비자산 그룹 제외).
    t = topics.load_topics()
    groups = topics.report_groups(t)
    assert groups["주식"] == ["kr_equity", "us_equity"]
    assert set(groups["원자재"]) == {"oil_energy", "precious_metals", "commodities"}
    assert "리스크" not in groups and "경제" not in groups and "정치·정책" not in groups
    flat = [lid for lids in groups.values() for lid in lids]
    assert sorted(flat) == sorted(topics.report_lens_ids(t))   # 자산 렌즈가 정확히 1그룹
