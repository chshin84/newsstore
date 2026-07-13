import os
from pathlib import Path

import pytest

# Pin the working directory to the repo root so tests that read relative paths
# (config/feeds.yaml, tests/fixtures/...) resolve regardless of where pytest is
# invoked from.
os.chdir(Path(__file__).resolve().parent.parent)


@pytest.fixture
def fsclient():
    """Firestore 에뮬레이터에 붙은 실 google client. 테스트 간 컬렉션을 비운다.
    FIRESTORE_EMULATOR_HOST 미설정이면 skip(에뮬레이터 없이 단위테스트만 돌 때)."""
    if not os.environ.get("FIRESTORE_EMULATOR_HOST"):
        pytest.skip("Firestore emulator not running (set FIRESTORE_EMULATOR_HOST)")
    from google.cloud import firestore
    db = firestore.Client(project=os.environ.get("GOOGLE_CLOUD_PROJECT", "test"))
    for col in ("items", "feed_state", "meta", "prices", "fundamentals", "t"):
        for d in db.collection(col).stream():
            d.reference.delete()
    return db


@pytest.fixture
def store(fsclient):
    """에뮬레이터-backed FirestoreStore."""
    from newsstore.store.firestore_store import FirestoreStore
    return FirestoreStore(fsclient)
