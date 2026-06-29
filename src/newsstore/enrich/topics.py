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
