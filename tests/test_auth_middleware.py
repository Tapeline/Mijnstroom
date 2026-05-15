import pytest
from litestar.testing import AsyncTestClient

from mijnstroom.bootstrap.config import Config, OIDCConfig, SessionConfig
from mijnstroom.bootstrap.di.container import build_web_container
from mijnstroom.infrastructure.auth.session import (
    SESSION_COOKIE_NAME,
    SessionCodec,
    SessionData,
)
from mijnstroom.presentation.http.app import create_app


def _make_config(tmp_data_dir: str) -> Config:
    return Config(
        storage=Config().storage.__class__(data_dir=tmp_data_dir),
        oidc=OIDCConfig(
            issuer="https://auth.example.com",
            client_id="mijnstroom",
            client_secret="x",
            redirect_uri="https://music.example.com/auth/callback",
            allowed_sub="me",
        ),
        session=SessionConfig(secret="test-secret"),
    )


@pytest.mark.asyncio
async def test_protected_route_redirects_to_login(tmp_data_dir: str) -> None:
    config = _make_config(tmp_data_dir)
    container = build_web_container(config)
    app = create_app(container)
    async with AsyncTestClient(app=app) as client:
        response = await client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/auth/login"


@pytest.mark.asyncio
async def test_authenticated_request_passes_middleware(tmp_data_dir: str) -> None:
    config = _make_config(tmp_data_dir)
    container = build_web_container(config)
    app = create_app(container)
    codec = SessionCodec(config.session)
    cookie = codec.encode(SessionData(sub="me"))
    async with AsyncTestClient(app=app) as client:
        client.cookies.set(SESSION_COOKIE_NAME, cookie)
        # / redirects to /library now; either way it must not be the login redirect.
        response = await client.get("/", follow_redirects=False)
    # Either 404 (no route) or 302/303 to /library; never /auth/login.
    assert response.headers.get("location") != "/auth/login"


@pytest.mark.asyncio
async def test_healthz_is_public(tmp_data_dir: str) -> None:
    config = _make_config(tmp_data_dir)
    container = build_web_container(config)
    app = create_app(container)
    async with AsyncTestClient(app=app) as client:
        response = await client.get("/healthz", follow_redirects=False)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_logout_clears_cookie(tmp_data_dir: str) -> None:
    config = _make_config(tmp_data_dir)
    container = build_web_container(config)
    app = create_app(container)
    async with AsyncTestClient(app=app) as client:
        response = await client.get("/auth/logout", follow_redirects=False)
    assert response.status_code in (301, 302, 303, 307, 308)
    assert response.headers["location"] == "/auth/login"
    # Cookie deletion is indicated by Set-Cookie with empty value or expired Max-Age
    set_cookie = response.headers.get("set-cookie", "")
    assert SESSION_COOKIE_NAME in set_cookie
