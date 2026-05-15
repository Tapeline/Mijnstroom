from dishka import AsyncContainer, make_async_container
from dishka.integrations.litestar import LitestarProvider

from mijnstroom.bootstrap.config import Config
from mijnstroom.bootstrap.di.providers import (
    ConfigProvider,
    InfraProvider,
    InteractorProvider,
    RequestProvider,
    WorkerRequestProvider,
)


def build_web_container(config: Config) -> AsyncContainer:
    return make_async_container(
        ConfigProvider(config),
        InfraProvider(),
        RequestProvider(),
        InteractorProvider(),
        LitestarProvider(),
    )


def build_worker_container(config: Config) -> AsyncContainer:
    return make_async_container(
        ConfigProvider(config),
        InfraProvider(),
        WorkerRequestProvider(),
        InteractorProvider(),
    )
