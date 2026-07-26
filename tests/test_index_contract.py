"""인덱스 계약 가드 (에뮬레이터 맹점 보완).

에뮬레이터는 복합 인덱스를 무시 → '쿼리는 통과하나 실 Firestore는 인덱스 요구'를 못 잡는다.
코드가 쓰는 복합쿼리가 firestore.indexes.json에 선언됐는지 fail-loud로 단언(원칙3).
"""
import json
import pathlib

# 코드의 복합쿼리(where+order_by/배열) ↔ 필요한 복합 인덱스 (collectionGroup, (fields...))
# 수집 전용(data-only): 남는 복합쿼리는 UI가 소스로 거르는 두 가지(뉴스 목록과 상태 탭)뿐이다.
REQUIRED = [
    ("items", ("source", "published_at")),     # UI 소스 필터: where(source==X).order_by(published_at desc)
    ("items", ("source", "fetched_at")),       # UI 상태 탭: where(source==X).order_by(fetched_at desc)
]


def test_required_composite_indexes_declared():
    idx = json.loads(pathlib.Path("firestore.indexes.json").read_text(encoding="utf-8"))
    have = {(i["collectionGroup"], tuple(f["fieldPath"] for f in i["fields"]))
            for i in idx["indexes"]}
    missing = [r for r in REQUIRED if r not in have]
    assert not missing, f"firestore.indexes.json에 누락된 복합 인덱스: {missing}"
