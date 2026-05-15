"""End-to-end smoke tests for the tracks vertical slice.

These tests shell out to ffmpeg / ffprobe; they are skipped when those
binaries are absent.
"""

import os
import shutil
import subprocess
import tempfile

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

ffmpeg_required = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg/ffprobe not installed",
)


def _gen_wav(path: str, seconds: float = 0.2) -> None:
    subprocess.check_call(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={seconds}",
            "-loglevel",
            "error",
            path,
        ]
    )


def _make_config(tmp_data_dir: str) -> Config:
    return Config(
        storage=StorageConfig(data_dir=tmp_data_dir),
        oidc=OIDCConfig(
            issuer="https://auth.example.com",
            client_id="mijnstroom",
            client_secret="x",
            redirect_uri="https://music.example.com/auth/callback",
            allowed_sub="me",
        ),
        session=SessionConfig(secret="test-secret"),
    )


@pytest.fixture
def auth_cookie(config: Config) -> str:
    return SessionCodec(config.session).encode(SessionData(sub="me"))


@pytest.mark.asyncio
@ffmpeg_required
async def test_upload_and_list_track(tmp_data_dir: str) -> None:
    config = _make_config(tmp_data_dir)
    settings = SqliteSettings(path=os.path.join(tmp_data_dir, "mijnstroom.sqlite"))
    await apply_migrations(settings)
    container = build_web_container(config)
    app = create_app(container)
    cookie = SessionCodec(config.session).encode(SessionData(sub="me"))

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fh:
        wav_path = fh.name
    try:
        _gen_wav(wav_path)
        with open(wav_path, "rb") as fh:
            wav_bytes = fh.read()

        async with AsyncTestClient(app=app) as client:
            client.cookies.set(SESSION_COOKIE_NAME, cookie)

            response = await client.post(
                "/upload",
                files={"audio": ("hello.wav", wav_bytes, "audio/wav")},
                follow_redirects=False,
            )
            assert response.status_code == 200, response.text
            # The metadata form should reference the incoming path.
            assert "incoming_path" in response.text
            # Extract the incoming_path value.
            import re

            match = re.search(r'name="incoming_path" value="([^"]+)"', response.text)
            assert match is not None
            incoming_path = match.group(1)

            # Submit the metadata form.
            response = await client.post(
                "/upload/finalize",
                data={
                    "incoming_path": incoming_path,
                    "title": "My Test Song",
                    "artist": "Tester",
                    "album": "Album X",
                    "year": "2024",
                    "genre": "Test",
                    "lyrics": "",
                },
                files={"cover": ("", b"", "application/octet-stream")},
                follow_redirects=False,
            )
            assert response.status_code in (302, 303), response.text
            location = response.headers["location"]
            assert location.startswith("/track/")
            track_id = location.removeprefix("/track/")

            # Library should now contain the track.
            response = await client.get("/library", follow_redirects=False)
            assert response.status_code == 200
            assert "My Test Song" in response.text

            # Track detail.
            response = await client.get(f"/track/{track_id}", follow_redirects=False)
            assert response.status_code == 200
            assert "My Test Song" in response.text

            # Stream (full content).
            response = await client.get(f"/track/{track_id}/stream", follow_redirects=False)
            assert response.status_code == 200

            # Stream (range).
            response = await client.get(
                f"/track/{track_id}/stream",
                headers={"Range": "bytes=0-31"},
                follow_redirects=False,
            )
            assert response.status_code == 206
            assert response.headers.get("content-range", "").startswith("bytes 0-31/")

            # Delete.
            response = await client.get(f"/track/{track_id}/delete", follow_redirects=False)
            assert response.status_code in (302, 303)

            response = await client.get(f"/track/{track_id}", follow_redirects=False)
            assert response.status_code == 404
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)


@pytest.mark.asyncio
@ffmpeg_required
async def test_edit_track_metadata(tmp_data_dir: str) -> None:
    config = _make_config(tmp_data_dir)
    settings = SqliteSettings(path=os.path.join(tmp_data_dir, "mijnstroom.sqlite"))
    await apply_migrations(settings)
    container = build_web_container(config)
    app = create_app(container)
    cookie = SessionCodec(config.session).encode(SessionData(sub="me"))

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fh:
        wav_path = fh.name
    try:
        _gen_wav(wav_path)
        with open(wav_path, "rb") as fh:
            wav_bytes = fh.read()

        async with AsyncTestClient(app=app) as client:
            client.cookies.set(SESSION_COOKIE_NAME, cookie)
            response = await client.post(
                "/upload",
                files={"audio": ("foo.wav", wav_bytes, "audio/wav")},
                follow_redirects=False,
            )
            import re

            match = re.search(r'name="incoming_path" value="([^"]+)"', response.text)
            assert match is not None
            incoming_path = match.group(1)

            response = await client.post(
                "/upload/finalize",
                data={
                    "incoming_path": incoming_path,
                    "title": "Original",
                    "artist": "",
                    "album": "",
                    "year": "",
                    "genre": "",
                    "lyrics": "",
                },
                files={"cover": ("", b"", "application/octet-stream")},
                follow_redirects=False,
            )
            track_id = response.headers["location"].removeprefix("/track/")

            # Edit
            response = await client.post(
                f"/track/{track_id}/edit",
                data={
                    "title": "Renamed",
                    "artist": "New Artist",
                    "album": "",
                    "year": "2020",
                    "genre": "",
                    "lyrics": "Some lyrics",
                },
                files={"cover": ("", b"", "application/octet-stream")},
                follow_redirects=False,
            )
            assert response.status_code in (302, 303), response.text

            response = await client.get(f"/track/{track_id}", follow_redirects=False)
            assert response.status_code == 200
            assert "Renamed" in response.text
            assert "New Artist" in response.text
            assert "Some lyrics" in response.text
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)
