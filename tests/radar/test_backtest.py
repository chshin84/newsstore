from newsstore.radar import backtest, localdb


def _mk(i, day, title):
    ts = f"{day}T09:00:00Z"
    return {"id": f"b{i}", "feed_id": "f", "source": "s", "asset_hint": "kr_stock",
            "language": "ko", "url": f"u{i}", "title": title, "body": "",
            "published_at": ts, "fetched_at": ts, "kind": "story"}


def _seed(db):
    rows, i = [], 0
    for d in range(1, 31):
        rows.append(_mk((i := i + 1), f"2026-06-{d:02d}", "시장 동향 정리"))
    for d in (4, 5, 6):
        for k in range(3):
            rows.append(_mk((i := i + 1), f"2026-07-{d:02d}", f"엔드게임 공포 {k}"))
    localdb.upsert_items(db, rows)


def test_lead_time_detects_pre_event_emergence(tmp_path):
    db = localdb.connect_items(str(tmp_path / "l.db"))
    _seed(db)
    res = backtest.lead_times(db, terms=["엔드게임"], event_day="2026-07-07",
                              start="2026-07-01", end="2026-07-08", w_days=3, m=3, z=2.0)
    assert res["엔드게임"] is not None and res["엔드게임"] < 0


def test_target_terms_fixed_list():
    assert len(backtest.TARGET_TERMS) == 10
    assert "엔드게임" in backtest.TARGET_TERMS and "HBM" in backtest.TARGET_TERMS


def test_corpus_presence_gate(tmp_path):
    db = localdb.connect_items(str(tmp_path / "l.db"))
    localdb.upsert_items(db, [_mk(1, "2026-07-01", "무관 제목")])
    present = backtest.corpus_presence(db, backtest.TARGET_TERMS)
    assert sum(1 for v in present.values() if v > 0) < 2          # 사전 게이트가 중단 사유를 보고


def test_signal1_fp_and_signal2_volume_run(tmp_path):
    db = localdb.connect_items(str(tmp_path / "l.db"))
    _seed(db)
    fp = backtest.signal1_fp_by_weekday(db, month_start="2026-06-01", month_end="2026-06-30")
    assert isinstance(fp, dict) and len(fp) == 7                  # 요일별 오탐 분해(왜곡 실측)
    vol = backtest.signal2_weekly_volume(db, weeks=8, as_of="2026-07-08")
    assert isinstance(vol, list)                                  # 주별 신규 간선 수(강등 판정 근거)
