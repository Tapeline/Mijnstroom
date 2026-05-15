import os
from datetime import datetime
from typing import Any

import pytest

from mijnstroom.application.worker.dispatch import HANDLER_REGISTRY, register_handler
from mijnstroom.bootstrap.config import Config, OIDCConfig, StorageConfig
from mijnstroom.bootstrap.di.container import build_worker_container
from mijnstroom.bootstrap.worker import _process_one
from mijnstroom.common.decorators import interactor
from mijnstroom.domain.job import Job, JobKind, JobStatus
from mijnstroom.infrastructure.persistence.job_repo import SqliteJobRepo
from mijnstroom.infrastructure.persistence.sqlite import SqliteSettings, apply_migrations
from mijnstroom.infrastructure.persistence.transaction import SqliteTransaction


def _make_config(tmp_data_dir: str) -> Config:
    return Config(
        storage=StorageConfig(data_dir=tmp_data_dir),
        oidc=OIDCConfig(allowed_sub="me"),
    )


# Module-level mutable state to prove the handler ran.
_processed_jobs: list[Job] = []


@interactor
class _RecordingHandler:
    async def __call__(self, job: Job) -> None:
        _processed_jobs.append(job)


@pytest.mark.asyncio
async def test_worker_processes_pending_job(tmp_data_dir: str) -> None:
    _processed_jobs.clear()
    config = _make_config(tmp_data_dir)
    settings = SqliteSettings(path=os.path.join(tmp_data_dir, "mijnstroom.sqlite"))
    await apply_migrations(settings)

    # Insert a pending job by hand.
    tx = SqliteTransaction(settings)
    repo = SqliteJobRepo(tx)
    try:
        async with tx:
            await repo.insert(
                Job(
                    id="job-1",  # type: ignore[arg-type]
                    kind=JobKind.YT_VIDEO,
                    payload_json='{"x": 1}',
                    status=JobStatus.PENDING,
                    attempts=0,
                    error=None,
                    parent_job_id=None,
                    created_at=datetime.now().astimezone(),
                    started_at=None,
                    finished_at=None,
                    next_run_at=datetime.now().astimezone(),
                )
            )
    finally:
        await tx.close()

    # Register handler and provider so Dishka can resolve _RecordingHandler.
    register_handler(JobKind.YT_VIDEO, _RecordingHandler)

    from dishka import Provider, Scope, provide

    class _HandlerProvider(Provider):
        scope = Scope.REQUEST
        record = provide(_RecordingHandler)

    # Patch the container builder to include our handler provider.
    from dishka import make_async_container

    from mijnstroom.bootstrap.di.providers import (
        ConfigProvider,
        InfraProvider,
        InteractorProvider,
        WorkerRequestProvider,
    )

    container = make_async_container(
        ConfigProvider(config),
        InfraProvider(),
        WorkerRequestProvider(),
        InteractorProvider(),
        _HandlerProvider(),
    )

    try:
        processed = await _process_one(container)
        assert processed is True
        assert len(_processed_jobs) == 1
        assert _processed_jobs[0].kind == JobKind.YT_VIDEO

        # Verify the job is now done.
        tx = SqliteTransaction(settings)
        try:
            async with tx:
                row = await SqliteJobRepo(tx).get("job-1")  # type: ignore[arg-type]
            assert row is not None
            assert row.status == JobStatus.DONE
        finally:
            await tx.close()
    finally:
        await container.close()
        HANDLER_REGISTRY.pop(JobKind.YT_VIDEO, None)


# Silence unused-import warnings for narrow type stubs we used above.
_ = build_worker_container, Any
