"""임베딩 인프라 계약 가드(FAIL-LOUD) — 규칙·배선이 조용히 빠지는 드리프트를 터뜨린다."""
import pathlib
import re


def test_item_vectors_public_read_rule_declared():
    rules = pathlib.Path("firestore.rules").read_text(encoding="utf-8")
    assert re.search(r"match /item_vectors/\{id\}\s*\{\s*allow read: if true; "
                     r"allow write: if false;", rules), \
        "firestore.rules에 item_vectors 공개 read 규칙이 없다"


def test_embed_extra_wired_into_prod_image():
    """스펙 재리뷰 critical: extra 선언만으로는 프로덕션에 설치되지 않는다 — 배선 3점 가드."""
    assert '"google-genai' in pathlib.Path("pyproject.toml").read_text(encoding="utf-8")
    dockerfile = pathlib.Path("infra/Dockerfile").read_text(encoding="utf-8")
    assert "INSTALL_EMBED" in dockerfile
    cloudbuild = pathlib.Path("infra/cloudbuild.yaml").read_text(encoding="utf-8")
    assert "INSTALL_EMBED=true" in cloudbuild
    lock = pathlib.Path("infra/requirements.lock").read_text(encoding="utf-8")
    assert "google-genai==" in lock
