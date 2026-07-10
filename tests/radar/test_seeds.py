"""시드가 자기 검증기를 통과하는지 — 시드·계약 드리프트를 커밋 전에 터뜨린다."""
from newsstore.radar import ledgers


def test_seed_gates_valid_ids_and_targets():
    gates = ledgers.load_gates("radar/gates.yaml")
    ids = {g["id"] for g in gates}
    assert {"gate-0729-hynix-call", "gate-adr-pin-release", "gate-price-sync-stability",
            "gate-workbench-adoption-review", "gate-arrival-news-verdict"} <= ids
    assert all(g["status"] == "pending" for g in gates)
    hynix_gates = ledgers.gates_for_target(gates, "sk_hynix")
    assert {"gate-0729-hynix-call", "gate-adr-pin-release"} <= {g["id"] for g in hynix_gates}


def test_seed_journal_valid():
    entries = ledgers.load_journal("journal/journal.jsonl")
    plans = [e for e in entries if e["type"] == "plan"]
    assert plans and plans[0]["target"] == "sk_hynix" and plans[0]["band"] == [2100000, 2200000]


def test_seed_frames_valid_and_gate_refs_resolve():
    gates = ledgers.load_gates("radar/gates.yaml")
    frames = ledgers.load_frames("radar/frames.json", gate_ids={g["id"] for g in gates})
    kr = frames["kr_equity"]
    assert {p["id"] for p in kr["risks"]} == {"lev-etf-reflexivity", "cycle-peak-thesis", "sell-on-best-print"}
    assert any(p.get("gate_id") == "gate-adr-pin-release" for p in kr["premiums"])
    assert "risk" in frames and any(p["id"] == "llm-herding" for p in frames["risk"]["risks"])
