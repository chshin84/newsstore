from newsstore.radar import daily, localdb


def _mk(i, ts, title):
    return {"id": f"i{i}", "feed_id": "f", "source": "s", "asset_hint": "kr_stock",
            "language": "ko", "url": f"u{i}", "title": title, "body": "",
            "published_at": ts, "fetched_at": ts, "kind": "story"}


def _seed_items(db, *, days=35, per_day=2):
    """기준선 창(28일)을 채우는 픽스처 — 7/10 기준 과거 days일, 하루 per_day건.
    당일(7/10)에는 급증분 4건을 얹어 뷰 임계(FIELD_MIN=3)를 넘는 발화 경로도 검증한다."""
    import datetime as dt
    rows = []
    i = 0
    end = dt.date(2026, 7, 10)
    for d in range(days):
        day = (end - dt.timedelta(days=d)).isoformat()
        for k in range(per_day):
            rows.append(_mk((i := i + 1), f"{day}T0{k}:00:00Z", f"SK하이닉스 시장 동향 {i}"))
    for k in range(4):                                            # 당일 급증(발화 경로)
        rows.append(_mk((i := i + 1), f"2026-07-10T0{k + 3}:00:00Z", f"SK하이닉스 급락 속보 {k}"))
    localdb.upsert_items(db, rows)


def _ctx(tmp_path, with_prices=False, seed=True):
    items_db = localdb.connect_items(str(tmp_path / "l.db"))
    if seed:
        _seed_items(items_db)
    prices_db = localdb.connect_prices(str(tmp_path / "p.db"))
    if with_prices:
        localdb.upsert_prices(prices_db, [{"ticker": "000660.KS", "date": "2026-07-10",
                                           "open": 1, "high": 1, "low": 1, "close": 2201000.0,
                                           "adj_close": 1, "volume": 1}], source="t")
    return items_db, prices_db


def test_report_sections_signals_and_stations(tmp_path):
    items_db, prices_db = _ctx(tmp_path, with_prices=True)
    md = daily.build_report(items_db, prices_db, today="2026-07-10")
    for sec in ("오늘의 게이트", "신호1", "신호2", "신호3", "신호4", "종목 스테이션", "부록"):
        assert sec in md, f"섹션 누락: {sec}"
    assert "피드가 본 세계" in md and "매칭:" in md
    assert "구간 밖" in md                                        # 시드 플랜 220.1만 > 220만 경고
    assert ", z=" in md                                           # 발화 경로 렌더(당일 급증 픽스처)


def test_plans_shown_even_without_prices(tmp_path):
    items_db, prices_db = _ctx(tmp_path, with_prices=False)
    md = daily.build_report(items_db, prices_db, today="2026-07-10")
    assert "결측" in md                                           # 상태판 결측 명시
    assert "plan-2026-07-10-hynix-entry" in md                    # 플랜은 가격 없이도 표기
    assert "비교 불가" in md


def test_baseline_coverage_guard_reports_missing(tmp_path):
    items_db, prices_db = _ctx(tmp_path, seed=False)
    localdb.upsert_items(items_db, [_mk(1, "2026-07-10T01:00:00Z", "SK하이닉스 단독")])
    md = daily.build_report(items_db, prices_db, today="2026-07-10")
    assert "결측: 기준선" in md                                    # 부분 백필 → 신호 결측 표기


def test_overdue_gate_warning_in_header(tmp_path):
    items_db, prices_db = _ctx(tmp_path)
    md = daily.build_report(items_db, prices_db, today="2026-09-01")
    assert "경고" in md and "pending" in md
