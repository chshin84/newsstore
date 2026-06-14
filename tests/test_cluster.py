import pytest
from newsstore.enrich.cluster import cosine, centroid
from newsstore.contracts.vectors import add_vectors

def test_add_vectors_elementwise():
    assert add_vectors([1.0, 2.0], [3.0, 4.0]) == [4.0, 6.0]

def test_add_vectors_dim_mismatch_raises():
    # centroid_sum += vec 의 무음 절단 방지 (원칙3)
    with pytest.raises(ValueError):
        add_vectors([1.0, 2.0, 3.0], [1.0, 2.0])

def test_cosine_identical():
    assert cosine([1, 0, 0], [1, 0, 0]) == 1.0

def test_cosine_orthogonal():
    assert cosine([1, 0], [0, 1]) == 0.0

def test_cosine_similar_high():
    assert cosine([1, 1, 0], [1, 0.9, 0]) > 0.9

def test_cosine_zero_vector_safe():
    assert cosine([0, 0], [1, 1]) == 0.0

def test_cosine_dim_mismatch_raises():
    # fail-loud: 차원이 다르면 조용히 zip 절단하지 말고 터뜨린다 (원칙3)
    with pytest.raises(ValueError):
        cosine([1, 0, 0], [1, 0])

def test_centroid_mean():
    assert centroid([2, 4, 6], 2) == [1.0, 2.0, 3.0]

def test_centroid_zero_count_raises():
    with pytest.raises(ValueError):
        centroid([1, 2, 3], 0)
