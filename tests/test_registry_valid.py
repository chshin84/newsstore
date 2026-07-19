from newsstore.collect.feeds import load_feeds

def test_registry_loads_and_is_unique():
    feeds = load_feeds("config/feeds.yaml")
    assert feeds                          # 불변식: 비어있지 않음(개수 매직넘버 금지 — SSOT는 feeds.yaml)
    ids = [f.feed_id for f in feeds]
    assert len(ids) == len(set(ids)), "duplicate feed_id"
    for f in feeds:
        assert f.url.startswith("http")
        assert f.body_mode in {"full", "summary", "headline"}   # 계약(FeedConfig Literal)과 동일 — 테스트가 더 느슨하면 안 됨
        assert f.poll_minutes >= 1

def test_distinct_sources_is_ssot_for_registry():
    from newsstore.collect.feeds import load_feeds, distinct_sources
    feeds = load_feeds("config/feeds.yaml")
    srcs = distinct_sources(feeds)
    # SSOT 불변식: 사이트 소스 목록 = 레지스트리의 모든 소스(누락·추가 없음)
    assert set(srcs) == {f.source for f in feeds}
    # 프로빙에 안 흔들리는 신뢰 family가 노출(BIS 등 프로빙 위험군은 제외)
    for s in ["매일경제", "인포맥스", "Bloomberg"]:
        assert s in srcs


def test_body_selectors_keys_are_known_feed_sources():
    # 드리프트 가드: body_fetch의 본문 셀렉터 맵 키는 feeds.yaml의 실제 source여야 한다.
    # (feeds.yaml에서 source 라벨을 바꾸면 본문 fetch가 조용히 무력화되는 것을 FAIL-LOUD로 잡음)
    from newsstore.collect.feeds import distinct_sources
    from newsstore.collect.body_fetch import BODY_SELECTORS
    sources = set(distinct_sources(load_feeds("config/feeds.yaml")))
    unknown = set(BODY_SELECTORS) - sources
    assert not unknown, f"BODY_SELECTORS keys not in feeds.yaml sources: {unknown}"


def test_source_tiers_derived_from_feeds():
    # #17: source→tier 매핑이 feeds.yaml에서 도출(첫 피드 우선), 모든 source 커버
    from newsstore.collect.feeds import source_tiers, distinct_sources
    feeds = load_feeds("config/feeds.yaml")
    tiers = source_tiers(feeds)
    assert set(tiers) == set(distinct_sources(feeds))            # 모든 source 커버
    assert all(v in {"primary", "analysis", "wire"} for v in tiers.values())
    # 첫 피드 우선(결정론): 같은 source의 첫 등장 tier와 일치
    first = {}
    for f in feeds:
        first.setdefault(f.source, f.tier)
    assert tiers == first
