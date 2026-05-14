from mijnstroom.bootstrap.config import OIDCConfig
from mijnstroom.infrastructure.auth.oidc_client import OIDCClient


def test_is_allowed_matches_configured_sub() -> None:
    client = OIDCClient(OIDCConfig(allowed_sub="me"))
    assert client.is_allowed("me") is True
    assert client.is_allowed("someone-else") is False


def test_is_allowed_returns_false_when_not_configured() -> None:
    client = OIDCClient(OIDCConfig(allowed_sub=""))
    assert client.is_allowed("me") is False
