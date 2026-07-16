"""run_collect 임베딩 배선 — 키 부재 fail-loud(대기분 있을 때만) + 수집 보존.

에뮬레이터에 붙어 main()을 통째로 돌린다(피드 0개 yaml — 수집은 no-op).
"""
from datetime import datetime, timezone
from newsstore.contracts.models import RawItem
from newsstore.entrypoints.run_collect import main

NOW = datetime(2026, 7, 16, 7, 0, tzinfo=timezone.utc)


def _feeds_yaml(tmp_path):
    p = tmp_path / "feeds.yaml"
    p.write_text("feeds: []\n", encoding="utf-8")
    return str(p)


def test_missing_key_with_pending_exits_1(store, tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    store.upsert_items([RawItem(id="p1", feed_id="f", source="S", url="https://e/p1",
                                title="Fed news", body="b", fetched_at=NOW)])
    assert main(["--feeds", _feeds_yaml(tmp_path)]) == 1


def test_missing_key_without_pending_exits_0(store, tmp_path, monkeypatch):
    """키 없는 로컬 수집 스모크를 깨지 않는다 — 대기 0건이면 경고 후 정상 종료."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert main(["--feeds", _feeds_yaml(tmp_path)]) == 0


def test_embed_wholesale_failure_preserves_collection_and_exits_1(store, tmp_path, monkeypatch):
    """패스 전체 실패(더미 키 → 클라이언트 생성/인증 실패)여도 수집 결과는 저장돼 있다."""
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-invalid-key")
    store.upsert_items([RawItem(id="p2", feed_id="f", source="S", url="https://e/p2",
                                title="Fed news 2", body="b", fetched_at=NOW)])
    assert main(["--feeds", _feeds_yaml(tmp_path)]) == 1
    assert store.db.collection("items").document("p2").get().exists   # 수집 보존
    d = store.db.collection("items").document("p2").get().to_dict()
    assert d["embed_pending"] is True                                 # 플래그 보존(재시도 가능)


def test_feed_failure_rate_exits_1_even_without_embed_issues(store, tmp_path, monkeypatch):
    """합성의 피드 축 — 임베딩이 무사(키 없음·대기 0건)해도 피드 실패율 초과면 exit 1."""
    import newsstore.entrypoints.run_collect as rc
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(rc, "collect_once", lambda *a, **k: {"f1": -1})   # 전 피드 실패 주입
    assert rc.main(["--feeds", _feeds_yaml(tmp_path)]) == 1
