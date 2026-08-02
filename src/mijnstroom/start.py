import asyncio

import uvicorn
from litestar import Litestar

from mijnstroom.config import load_config
from mijnstroom.http.app import create_app
from mijnstroom.http.container import AppContainer
from mijnstroom.media.yt import YT
from mijnstroom.storage import LockedStorage
from mijnstroom.usecases.registry import (
    PipelineRegistry,
)


def build_container() -> AppContainer:
    config = load_config()
    storage = LockedStorage(config)
    storage.init()
    registry = PipelineRegistry()
    yt = YT(config, storage.tmp_path)
    return AppContainer(
        config=config,
        storage=storage,
        registry=registry,
        yt=yt,
    )


def main():
    container = build_container()
    app = create_app(container)
    uvicorn.run(
        app,
        port=container.config.http.port,
        host=container.config.http.host
    )


if __name__ == "__main__":
    main()
