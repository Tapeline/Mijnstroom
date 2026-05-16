import os

import pytest
from litestar.testing import AsyncTestClient

from mijnstroom.bootstrap.config import Config, OIDCConfig, SessionConfig, StorageConfig
from mijnstroom.bootstrap.di.container import build_web_container
from mijnstroom.infrastructure.auth.session import (
    SESSION_COOKIE_NAME,
    SessionCodec,
    SessionData,
)
from mijnstroom.infrastructure.persistence.sqlite import SqliteSettings, apply_migrations
from mijnstroom.presentation.http.app import create_app


def _make_config(tmp_data_dir: str) -> Config:
    return Config(
        storage=StorageConfig(data_dir=tmp_data_dir),
        oidc=OIDCConfig(
            issuer="https://auth.example.com",
            client_id="m",
            client_secret="x",
            redirect_uri="https://m/callback",
            allowed_sub="me",
        ),
        session=SessionConfig(secret="test-secret"),
    )


@pytest.mark.asyncio
async def test_playlist_create_rename_delete(tmp_data_dir: str) -> None:
    config = _make_config(tmp_data_dir)
    settings = SqliteSettings(path=os.path.join(tmp_data_dir, "mijnstroom.sqlite"))
    await apply_migrations(settings)
    container = build_web_container(config)
    app = create_app(container)
    cookie = SessionCodec(config.session).encode(SessionData(sub="me"))

    async with AsyncTestClient(app=app) as client:
        client.cookies.set(SESSION_COOKIE_NAME, cookie)

        # Create
        response = await client.post(
            "/playlists",
            data={"name": "My Mix"},
            follow_redirects=False,
        )
        assert response.status_code in (302, 303)
        location = response.headers["location"]
        assert location.startswith("/playlists/")
        playlist_id = location.removeprefix("/playlists/")

        # View
        response = await client.get(f"/playlists/{playlist_id}", follow_redirects=False)
        assert response.status_code == 200
        assert "My Mix" in response.text

        # Rename
        response = await client.post(
            f"/playlists/{playlist_id}/rename",
            data={"name": "Renamed"},
            follow_redirects=False,
        )
        assert response.status_code in (302, 303)

        response = await client.get(f"/playlists/{playlist_id}", follow_redirects=False)
        assert "Renamed" in response.text

        # Delete
        response = await client.post(f"/playlists/{playlist_id}/delete", follow_redirects=False)
        assert response.status_code in (302, 303)

        response = await client.get("/playlists", follow_redirects=False)
        assert "Renamed" not in response.text


@pytest.mark.asyncio
async def test_blank_playlist_name_rejected(tmp_data_dir: str) -> None:
    config = _make_config(tmp_data_dir)
    settings = SqliteSettings(path=os.path.join(tmp_data_dir, "mijnstroom.sqlite"))
    await apply_migrations(settings)
    container = build_web_container(config)
    app = create_app(container)
    cookie = SessionCodec(config.session).encode(SessionData(sub="me"))

    async with AsyncTestClient(app=app) as client:
        client.cookies.set(SESSION_COOKIE_NAME, cookie)
        response = await client.post(
            "/playlists",
            data={"name": "   "},
            follow_redirects=False,
        )
        assert response.status_code == 400
