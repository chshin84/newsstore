import pytest
from newsstore.radar import watchlist


def test_load_watchlist_and_shape():
    wl = watchlist.load_watchlist("config/watchlist.yaml")
    ids = [e["id"] for e in wl]
    assert "sk_hynix" in ids and "kospi" in ids
    assert len(ids) == len(set(ids))
    hynix = next(e for e in wl if e["id"] == "sk_hynix")
    assert hynix["ticker"] == "000660.KS"
    assert hynix["station"] is True and "하이닉스" in hynix["aliases"]
    for e in wl:
        assert e["role"] in ("stock", "index", "fx")


def test_station_entries_require_aliases(tmp_path):
    bad = tmp_path / "w.yaml"
    bad.write_text(
        "entries:\n  - id: x\n    label: X\n    ticker: T\n    role: stock\n"
        "    station: true\n    aliases: []\n", encoding="utf-8")
    with pytest.raises(ValueError, match="aliases"):
        watchlist.load_watchlist(str(bad))


def test_duplicate_id_and_missing_ticker_fail(tmp_path):
    dup = tmp_path / "d.yaml"
    dup.write_text(
        "entries:\n"
        "  - {id: a, label: A, ticker: T1, role: stock, station: false, aliases: []}\n"
        "  - {id: a, label: A2, ticker: T2, role: stock, station: false, aliases: []}\n",
        encoding="utf-8")
    with pytest.raises(ValueError, match="중복"):
        watchlist.load_watchlist(str(dup))
    noticker = tmp_path / "n.yaml"
    noticker.write_text(
        "entries:\n  - {id: b, label: B, role: stock, station: false, aliases: []}\n",
        encoding="utf-8")
    with pytest.raises(ValueError, match="ticker"):
        watchlist.load_watchlist(str(noticker))
