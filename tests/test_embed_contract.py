"""임베딩 인프라 계약 가드(FAIL-LOUD) — 규칙·배선이 조용히 빠지는 드리프트를 터뜨린다."""
import pathlib
import re


def test_item_vectors_public_read_rule_declared():
    rules = pathlib.Path("firestore.rules").read_text(encoding="utf-8")
    assert re.search(r"match /item_vectors/\{id\}\s*\{\s*allow read: if true; "
                     r"allow write: if false;", rules), \
        "firestore.rules에 item_vectors 공개 read 규칙이 없다"


def test_gemini_client_sends_task_type_from_ssot():
    """task_type 미지정은 조용한 계약 공백이다 — 같은 문장도 타입에 따라 다른 벡터가 나오므로
    다운스트림이 쿼리를 맞출 수 없다. 실 SDK는 테스트 이미지에 없어(embed extra는 collect
    전용) 배선을 소스에서 가드한다."""
    from newsstore.contracts.embedding import EMBED_TASK_TYPE
    assert EMBED_TASK_TYPE, "EMBED_TASK_TYPE 상수가 비어 있다"
    src = pathlib.Path("src/newsstore/embed/gemini.py").read_text(encoding="utf-8")
    assert "EMBED_TASK_TYPE" in src, "gemini.py가 task_type SSOT 상수를 쓰지 않는다"
    assert re.search(r"task_type\s*=\s*EMBED_TASK_TYPE", src), \
        "embed 호출이 task_type을 SSOT 상수로 넘기지 않는다(리터럴 이중 정의 금지)"


def test_embed_extra_wired_into_prod_image():
    """스펙 재리뷰 critical: extra 선언만으로는 프로덕션에 설치되지 않는다 — 배선 3점 가드."""
    assert '"google-genai' in pathlib.Path("pyproject.toml").read_text(encoding="utf-8")
    dockerfile = pathlib.Path("infra/Dockerfile").read_text(encoding="utf-8")
    assert "INSTALL_EMBED" in dockerfile
    # ARG 선언만으로는 부족 — RUN의 EXTRAS 조립(실제 설치 경로)까지 있어야 한다.
    assert 'EXTRAS="${EXTRAS:+$EXTRAS,}embed"' in dockerfile
    cloudbuild = pathlib.Path("infra/cloudbuild.yaml").read_text(encoding="utf-8")
    assert "INSTALL_EMBED=true" in cloudbuild
    lock = pathlib.Path("infra/requirements.lock").read_text(encoding="utf-8")
    assert "google-genai==" in lock
