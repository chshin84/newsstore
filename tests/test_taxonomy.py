from newsstore.enrich.taxonomy import load_taxonomy


def test_load_taxonomy(tmp_path):
    p = tmp_path / "tax.yaml"
    p.write_text("entities: [Fed, ECB]\ntopics: [rates, fx]\n", encoding="utf-8")
    tax = load_taxonomy(p)
    assert tax["entities"] == ["Fed", "ECB"]
    assert tax["topics"] == ["rates", "fx"]


def test_real_taxonomy_has_core_terms():
    tax = load_taxonomy("config/taxonomy.yaml")
    assert "Fed" in tax["entities"]
    assert "rates" in tax["topics"] and "crypto" in tax["topics"]


def test_load_taxonomy_failloud_on_empty(tmp_path):
    import pytest
    p = tmp_path / "empty.yaml"
    p.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError):          # 빈 어휘는 조용히 통과 X (FAIL-LOUD)
        load_taxonomy(p)
