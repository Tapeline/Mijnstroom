import asyncio
import logging
import os
from dataclasses import replace

from dishka import AsyncContainer

from mijnstroom.application.interfaces.queue import QueueGateway
from mijnstroom.application.worker.dispatch import HANDLER_REGISTRY
from mijnstroom.bootstrap.config import Config
from mijnstroom.bootstrap.di.container import build_worker_container
from mijnstroom.bootstrap.logging import configure_logging
from mijnstroom.domain.job import Job
from mijnstroom.infrastructure.persistence.sqlite import SqliteSettings, apply_migrations

from mijnstroom.bootstrap.config import load_config

logger = logging.getLogger(__name__)


async def _process_one(container: AsyncContainer) -> bool:
    """Claim and process a single job. Returns True if a job was processed."""
    async with container() as request_container:
        queue: QueueGateway = await request_container.get(QueueGateway)
        job: Job | None = await queue.claim_next()
        if job is None:
            return False

    handler_cls = HANDLER_REGISTRY.get(job.kind)
    if handler_cls is None:
        logger.error("No handler registered for job kind %s", job.kind)
        async with container() as request_container:
            queue = await request_container.get(QueueGateway)
            await queue.mark_failed(job.id, f"No handler for kind {job.kind}")
        return True

    # Run the handler in a fresh REQUEST scope so its own transaction
    # is independent from the claim transaction.
    try:
        async with container() as request_container:
            handler = await request_container.get(handler_cls)
            await handler(job)
        async with container() as request_container:
            queue = await request_container.get(QueueGateway)
            await queue.mark_done(job.id)
    except Exception as exc:  # intentional broad catch
        logger.exception("Job %s (%s) failed", job.id, job.kind)
        async with container() as request_container:
            queue = await request_container.get(QueueGateway)
            await queue.mark_failed(job.id, str(exc))
    return True


async def run() -> None:
    configure_logging()
    config = load_config("config.yml")
    data_dir = os.environ.get("MIJNSTROOM_DATA_DIR")
    if data_dir:
        config = replace(config, storage=replace(config.storage, data_dir=data_dir))
    settings = SqliteSettings(path=os.path.join(config.storage.data_dir, "mijnstroom.sqlite"))
    await apply_migrations(settings)

    # Late import so handler registration runs only in the worker process.
    from mijnstroom.bootstrap.worker_handlers import register_all_handlers

    register_all_handlers()

    container = build_worker_container(config)
    poll_interval = config.queue.poll_interval_seconds
    try:
        logger.info("Worker started; %d handler(s) registered", len(HANDLER_REGISTRY))
        while True:
            try:
                processed = await _process_one(container)
            except Exception:  # intentional broad catch
                logger.exception("Worker loop iteration failed")
                processed = False
            if not processed:
                await asyncio.sleep(poll_interval)
    finally:
        await container.close()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":  # pragma: no cover
    main()
