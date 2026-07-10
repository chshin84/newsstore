"""원장 3종 검증기 — gates.yaml·journal.jsonl·frames.json(v2-local).
결정⑨a: 판정·채점의 주체와 근거를 스키마가 강제한다 — Claude의 재량에 의존하지 않는다."""
from __future__ import annotations

import datetime as dt
import json

import yaml

GATE_STATUSES = ("pending", "confirmed", "refuted", "void")
AXES = ("risks", "premiums", "watchpoints")
MAX_ACTIVE_POLES = 5
BASIS_KINDS = ("price", "flow", "event")


def load_gates(path: str = "radar/gates.yaml") -> list[dict]:
    with open(path, encoding="utf-8") as f:
        gates = (yaml.safe_load(f) or {}).get("gates") or []
    validate_gates(gates)
    return gates


def validate_gates(gates: list[dict]) -> None:
    seen: set[str] = set()
    for g in gates:
        for k in ("id", "date", "test", "on_confirm", "on_refute", "status"):
            if not g.get(k):
                raise ValueError(f"gate {g.get('id')!r}: 필수 필드 {k} 결측")
        if g["id"] in seen:
            raise ValueError(f"gate id 중복: {g['id']}")
        seen.add(g["id"])
        if g["status"] not in GATE_STATUSES:
            raise ValueError(f"gate {g['id']}: status {g['status']!r}는 {GATE_STATUSES} 밖")
        if g["status"] != "pending" and g.get("judged_by") != "user":
            raise ValueError(f"gate {g['id']}: 상태 전이엔 judged_by: user 필수(결정⑨a)")
        if "targets" in g and not isinstance(g["targets"], list):
            raise ValueError(f"gate {g['id']}: targets는 watchlist id 리스트여야 한다")


def overdue_pending(gates: list[dict], *, today: str, grace_days: int = 3) -> list[dict]:
    t = dt.date.fromisoformat(today)
    return [g for g in gates if g["status"] == "pending"
            and dt.date.fromisoformat(str(g["date"])) + dt.timedelta(days=grace_days) < t]


def due_around(gates: list[dict], *, today: str, window_days: int = 2) -> list[dict]:
    t = dt.date.fromisoformat(today)
    return [g for g in gates if g["status"] == "pending"
            and abs((dt.date.fromisoformat(str(g["date"])) - t).days) <= window_days]


def gates_for_target(gates: list[dict], target_id: str) -> list[dict]:
    return [g for g in gates if target_id in (g.get("targets") or [])]


def _validate_entry(e: dict) -> None:
    if e.get("type") == "plan":
        for k in ("id", "date", "target", "thesis", "band", "invalidation", "by"):
            if not e.get(k):
                raise ValueError(f"journal plan: 필수 필드 {k} 결측 — 시한 없는 판단은 채점 불가")
    elif e.get("type") == "review":
        for k in ("plan_id", "date"):
            if not e.get(k):
                raise ValueError(f"journal review: 필수 필드 {k} 결측")
        vb = e.get("verdict_basis")
        if not isinstance(vb, dict):
            raise ValueError("journal review: verdict_basis는 구조화 필드여야 한다(자유 문자열 금지 — 결정⑨a)")
        if vb.get("kind") in BASIS_KINDS:
            for k in ("metric", "value", "source"):
                if k not in vb:
                    raise ValueError(f"journal review: verdict_basis.{k} 결측")
        elif not e.get("user_approved"):
            raise ValueError("journal review: 결정론 kind(price|flow|event)가 아니면 user_approved 필수")
    else:
        raise ValueError(f"journal: 알 수 없는 type {e.get('type')!r}")


def append_journal(path: str, entry: dict) -> None:
    _validate_entry(entry)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_journal(path: str = "journal/journal.jsonl") -> list[dict]:
    try:
        with open(path, encoding="utf-8") as f:
            entries = [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []
    for e in entries:
        _validate_entry(e)
    return entries


def active_plans(entries: list[dict], *, today: str) -> list[dict]:
    return [e for e in entries if e.get("type") == "plan" and str(e.get("by", "")) >= today]


def drop_invalid_poles(frame: dict) -> dict:
    return {ax: [p for p in frame.get(ax, []) if p.get("id") and p.get("label")]
            for ax in AXES}


def validate_frames(frames: dict, *, gate_ids: set[str]) -> None:
    for lens, frame in frames.items():
        missing = [ax for ax in AXES if ax not in frame]
        if missing:
            raise ValueError(f"frames[{lens}]: 축 결측 {missing} — 축 3종 필수")
        for ax in AXES:
            poles = frame[ax]
            active = [p for p in poles if p.get("status", "active") == "active"]
            if len(active) > MAX_ACTIVE_POLES:
                raise ValueError(f"frames[{lens}].{ax}: active 극 {len(active)}개 — 상한 {MAX_ACTIVE_POLES}")
            for p in poles:
                gid = p.get("gate_id")
                if gid and gid not in gate_ids:
                    raise ValueError(f"frames[{lens}].{ax}.{p.get('id')}: gate_id {gid!r} 미실재")


def load_frames(path: str = "radar/frames.json", *, gate_ids: set[str]) -> dict:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    frames = raw.get("lenses") or {}
    validate_frames(frames, gate_ids=gate_ids)
    return frames
