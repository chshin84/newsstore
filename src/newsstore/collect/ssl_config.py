import os
import httpx

from .fetcher import USER_AGENT      # UA SSOT — 복제 금지(fetcher가 단일 출처)

def get_verify():
    """office(사내 ePrism) -> CA 번들 경로, home -> 기본 검증(True)."""
    if os.environ.get("APP_ENV", "home").lower() == "office":
        return os.environ.get("REQUESTS_CA_BUNDLE", "/etc/ssl/certs/ca-certificates.crt")
    return True

def make_client(**kwargs) -> httpx.Client:
    kwargs.setdefault("timeout", 90.0)        # 사내 프록시 첫 연결 지연 대비
    kwargs.setdefault("follow_redirects", True)
    headers = {"User-Agent": USER_AGENT}
    headers.update(kwargs.pop("headers", {}))
    return httpx.Client(verify=get_verify(), headers=headers, **kwargs)
