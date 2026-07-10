"""LLM 사용시점(usage)별 모델 지정 로더 — SSOT는 config/models.yaml.

방침(2026-07-04 사용자): 워커(결정론 비교·분류)는 싼 모델, 추론(프레임·리포트 합성)과
리뷰어는 상위 모델. 어느 콜이 어느 모델을 쓰는지는 전부 yaml에서 도출(코드 하드코딩 금지).

계약(FAIL-LOUD):
- yaml 키 집합 == USAGES 정확히 일치(누락/잉여 = 로드 시 ValueError — 드리프트 즉사).
- 미등록 usage 조회 = ValueError(조용한 기본값 폴백 금지).
- env GEMINI_MODEL = 전역 비상 오버라이드(모든 usage에 우선; 재빌드 없이 잡 env로 적용).
"""
from __future__ import annotations
import logging
import os
from functools import lru_cache

import yaml

log = logging.getLogger("newsstore.enrich.model_config")

DEFAULT_PATH = "config/models.yaml"

# 코드가 아는 LLM 사용시점 전체(레지스트리). 콜 사이트의 model_for("...") 리터럴과
# 이 집합의 일치는 tests/test_model_config.py가 grep으로 강제한다.
USAGES = frozenset({
    "cluster_judge", "summary", "lenses", "score", "article", "tag",
    "frame_gen", "frame_review", "report_backdrop", "report_section", "report_review",
})


@lru_cache(maxsize=None)
def load_models(path: str = DEFAULT_PATH) -> dict[str, str]:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    usages = raw.get("usages")
    if not isinstance(usages, dict):
        raise ValueError(f"{path}: 최상위 'usages' 맵이 필요하다")
    keys = set(usages)
    missing, extra = USAGES - keys, keys - USAGES
    if missing or extra:
        raise ValueError(
            f"{path} usage 키 드리프트 — 누락={sorted(missing)} 잉여={sorted(extra)} "
            "(코드 레지스트리 model_config.USAGES와 일치해야 함)")
    bad = [k for k, v in usages.items() if not (isinstance(v, str) and v.strip())]
    if bad:
        raise ValueError(f"{path}: 모델명이 비어있는 usage {sorted(bad)}")
    models = {k: v.strip() for k, v in usages.items()}
    log.info("LLM model config loaded (%s): %s", path,
             ", ".join(f"{k}={v}" for k, v in sorted(models.items())))
    return models


def model_for(usage: str, path: str = DEFAULT_PATH) -> str:
    """usage의 모델명. env GEMINI_MODEL이 있으면 전역 우선(비상 레버)."""
    override = os.environ.get("GEMINI_MODEL")
    if override:
        return override
    models = load_models(path)
    if usage not in models:
        raise ValueError(f"미등록 LLM usage: {usage!r} — config/models.yaml·USAGES에 등록하라")
    return models[usage]
