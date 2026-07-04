"""topics.yaml 렌즈 SSOT 로더 + registry. 분류·UI·정렬이 전부 여기서 도출."""
from __future__ import annotations
import functools
import yaml

_TYPES = {"standing", "development", "sector", "watch", "risk"}


@functools.lru_cache(maxsize=4)
def load_topics(path: str = "config/topics.yaml") -> dict:
    t = yaml.safe_load(open(path, encoding="utf-8"))
    bad = [l["id"] for l in t["lenses"] if l["type"] not in _TYPES]
    if bad:                       # FAIL-LOUD: 미지정 type 즉시 폭발
        raise ValueError(f"topics.yaml unknown type for: {bad}")
    return t


def valid_ids(t: dict) -> set[str]:
    return {l["id"] for l in t["lenses"]}


def lens_type(t: dict, lens_id: str) -> str:
    for l in t["lenses"]:
        if l["id"] == lens_id:
            return l["type"]
    raise KeyError(f"unknown lens id: {lens_id}")


def lens_labels(t: dict) -> dict[str, str]:
    """렌즈 id → 한국어 라벨(UI 표기용, SSOT). label.ko 없으면 id 폴백."""
    out = {}
    for l in t["lenses"]:
        lab = l.get("label") if isinstance(l.get("label"), dict) else {}
        out[l["id"]] = (lab.get("ko") if lab else None) or l["id"]
    return out


def report_lens_ids(t: dict) -> list[str]:
    """리포트 대상 렌즈 id(등장 순서) = 금융 자산(type=standing)만(사용자 결정 2026-07-04).
    리스크(type=risk)·경제·정치·정책(type=development)은 리포트로 만들지 않고, 그 뉴스는
    context_lens_ids 풀로 자산 리포트(백드롭·시장프레임)에 녹인다(#2). watch·sector도 제외."""
    return [l["id"] for l in t["lenses"] if l["type"] == "standing"]


def context_lens_ids(t: dict) -> list[str]:
    """시장프레임·백드롭 입력 풀 = watch·sector 외 렌즈 전부(자산 + 리스크·경제·정치·정책).
    리포트는 안 만들지만 비자산 뉴스를 자산 리포트로 녹이려면 이 풀에 남아야 한다(#2 fold-in)."""
    return [l["id"] for l in t["lenses"] if l["type"] not in ("watch", "sector")]


def report_groups(t: dict) -> dict[str, list[str]]:
    """report_group → [lens_id...] (yaml 등장 순서 보존). UI 섹션 앵커 도출(SSOT).
    자산(standing) 렌즈만 — 리포트 대상과 일치(report_lens_ids). report_group 누락 시 KeyError."""
    out: dict[str, list[str]] = {}
    for l in t["lenses"]:
        if l["type"] != "standing":
            continue
        out.setdefault(l["report_group"], []).append(l["id"])
    return out
