from newsstore.collect.feeds import load_feeds

def test_registry_loads_and_is_unique():
    feeds = load_feeds("config/feeds.yaml")
    assert feeds                          # 불변식: 비어있지 않음(개수 매직넘버 금지 — SSOT는 feeds.yaml)
    ids = [f.feed_id for f in feeds]
    assert len(ids) == len(set(ids)), "duplicate feed_id"
    for f in feeds:
        assert f.url.startswith("http")
        assert f.body_mode in {"full", "summary", "headline", "calendar"}
        assert f.poll_minutes >= 1

def test_distinct_sources_is_ssot_for_registry():
    from newsstore.collect.feeds import load_feeds, distinct_sources
    feeds = load_feeds("config/feeds.yaml")
    srcs = distinct_sources(feeds)
    # SSOT 불변식: 사이트 소스 목록 = 레지스트리의 모든 소스(누락·추가 없음)
    assert set(srcs) == {f.source for f in feeds}
    # 프로빙에 안 흔들리는 신뢰 family가 노출(BIS 등 프로빙 위험군은 제외)
    for s in ["Benzinga", "매일경제", "한국경제"]:
        assert s in srcs


def test_body_selectors_keys_are_known_feed_sources():
    # 드리프트 가드: body_fetch의 본문 셀렉터 맵 키는 feeds.yaml의 실제 source여야 한다.
    # (feeds.yaml에서 source 라벨을 바꾸면 본문 fetch가 조용히 무력화되는 것을 FAIL-LOUD로 잡음)
    from newsstore.collect.feeds import distinct_sources
    from newsstore.collect.body_fetch import BODY_SELECTORS
    sources = set(distinct_sources(load_feeds("config/feeds.yaml")))
    unknown = set(BODY_SELECTORS) - sources
    assert not unknown, f"BODY_SELECTORS keys not in feeds.yaml sources: {unknown}"
