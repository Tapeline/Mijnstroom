import os

import uvicorn
from litestar import Litestar

from mijnstroom.bootstrap.config import Config
from mijnstroom.bootstrap.di.container import build_web_container
from mijnstroom.bootstrap.logging import configure_logging
from mijnstroom.infrastructure.persistence.sqlite import SqliteSettings, apply_migrations
from mijnstroom.presentation.http.app import create_app

from src.mijnstroom.bootstrap.config import load_config


def build_app_from_env() -> tuple[Config, Litestar]:
    """Build a fresh container + app from the ambient configuration."""
    configure_logging()
    config = load_config("config.yml")
    data_dir = os.environ.get("MIJNSTROOM_DATA_DIR")
    if data_dir:
        from dataclasses import replace

        config = replace(config, storage=replace(config.storage, data_dir=data_dir))
    container = build_web_container(config)
    app: Litestar = create_app(container)
    return config, app


async def _prepare_database(config: Config) -> None:
    settings = SqliteSettings(path=os.path.join(config.storage.data_dir, "mijnstroom.sqlite"))
    await apply_migrations(settings)


def main() -> None:
    import asyncio

    config, app = build_app_from_env()
    asyncio.run(_prepare_database(config))
    uvicorn.run(
        app,
        host=config.http.host,
        port=config.http.port,
        workers=1,
        log_level="info",
    )


if __name__ == "__main__":  # pragma: no cover
    main()
