import pytest

from newsstore.radar import ledgers


def _gate(**kw):
    g = {"id": "g1", "date": "2026-07-29", "test": "t", "on_confirm": "c",
         "on_refute": "r", "status": "pending"}
    g.update(kw)
    return g


def test_gates_status_vocab_and_transition_requires_user():
    ledgers.validate_gates([_gate()])
    with pytest.raises(ValueError, match="status"):
        ledgers.validate_gates([_gate(status="done")])
    with pytest.raises(ValueError, match="judged_by"):
        ledgers.validate_gates([_gate(status="confirmed")])
    ledgers.validate_gates([_gate(status="confirmed", judged_by="user")])


def test_gates_targets_optional_list():
    ledgers.validate_gates([_gate(targets=["sk_hynix"])])
    with pytest.raises(ValueError, match="targets"):
        ledgers.validate_gates([_gate(targets="sk_hynix")])       # 리스트가 아니면 거부


def test_gates_overdue_and_due_window():
    over = ledgers.overdue_pending([_gate(date="2026-07-01")], today="2026-07-10", grace_days=3)
    assert [g["id"] for g in over] == ["g1"]
    assert ledgers.overdue_pending([_gate(date="2026-07-09")], today="2026-07-10", grace_days=3) == []
    assert ledgers.due_around([_gate(date="2026-07-11")], today="2026-07-10")
    assert not ledgers.due_around([_gate(date="2026-07-20")], today="2026-07-10")


def test_journal_plan_requires_invalidation_and_by(tmp_path):
    p = tmp_path / "j.jsonl"
    ok = {"type": "plan", "id": "p1", "date": "2026-07-10", "target": "sk_hynix",
          "thesis": "t", "band": [1, 2], "invalidation": "x", "triggers": [], "by": "2026-07-29"}
    ledgers.append_journal(str(p), ok)
    bad = dict(ok, id="p2")
    bad.pop("invalidation")
    with pytest.raises(ValueError, match="invalidation"):
        ledgers.append_journal(str(p), bad)
    assert len(p.read_text(encoding="utf-8").strip().splitlines()) == 1


def test_journal_review_verdict_basis_schema(tmp_path):
    p = tmp_path / "j.jsonl"
    ok = {"type": "review", "plan_id": "p1", "date": "2026-08-01",
          "verdict_basis": {"kind": "price", "metric": "close", "value": 2050000, "source": "prices.db"}}
    ledgers.append_journal(str(p), ok)
    with pytest.raises(ValueError, match="verdict_basis"):
        ledgers.append_journal(str(p), {"type": "review", "plan_id": "p1", "date": "2026-08-01",
                                        "verdict_basis": "느낌이 나빴다"})
    narr = {"type": "review", "plan_id": "p1", "date": "2026-08-01",
            "verdict_basis": {"kind": "narrative", "note": "서사"}}
    with pytest.raises(ValueError, match="user_approved"):
        ledgers.append_journal(str(p), narr)
    ledgers.append_journal(str(p), dict(narr, user_approved=True))


def test_frames_v2_local_contract():
    def pole(i, status="active"):
        return {"id": f"p{i}", "label": f"L{i}", "evidence": "e", "test": "t",
                "retire_when": "w", "status": status}
    frame = {"risks": [pole(i) for i in range(5)], "premiums": [], "watchpoints": []}
    ledgers.validate_frames({"kr_equity": frame}, gate_ids=set())
    with pytest.raises(ValueError, match="5"):
        ledgers.validate_frames({"kr_equity": {"risks": [pole(i) for i in range(6)],
                                               "premiums": [], "watchpoints": []}}, gate_ids=set())
    retired_ok = {"risks": [pole(i) for i in range(5)] + [pole(9, "retired")],
                  "premiums": [], "watchpoints": []}
    ledgers.validate_frames({"kr_equity": retired_ok}, gate_ids=set())
    with pytest.raises(ValueError, match="gate"):
        ledgers.validate_frames({"kr_equity": {"risks": [dict(pole(1), gate_id="ghost")],
                                               "premiums": [], "watchpoints": []}}, gate_ids={"g1"})
    with pytest.raises(ValueError, match="축"):
        ledgers.validate_frames({"kr_equity": {"risks": []}}, gate_ids=set())
    dropped = ledgers.drop_invalid_poles({"risks": [pole(1), {"id": "", "label": ""}],
                                          "premiums": [], "watchpoints": []})
    assert [q["id"] for q in dropped["risks"]] == ["p1"]
