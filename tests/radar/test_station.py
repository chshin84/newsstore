from newsstore.radar import ledgers, localdb, station


def _entry():
    return {"id": "sk_hynix", "label": "SK하이닉스", "ticker": "000660.KS", "role": "stock",
            "station": True, "aliases": ["SK하이닉스", "하이닉스"]}


def _items():
    mk = lambda i, ts, title: {"id": f"i{i}", "feed_id": "f", "source": f"s{i}",
                               "asset_hint": "kr_stock", "language": "ko", "url": f"u{i}",
                               "title": title, "body": "", "published_at": ts,
                               "fetched_at": ts, "kind": "story"}
    return [mk(1, "2026-07-10T01:00:00Z", "SK하이닉스 급락"),
            mk(2, "2026-07-10T02:00:00Z", "사이렌 울린 도심"),
            mk(3, "2026-07-09T01:00:00Z", "하이닉스가 반등")]


def test_arrival_news_matches_with_evidence_and_kst_window():
    block = station.arrival_news(_entry(), _items(), today="2026-07-10")
    assert block["total"] == 2
    assert all("alias" in h and "pos" in h for h in block["hits"])
    assert block["count_today"] == 1                             # KST 당일(7/10) 도착분만


def test_arrival_news_fold_rule():
    many = [{"id": f"i{i}", "title": f"SK하이닉스 뉴스 {i}", "body": "", "source": "s",
             "asset_hint": "kr_stock", "language": "ko", "url": f"u{i}", "feed_id": "f",
             "published_at": f"2026-07-10T{i % 24:02d}:00:00Z",
             "fetched_at": f"2026-07-10T{i % 24:02d}:00:00Z", "kind": "story"} for i in range(24)]
    block = station.arrival_news(_entry(), many, today="2026-07-10")
    assert block["total"] == 24 and len(block["shown"]) == 20 and block["folded"] == 4


def test_status_board_drawdown_and_mdd(tmp_path):
    db = localdb.connect_prices(str(tmp_path / "p.db"))
    rows = [{"ticker": "000660.KS", "date": d, "open": c, "high": c, "low": c,
             "close": c, "adj_close": c, "volume": 1} for d, c in
            [("2026-06-18", 2700000.0), ("2026-07-07", 2109000.0), ("2026-07-10", 2201000.0)]]
    localdb.upsert_prices(db, rows, source="t")
    board = station.status_board(_entry(), db)
    assert board["close"] == 2201000.0 and board["peak"] == 2700000.0
    assert round(board["drawdown"], 4) == round(2201000 / 2700000 - 1, 4)
    assert board["basis"] == "000660.KS 종가"


def test_plan_check_out_of_band():
    plan = {"type": "plan", "id": "p1", "target": "sk_hynix", "band": [2100000, 2200000],
            "invalidation": "x", "by": "2026-07-29", "thesis": "t", "date": "2026-07-10"}
    assert station.plan_check(plan, close=2201000.0)["out_of_band"] is True
    assert station.plan_check(plan, close=2150000.0)["out_of_band"] is False
    nocmp = station.plan_check(plan, close=None)                 # 가격 결측 — 비교 불가 표기
    assert nocmp["out_of_band"] is None


def test_target_gates_filter():
    gates = [{"id": "g-h", "date": "2026-07-29", "test": "t", "on_confirm": "c",
              "on_refute": "r", "status": "pending", "targets": ["sk_hynix"]},
             {"id": "g-all", "date": "2026-07-29", "test": "t", "on_confirm": "c",
              "on_refute": "r", "status": "pending"}]
    ledgers.validate_gates(gates)
    mine = station.target_gates(_entry(), gates, today="2026-07-28")
    assert [g["id"] for g in mine] == ["g-h"]                    # 종목 게이트만(전역은 일보 머리 몫)


def test_coverage_gauge():
    g = station.coverage(_entry(), _items())
    assert g["matched"] == 2 and g["sources"] >= 1 and 0 <= g["body_ratio"] <= 1
