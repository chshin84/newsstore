"""사가 분리 측정 스크립트(A3) 순수 로직 — 후보 축소·차원 단언·게이트. fake 주입으로 결정론.

scripts/는 패키지가 아니라 importlib로 파일에서 직접 로드한다(무거운 import는 main() 내부
지연이라 로드 자체는 google 미설치서도 성공)."""
import importlib.util
import pathlib
from datetime import datetime, timedelta, timezone

import pytest

_PATH = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "saga_split_audit.py"
_spec = importlib.util.spec_from_file_location("saga_split_audit", _PATH)
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)

NOW = datetime(2026, 7, 5, 7, 0, tzinfo=timezone.utc)
DIM = audit.EMBED_DIM


def _vec(seed):
    """DIM 길이의 결정론 벡터 — 앞 두 성분으로 방향, 나머지 0."""
    x, y = seed
    return [float(x), float(y)] + [0.0] * (DIM - 2)


def _story(sid, *, entities=(), title="", lenses=("fx",), hours_ago=1, vec=(1.0, 0.0)):
    return {"id": sid, "title": title, "summary": "", "entities": list(entities),
            "lenses": list(lenses), "last_seen": NOW - timedelta(hours=hours_ago),
            "developments": [], "centroid_sum": _vec(vec)}


# ── 패리티 fail-loud(768) ──
def test_cosine_asserts_dimension_parity():
    good = _vec((1.0, 0.0))
    assert audit.cosine(good, good) == pytest.approx(1.0)
    with pytest.raises(ValueError):
        audit.cosine([1.0, 0.0, 0.0], good)          # 차원 불일치 → fail-loud(zip 절단 방지)


def test_cosine_orthogonal_and_opposite():
    assert audit.cosine(_vec((1.0, 0.0)), _vec((0.0, 1.0))) == pytest.approx(0.0)
    assert audit.cosine(_vec((1.0, 0.0)), _vec((-1.0, 0.0))) == pytest.approx(-1.0)


# ── 개체 공유 ──
def test_share_dominant_entity_uses_entities_then_title():
    assert audit.share_dominant_entity(
        _story("a", entities=["BOJ"]), _story("b", entities=["BOJ", "Fed"]))
    assert not audit.share_dominant_entity(
        _story("a", entities=["BOJ"]), _story("b", entities=["ECB"]))
    # entities 없으면 제목 키워드 폴백(불용어 제외)
    assert audit.share_dominant_entity(
        _story("a", title="엔화 초읽기"), _story("b", title="엔화 반등"))
    assert not audit.share_dominant_entity(
        _story("a", title="엔화 초읽기"), _story("b", title="반도체 수요"))


# ── 시간 근접 ──
def test_time_proximate_within_and_outside_window():
    w = timedelta(hours=48)
    assert audit.time_proximate(_story("a", hours_ago=1), _story("b", hours_ago=10), window=w)
    assert not audit.time_proximate(_story("a", hours_ago=1), _story("b", hours_ago=100), window=w)


# ── 후보 축소(결정론) ──
def test_candidate_pairs_requires_all_three_conjuncts():
    w = timedelta(hours=48)
    # 같은 개체 + 시간 근접 + 코사인 높음 → 후보
    same = [_story("s1", entities=["엔화"], vec=(1.0, 0.0)),
            _story("s2", entities=["엔화"], vec=(1.0, 0.01))]
    assert [(p["a"], p["b"]) for p in audit.candidate_pairs(same, window=w)] == [("s1", "s2")]
    # 개체 다름 → 후보 아님
    diff_ent = [_story("s1", entities=["엔화"]), _story("s2", entities=["원화"])]
    assert audit.candidate_pairs(diff_ent, window=w) == []
    # 시간 멀음 → 후보 아님
    far = [_story("s1", entities=["엔화"], hours_ago=1),
           _story("s2", entities=["엔화"], hours_ago=200)]
    assert audit.candidate_pairs(far, window=w) == []


def test_candidate_pairs_min_cos_floor_filters():
    w = timedelta(hours=48)
    orth = [_story("s1", entities=["엔화"], vec=(1.0, 0.0)),
            _story("s2", entities=["엔화"], vec=(0.0, 1.0))]        # 코사인 0
    assert audit.candidate_pairs(orth, window=w, min_cos=0.5) == []  # floor로 제외
    assert len(audit.candidate_pairs(orth, window=w, min_cos=0.0)) == 1  # floor 0 → 남김


def test_candidate_pairs_sorted_by_cosine_desc():
    w = timedelta(hours=48)
    stories = [_story("s1", entities=["e"], vec=(1.0, 0.0)),
               _story("s2", entities=["e"], vec=(1.0, 0.05)),   # s1과 가까움(높은 코사인)
               _story("s3", entities=["e"], vec=(1.0, 1.0))]    # s1과 45도(낮은 코사인)
    pairs = audit.candidate_pairs(stories, window=w)
    coses = [p["cosine"] for p in pairs]
    assert coses == sorted(coses, reverse=True)                  # 내림차순


# ── 게이트(정량 처방) ──
def _cands(coses):
    return [{"a": f"a{i}", "b": f"b{i}", "cosine": c, "lenses": ["fx"]}
            for i, c in enumerate(coses)]


def test_prescribe_cluster_recal_when_median_at_or_above_threshold():
    v = audit.prescribe(n_stories=10, candidates=_cands([0.66, 0.70, 0.72]),
                        merge_lo=0.62, merge_hi=0.80)
    assert v["prescription"] == "cluster_recal"


def test_prescribe_llm_saga_when_median_clearly_below_threshold():
    v = audit.prescribe(n_stories=10, candidates=_cands([0.30, 0.35, 0.40]),
                        merge_lo=0.62, merge_hi=0.80)
    assert v["prescription"] == "llm_saga"           # 중앙값 0.35 < 0.62−0.1


def test_prescribe_saga_unnecessary_when_split_rate_negligible():
    v = audit.prescribe(n_stories=100, candidates=_cands([0.90]),   # 1/100 = 1% < 5%
                        merge_lo=0.62, merge_hi=0.80)
    assert v["prescription"] == "saga_unnecessary"


def test_prescribe_inconclusive_between():
    v = audit.prescribe(n_stories=10, candidates=_cands([0.55, 0.58, 0.60]),
                        merge_lo=0.62, merge_hi=0.80)
    assert v["prescription"] == "inconclusive"       # 0.58: 임계 아래지만 −0.1 밖은 아님


# ── 오프라인 LLM 라벨(선택·주입 fake) ──
def test_llm_same_saga_labels_uses_injected_fake():
    stories = [_story("s1", entities=["엔화"]), _story("s2", entities=["엔화"]),
               _story("s3", entities=["엔화"])]
    cands = [{"a": "s1", "b": "s2", "cosine": 0.7, "lenses": ["fx"]},
             {"a": "s1", "b": "s3", "cosine": 0.5, "lenses": ["fx"]}]

    class _FakeLLM:
        def complete(self, prompt, **kw):
            return "SAME 두 스토리는 같은 사가" if "s2" not in prompt else "DIFFERENT"

    labels = audit.llm_same_saga_labels(cands, stories, _FakeLLM())
    # 프롬프트에 s2 제목이 없으므로(제목 빈 문자열) 위 fake는 항상 SAME 분기가 아님 — 계약만 확인
    assert set(labels.keys()) == {("s1", "s2"), ("s1", "s3")}
    assert all(isinstance(v, bool) for v in labels.values())


def test_llm_labels_none_guard_on_empty_response():
    stories = [_story("s1", entities=["e"]), _story("s2", entities=["e"])]
    cands = [{"a": "s1", "b": "s2", "cosine": 0.7, "lenses": []}]

    class _NoneLLM:
        def complete(self, prompt, **kw):
            return None                              # 실 SDK 빈 응답 계약

    labels = audit.llm_same_saga_labels(cands, stories, _NoneLLM())
    assert labels[("s1", "s2")] is False             # None 가드 → DIFFERENT


# ── audit 통합(순수) + 포맷 ──
def test_audit_and_format_smoke():
    w = timedelta(hours=48)
    stories = [_story("s1", entities=["엔화"], vec=(1.0, 0.0)),
               _story("s2", entities=["엔화"], vec=(1.0, 0.02)),
               _story("s3", entities=["원화"], vec=(0.0, 1.0))]
    result = audit.audit(stories, window=w, merge_lo=0.62, merge_hi=0.80)
    assert result["n_stories"] == 3 and result["n_candidates"] == 1
    text = audit.format_report(result)
    assert "사가 분리 측정" in text and "처방" in text
