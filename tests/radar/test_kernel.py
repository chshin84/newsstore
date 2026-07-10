from newsstore.radar import kernel, match


def _item(i, ts, title, hint="kr_stock"):
    return {"id": f"i{i}", "feed_id": "f", "source": f"src{i % 2}", "asset_hint": hint,
            "language": "ko", "url": f"http://x/{i}", "title": title, "body": "",
            "published_at": ts, "fetched_at": ts, "kind": "story"}


def test_dedup_by_normalized_title():
    rows = [_item(1, "2026-07-10T01:00:00Z", "삼성전자  실적 발표"),
            _item(2, "2026-07-10T02:00:00Z", "삼성전자 실적 발표")]
    assert len(kernel.dedup(rows)) == 1


def test_zscore_series():
    assert kernel.zscore(10, [2, 2, 2, 2]) == "new"            # 표준편차 0 + 초과 → 신규
    z = kernel.zscore(10, [2, 4, 2, 4])
    assert isinstance(z, float) and z > 0
    assert kernel.zscore(0, []) == "new" or kernel.zscore(0, []) == 0.0  # 빈 기준선 규약 확인용


def test_baseline_coverage_guard():
    ok, _ = kernel.baseline_coverage([1] * 21, window_days=28, min_ratio=2 / 3)
    assert ok
    ok2, reason2 = kernel.baseline_coverage([1] * 10, window_days=28, min_ratio=2 / 3)
    assert not ok2 and "부족" in reason2


def test_article_lenses_and_lens_counts():
    rows = [_item(1, "2026-07-10T01:00:00Z", "삼성전자 실적"),
            _item(2, "2026-07-10T02:00:00Z", "코스피 반등")]
    per = kernel.article_lenses(rows)                          # {item_id: [lens_id...]} 1회 분류
    assert set(per) == {"i1", "i2"}
    counts = kernel.lens_counts_from(per)
    assert sum(counts.values()) >= 1                           # asset_hint=kr_stock 경로로 kr_equity 매칭


def test_signal2_new_edges_and_cooccur():
    rows = [_item(1, "2026-07-10T01:00:00Z", "엔비디아 HBM 공급 계약")]
    edges = kernel.cooccur_edges(rows, ["엔비디아", "HBM", "ADR"], match.find_alias)
    assert ("HBM", "엔비디아") in {tuple(sorted(e)) for e in edges}
    assert kernel.new_edges({("A", "B"), ("A", "C")}, [{("A", "B")}]) == {("A", "C")}


def test_signal3_daily_baseline_real_z():
    titles_now = ["엔드게임 공포 확산", "엔드게임 논쟁 격화", "엔드게임 재점화"]
    base_days = [["시장 상승 마감"], ["금리 동결 발표"], ["엔드게임 언급 소폭"]] * 10   # 30일 일별
    res = kernel.emerging_terms(titles_now, base_days, w_days=1)
    got = {t: (c, z) for t, c, z in res}
    assert "엔드게임" in got
    c, z = got["엔드게임"]
    assert c == 3 and isinstance(z, float) and z > 2.0          # 일별 분포 기반 실제 z(이진 퇴화 금지)


def test_signal3_bigram_emerges():
    titles_now = ["변동성 덫 경고", "변동성 덫 심화", "변동성 덫 재점화"]
    base_days = [["평온한 시장"]] * 30
    res = kernel.emerging_terms(titles_now, base_days, w_days=1)
    assert any(t == "변동성 덫" for t, _c, _z in res)            # 바이그램 검출
