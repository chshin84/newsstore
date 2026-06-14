def test_set_meta_upserts(store):
    store.set_meta("sources", {"sources": ["A", "B"]})
    d = store.db.collection("meta").document("sources").get().to_dict()
    assert d == {"sources": ["A", "B"]}
    store.set_meta("sources", {"sources": ["C"]})   # 같은 키 덮어쓰기
    d = store.db.collection("meta").document("sources").get().to_dict()
    assert d == {"sources": ["C"]}
