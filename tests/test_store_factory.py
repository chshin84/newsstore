import pytest
from newsstore.store.factory import make_store
from newsstore.store.sqlite_store import SqliteStore

def test_default_is_sqlite(tmp_path, monkeypatch):
    monkeypatch.delenv("NEWSSTORE_BACKEND", raising=False)
    s = make_store(db_path=str(tmp_path / "db.sqlite"))
    assert isinstance(s, SqliteStore)

def test_explicit_sqlite(tmp_path):
    s = make_store("sqlite", db_path=str(tmp_path / "db.sqlite"))
    assert isinstance(s, SqliteStore)

def test_env_var_selects_backend(tmp_path, monkeypatch):
    monkeypatch.setenv("NEWSSTORE_BACKEND", "sqlite")
    s = make_store(db_path=str(tmp_path / "db.sqlite"))
    assert isinstance(s, SqliteStore)

def test_unknown_backend_raises():
    with pytest.raises(ValueError):
        make_store("redis")
