from newsstore.enrich.cluster import cosine, centroid, assign

def test_cosine_identical():
    assert cosine([1, 0, 0], [1, 0, 0]) == 1.0

def test_cosine_orthogonal():
    assert cosine([1, 0], [0, 1]) == 0.0

def test_cosine_similar_high():
    assert cosine([1, 1, 0], [1, 0.9, 0]) > 0.9

def test_cosine_zero_vector_safe():
    assert cosine([0, 0], [1, 1]) == 0.0

def test_centroid_mean():
    assert centroid([2, 4, 6], 2) == [1.0, 2.0, 3.0]

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
