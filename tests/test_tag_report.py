from newsstore.enrich.tag_report import tag_coverage


def test_tag_coverage_counts_and_untagged_rate():
    items = [["aapl", "tech"], [], ["aapl"], ["fed", "tech"]]
    r = tag_coverage(items)
    assert r["total"] == 4 and r["untagged"] == 1 and r["untagged_rate"] == 0.25
    assert dict(r["tag_freq"])["aapl"] == 2 and dict(r["tag_freq"])["tech"] == 2
    assert "out_of_vocab" not in r          # vocab 미지정 → 키 없음


def test_tag_coverage_out_of_vocab():
    items = [["aapl", "weirdtag"], ["fed"]]
    r = tag_coverage(items, vocab={"aapl", "fed"})
    assert r["out_of_vocab"] == [("weirdtag", 1)]   # 통제 어휘 밖만


def test_tag_coverage_empty():
    r = tag_coverage([])
    assert r["total"] == 0 and r["untagged_rate"] == 0.0 and r["tag_freq"] == []
