from newsstore.radar import match


def test_latin_alias_word_boundary():
    assert match.find_alias("IREN", "IREN shares surge 10%") is not None
    assert match.find_alias("IREN", "SIRENS blared downtown") is None
    assert match.find_alias("IREN", "siren 소리가 났다") is None


def test_hangul_alias_allows_josa_but_blocks_leading_attach():
    assert match.find_alias("하이닉스", "하이닉스가 급등했다") is not None
    assert match.find_alias("하이닉스", "SK하이닉스가 발표") is None
    assert match.find_alias("SK하이닉스", "SK하이닉스가 발표") is not None


def test_match_evidence_positions():
    assert match.find_alias("코스피", "오늘 코스피지수는 하락") == ("코스피", 3)


def test_match_any_over_watchlist_aliases():
    aliases = ["SK하이닉스", "하이닉스", "SK hynix"]
    assert match.find_any(aliases, "SK hynix ADR debut") == ("SK hynix", 0)
    assert match.find_any(aliases, "무관한 제목") is None


def test_vocab_file_loads_and_derives_taxonomy():
    vocab = match.load_vocab("config/radar_vocab.yaml")
    assert "Fed" in vocab and "한국은행" in vocab
    assert "HBM" in vocab
