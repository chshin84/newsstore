"""프레임 패스 순수 로직 — validate·diff (fake LLM, 에뮬레이터 불요)."""
from newsstore.enrich.frames import validate_frame, frame_diff, FRAME_MAX_POLES

OLD = {"risks": [{"id": "r1", "text": "빅테크 capex 감속"}],
       "premiums": [{"id": "p1", "text": "HBM 수요"}], "watchpoints": []}


def test_validate_frame_schema_and_caps():
    raw = {"risks": [{"id": f"r{i}", "text": f"극{i}"} for i in range(FRAME_MAX_POLES + 2)],
           "premiums": [{"id": "p1", "text": "ok"}], "watchpoints": None}   # null 가드
    v = validate_frame(raw)
    assert len(v["risks"]) == FRAME_MAX_POLES            # 축당 상한 강제
    assert v["watchpoints"] == []                        # null → []
    assert all(p["id"] and p["text"] for p in v["risks"])


def test_validate_frame_rejects_garbage():
    assert validate_frame(None) is None
    assert validate_frame(["not", "dict"]) is None
    assert validate_frame({"risks": "문자열"}) is None    # 축이 리스트 아님 → 무효
    # 극에 id/text 없으면 그 극만 드롭(비파괴), 전부 빈 프레임도 유효(단극·무극 허용)
    v = validate_frame({"risks": [{"text": "id없음"}, {"id": "r1", "text": "ok"}],
                        "premiums": [], "watchpoints": []})
    assert [p["id"] for p in v["risks"]] == ["r1"]


def test_frame_diff_new_and_changed_only():
    new = {"risks": [{"id": "r1", "text": "빅테크 capex 감속(수정)"},   # 텍스트 변경
                     {"id": "r9", "text": "관세 재점화"}],              # 신규
           "premiums": [{"id": "p1", "text": "HBM 수요"}],             # 동일 유지
           "watchpoints": []}
    d = frame_diff(OLD, new)
    assert {p["id"] for p in d} == {"r1", "r9"}          # 유지 극(p1)은 diff 아님 → 리뷰 0대상
