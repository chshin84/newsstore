"""LLM usage별 모델 지정(config/models.yaml) — SSOT·드리프트 가드·fail-loud 계약."""
import re
from pathlib import Path

import pytest

from newsstore.enrich import model_config
from newsstore.enrich.model_config import USAGES, load_models, model_for

REPO = Path(__file__).resolve().parents[1]
REAL_YAML = str(REPO / "config" / "models.yaml")


def _fresh():
    load_models.cache_clear()


def test_real_yaml_covers_every_usage():
    """레지스트리 테스트: 실제 yaml이 모든 usage를 비어있지 않은 모델명으로 지정."""
    _fresh()
    models = load_models(REAL_YAML)
    assert set(models) == set(USAGES)
    for usage, model in models.items():
        assert isinstance(model, str) and model.strip(), usage


def test_unknown_usage_fails_loud():
    _fresh()
    with pytest.raises(ValueError, match="usage"):
        model_for("nonexistent_usage", path=REAL_YAML)


def test_yaml_key_drift_fails_loud(tmp_path):
    """yaml 키 누락/잉여 = 기동 시점 에러(조용한 폴백 금지)."""
    _fresh()
    missing = tmp_path / "missing.yaml"
    missing.write_text("usages:\n  summary: m\n", encoding="utf-8")
    with pytest.raises(ValueError, match="드리프트"):
        load_models(str(missing))
    _fresh()
    lines = "".join(f"  {u}: m\n" for u in USAGES)
    extra = tmp_path / "extra.yaml"
    extra.write_text("usages:\n" + lines + "  ghost_usage: m\n", encoding="utf-8")
    with pytest.raises(ValueError, match="드리프트"):
        load_models(str(extra))


def test_gemini_model_env_overrides_all(monkeypatch):
    """GEMINI_MODEL env = 전역 비상 오버라이드(재빌드 없이 잡 env로 적용)."""
    _fresh()
    monkeypatch.setenv("GEMINI_MODEL", "override-model")
    assert model_for("summary", path=REAL_YAML) == "override-model"
    assert model_for("report_section", path=REAL_YAML) == "override-model"
    monkeypatch.delenv("GEMINI_MODEL")
    _fresh()
    assert model_for("summary", path=REAL_YAML) != "override-model"


def test_code_literals_match_registry():
    """드리프트 가드: src의 model_for("...") 리터럴 집합 == USAGES.
    (새 콜 사이트 추가 시 yaml·레지스트리 동시 갱신을 강제 — 카운트는 스스로 센다.)"""
    src = REPO / "src" / "newsstore"
    found = set()
    for py in src.rglob("*.py"):
        found |= set(re.findall(r'model_for\(\s*"([a-z_]+)"', py.read_text(encoding="utf-8")))
    assert found == set(USAGES), f"코드 사용 키와 레지스트리 불일치: 코드에만={found - USAGES} 레지스트리에만={USAGES - found}"


def test_worker_low_reviewer_high_policy():
    """정책 가드(2026-07-04 사용자 결정): 리뷰어·리포트 전 과정은 워커(summary)와
    다른(상위) 모델이어야 한다 — 실수로 전부 같은 모델로 되돌리면 터진다."""
    _fresh()
    models = load_models(REAL_YAML)
    worker = models["summary"]
    for usage in ("frame_gen", "frame_review", "report_backdrop",
                  "report_section", "report_review"):
        assert models[usage] != worker, f"{usage}는 워커 모델과 달라야 함(추론/리뷰어=상위)"
