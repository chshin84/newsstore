from __future__ import annotations
import os


def make_store(backend: str | None = None, *, db_path: str | None = None,
               project: str | None = None):
    """Firestore Store. 로컬/테스트는 FIRESTORE_EMULATOR_HOST로 에뮬레이터에 붙는다
    (sqlite 백엔드는 제거됨 — store 구현 단일화). backend/db_path 인자는 하위호환용(무시)."""
    from google.cloud import firestore
    from .firestore_store import FirestoreStore
    client = firestore.Client(project=project or os.environ.get("GOOGLE_CLOUD_PROJECT"))
    return FirestoreStore(client)
