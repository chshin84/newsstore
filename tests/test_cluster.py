import pytest
from newsstore.enrich.cluster import cosine, centroid, assign
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

def test_assign_joins_most_similar_open_story():
    stories = [{"id": "s1", "centroid": [1, 0, 0]}, {"id": "s2", "centroid": [0, 1, 0]}]
    assert assign([0.99, 0.01, 0], stories) == "s1"

def test_assign_new_story_when_dissimilar():
    stories = [{"id": "s1", "centroid": [1, 0, 0]}]
    assert assign([0, 1, 0], stories) is None

def test_assign_respects_threshold():
    stories = [{"id": "s1", "centroid": [1, 0, 0]}]
    assert assign([0.9, 0.1, 0], stories, threshold=0.999) is None
    assert assign([0.9, 0.1, 0], stories, threshold=0.5) == "s1"

def test_assign_empty_stories_is_new():
    assert assign([1, 0, 0], []) is None

def test_assign_threshold_inclusive_boundary():
    stories = [{"id": "s1", "centroid": [1, 0, 0]}]
    # cosine([1,0,0],[1,0,0]) == 1.0, threshold 1.0 → 경계 포함(>=)이라 합류
    assert assign([1, 0, 0], stories, threshold=1.0) == "s1"
