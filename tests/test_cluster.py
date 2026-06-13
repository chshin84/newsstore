from newsstore.enrich.cluster import cosine

def test_cosine_identical():
    assert cosine([1, 0, 0], [1, 0, 0]) == 1.0

def test_cosine_orthogonal():
    assert cosine([1, 0], [0, 1]) == 0.0

def test_cosine_similar_high():
    assert cosine([1, 1, 0], [1, 0.9, 0]) > 0.9

def test_cosine_zero_vector_safe():
    assert cosine([0, 0], [1, 1]) == 0.0
