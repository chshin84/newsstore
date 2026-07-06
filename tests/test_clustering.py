from newsstore.enrich.clustering import EventClusterer, cluster_articles
from newsstore.enrich.clustering_types import Article, Story


class _LLM:
    def __init__(self, verdict="DIFFERENT", boom=False):
        self.verdict, self.boom, self.calls = verdict, boom, 0

    def complete(self, prompt, *, timeout=30.0, model=None):
        self.calls += 1
        if self.boom:
            raise RuntimeError("down")
        return self.verdict


def _art(i, vec):
    return Article(id=i, title=f"t{i}", body="b", source="S", published_at="2026-06-29",
                   embedding=tuple(vec))


def test_assign_deterministic_join_identical():
    llm = _LLM()
    c = EventClusterer(embed=lambda t: [[0.0, 0.0]], llm=llm)
    s = Story(id="s1", title="x", centroid_sum=(1.0, 0.0))
    assert c.assign(_art("a", [1.0, 0.0]), [s]) == "s1" and llm.calls == 0


def test_assign_deterministic_new_orthogonal():
    llm = _LLM()
    c = EventClusterer(embed=lambda t: [[0.0, 0.0]], llm=llm)
    s = Story(id="s1", title="x", centroid_sum=(1.0, 0.0))
    assert c.assign(_art("a", [0.0, 1.0]), [s]) is None and llm.calls == 0


def test_assign_gray_band_same_joins():
    llm = _LLM("SAME")
    c = EventClusterer(embed=lambda t: [[0.0, 0.0]], llm=llm)
    s = Story(id="s1", title="x", centroid_sum=(1.0, 0.0))
    assert c.assign(_art("a", [0.83, 1.0]), [s]) == "s1" and llm.calls == 1


def test_assign_gray_band_llm_error_failsoft_new():
    llm = _LLM(boom=True)
    c = EventClusterer(embed=lambda t: [[0.0, 0.0]], llm=llm)
    s = Story(id="s1", title="x", centroid_sum=(1.0, 0.0))
    assert c.assign(_art("a", [0.83, 1.0]), [s]) is None


import logging


def _decision_lines(caplog):
    return [r.message for r in caplog.records if r.message.startswith("assign_decision")]


def test_assign_telemetry_logs_det_hi_without_changing_shape(caplog):
    # IB1: 결정론 합류 결정에 텔레메트리 1줄 발행. 반환 shape(str) 불변·LLM콜0.
    llm = _LLM()
    c = EventClusterer(embed=lambda t: [[0.0, 0.0]], llm=llm)
    s = Story(id="s1", title="x", centroid_sum=(1.0, 0.0))
    with caplog.at_level(logging.INFO, logger="newsstore.enrich.clustering"):
        result = c.assign(_art("a", [1.0, 0.0]), [s])
    assert result == "s1" and llm.calls == 0            # 판정·shape 불변
    lines = _decision_lines(caplog)
    assert len(lines) == 1 and "gate=det_hi" in lines[0] and "llm=na" in lines[0]
    assert "result=join" in lines[0] and "cands=1" in lines[0]


def test_assign_telemetry_logs_below_lo(caplog):
    c = EventClusterer(embed=lambda t: [[0.0, 0.0]], llm=_LLM())
    s = Story(id="s1", title="x", centroid_sum=(1.0, 0.0))
    with caplog.at_level(logging.INFO, logger="newsstore.enrich.clustering"):
        assert c.assign(_art("a", [0.0, 1.0]), [s]) is None
    (line,) = _decision_lines(caplog)
    assert "gate=below_lo" in line and "result=new" in line


def test_assign_telemetry_logs_no_candidate(caplog):
    c = EventClusterer(embed=lambda t: [[1.0, 0.0]], llm=_LLM())
    with caplog.at_level(logging.INFO, logger="newsstore.enrich.clustering"):
        assert c.assign(_art("a", [1.0, 0.0]), []) is None   # open_stories 없음
    (line,) = _decision_lines(caplog)
    assert "gate=no_cand" in line and "cands=0" in line and "result=new" in line


def test_assign_telemetry_logs_grayband_merge_and_split(caplog):
    s = Story(id="s1", title="x", centroid_sum=(1.0, 0.0))
    with caplog.at_level(logging.INFO, logger="newsstore.enrich.clustering"):
        c_same = EventClusterer(embed=lambda t: [[0.0, 0.0]], llm=_LLM("SAME"))
        assert c_same.assign(_art("a", [0.83, 1.0]), [s]) == "s1"
    merge_lines = [l for l in _decision_lines(caplog) if "llm=merge" in l]
    assert merge_lines and "gate=grayband" in merge_lines[0] and "result=join" in merge_lines[0]
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="newsstore.enrich.clustering"):
        c_diff = EventClusterer(embed=lambda t: [[0.0, 0.0]], llm=_LLM("DIFFERENT"))
        assert c_diff.assign(_art("a", [0.83, 1.0]), [s]) is None
    split_lines = [l for l in _decision_lines(caplog) if "gate=grayband" in l]
    assert split_lines and "llm=split" in split_lines[0] and "result=new" in split_lines[0]


def test_assign_telemetry_grayband_llm_error_marks_fallback(caplog):
    s = Story(id="s1", title="x", centroid_sum=(1.0, 0.0))
    c = EventClusterer(embed=lambda t: [[0.0, 0.0]], llm=_LLM(boom=True))
    with caplog.at_level(logging.INFO, logger="newsstore.enrich.clustering"):
        assert c.assign(_art("a", [0.83, 1.0]), [s]) is None
    grayband = [l for l in _decision_lines(caplog) if "gate=grayband" in l]
    assert grayband and "fallback=llm_error" in grayband[0] and "result=new" in grayband[0]


def test_assign_telemetry_grayband_no_llm_marks_no_llm(caplog):
    s = Story(id="s1", title="x", centroid_sum=(1.0, 0.0))
    c = EventClusterer(embed=lambda t: [[0.0, 0.0]])       # llm 미주입
    with caplog.at_level(logging.INFO, logger="newsstore.enrich.clustering"):
        assert c.assign(_art("a", [0.83, 1.0]), [s]) is None
    grayband = [l for l in _decision_lines(caplog) if "gate=grayband" in l]
    assert grayband and "llm=na" in grayband[0] and "fallback=no_llm" in grayband[0]


def test_assign_fallback_embed_input_is_title_plus_body():
    # 폴백 임베딩 입력도 정본 규칙(title+body[:500] — embedder.embed_text)을 따라야 한다.
    # 스토리 centroid는 title+body 벡터의 합이라 규칙이 다르면(과거 title-only 잔재)
    # 코사인이 체계적으로 어긋나 0.62/0.80 임계 판정이 왜곡된다.
    from newsstore.enrich.embedder import BODY_CAP
    captured = {}

    def embed(texts):
        captured["text"] = texts[0]
        return [[1.0, 0.0]]

    c = EventClusterer(embed=embed)
    art = Article(id="a", title="Title", body="B" * (BODY_CAP + 100),
                  source="S", published_at="2026-06-12T00:00:00Z")
    c.assign(art, [])
    assert captured["text"] == "Title " + "B" * BODY_CAP


def test_cluster_articles_merges_same_event():
    llm = _LLM()
    out = cluster_articles([_art("a", [1.0, 0.0]), _art("b", [1.0, 0.0])],
                           embed=lambda t: [[0.0, 0.0]] * len(t), llm=llm)
    assert out["a"] == out["b"]


def test_env_gray_band_default_override_and_failloud(monkeypatch):
    # #6: gray-band env 오버라이드 — 미설정=기본, 설정=그 값, 범위위반=FAIL-LOUD
    import pytest
    from newsstore.enrich.clustering import env_gray_band
    monkeypatch.delenv("NEWSSTORE_GRAY_BAND_LO", raising=False)
    monkeypatch.delenv("NEWSSTORE_GRAY_BAND_HI", raising=False)
    assert env_gray_band() == (0.62, 0.80)   # #6 측정 반영 기본값
    monkeypatch.setenv("NEWSSTORE_GRAY_BAND_LO", "0.50")
    monkeypatch.setenv("NEWSSTORE_GRAY_BAND_HI", "0.80")
    assert env_gray_band() == (0.50, 0.80)
    monkeypatch.setenv("NEWSSTORE_GRAY_BAND_LO", "0.90")   # lo>hi → 위반
    with pytest.raises(ValueError):
        env_gray_band()
