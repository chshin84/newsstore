import importlib, os
from newsstore import ssl_config

def test_home_uses_default_verify(monkeypatch):
    monkeypatch.setenv("APP_ENV", "home")
    assert ssl_config.get_verify() is True

def test_office_uses_ca_bundle(monkeypatch):
    monkeypatch.setenv("APP_ENV", "office")
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", "/etc/ssl/certs/ca-certificates.crt")
    assert ssl_config.get_verify() == "/etc/ssl/certs/ca-certificates.crt"

def test_make_client_has_browser_ua_and_timeout(monkeypatch):
    monkeypatch.setenv("APP_ENV", "home")
    c = ssl_config.make_client()
    assert "Mozilla" in c.headers["User-Agent"]
    c.close()
