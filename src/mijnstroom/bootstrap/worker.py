import asyncio
import logging
import os
from dataclasses import replace

from mijnstroom.bootstrap.config import Config
from mijnstroom.bootstrap.di.container import build_worker_container
from mijnstroom.bootstrap.logging import configure_logging
from mijnstroom.infrastructure.persistence.sqlite import SqliteSettings, apply_migrations

logger = logging.getLogger(__name__)


async def run() -> None:
    configure_logging()
    config = Config()
    data_dir = os.environ.get("MIJNSTROOM_DATA_DIR")
    if data_dir:
        config = replace(config, storage=replace(config.storage, data_dir=data_dir))
    settings = SqliteSettings(path=os.path.join(config.storage.data_dir, "mijnstroom.sqlite"))
    await apply_migrations(settings)
    container = build_worker_container(config)
    try:
        logger.info("Worker started; idle (no handlers registered yet)")
        while True:
            await asyncio.sleep(config.queue.poll_interval_seconds)
    finally:
        await container.close()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":  # pragma: no cover
    main()


