import pytest

from mijnstroom.application.interfaces.tx import Transaction
from mijnstroom.bootstrap.config import Config
from mijnstroom.bootstrap.di.container import build_web_container, build_worker_container


@pytest.mark.asyncio
async def test_web_container_resolves_app_scope(config: Config) -> None:
    container = build_web_container(config)
    try:
        resolved = await container.get(Config)
        assert resolved is config
    finally:
        await container.close()


@pytest.mark.asyncio
async def test_worker_container_resolves_request_scope(config: Config) -> None:
    container = build_worker_container(config)
    try:
        async with container() as request:
            tx = await request.get(Transaction)
            assert tx is not None
    finally:
        await container.close()
