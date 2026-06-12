from __future__ import annotations
import os
from .sqlite_store import SqliteStore


def make_store(backend: str | None = None, *,
               db_path: str = "data/newsstore.db",
               project: str | None = None):
    """Select a Store backend. `backend` arg overrides $NEWSSTORE_BACKEND
    (default 'sqlite'). The firestore branch lazy-imports google so sqlite/test
    runs never need the cloud SDK."""
    backend = (backend or os.environ.get("NEWSSTORE_BACKEND", "sqlite")).lower()
    if backend == "sqlite":
        return SqliteStore(db_path)
    if backend == "firestore":
        from google.cloud import firestore
        from .firestore_store import FirestoreStore
        client = firestore.Client(project=project or os.environ.get("GOOGLE_CLOUD_PROJECT"))
        return FirestoreStore(client)
    raise ValueError(f"unknown NEWSSTORE_BACKEND: {backend!r}")
