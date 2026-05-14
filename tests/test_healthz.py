import pytest
from litestar.testing import AsyncTestClient

from mijnstroom.bootstrap.config import Config
from mijnstroom.bootstrap.di.container import build_web_container
from mijnstroom.presentation.http.app import create_app


@pytest.mark.asyncio
async def test_healthz_ok(config: Config) -> None:
    container = build_web_container(config)
    app = create_app(container)
    async with AsyncTestClient(app=app) as client:
        response = await client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["data_dir"] == config.storage.data_dir
