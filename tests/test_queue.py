import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from mijnstroom.common.time import Clock
from mijnstroom.domain.job import JobKind, JobStatus
from mijnstroom.infrastructure.persistence.job_repo import SqliteJobRepo
from mijnstroom.infrastructure.persistence.sqlite import SqliteSettings, apply_migrations
from mijnstroom.infrastructure.persistence.transaction import SqliteTransaction
from mijnstroom.infrastructure.queue.sqlite_queue import SqliteQueueGateway


class _FixedClock(Clock):
    __slots__ = ("_now",)

    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


@pytest.mark.asyncio
async def test_enqueue_and_claim(db_path: str) -> None:
    settings = SqliteSettings(path=db_path)
    await apply_migrations(settings)
    tx = SqliteTransaction(settings)
    repo = SqliteJobRepo(tx)
    clock = _FixedClock(datetime(2026, 1, 1, tzinfo=UTC))
    queue = SqliteQueueGateway(repo, tx, clock)
    try:
        job_id = await queue.enqueue(JobKind.YT_VIDEO, '{"url": "x"}')
        claimed = await queue.claim_next()
        assert claimed is not None
        assert claimed.id == job_id
        assert claimed.status == JobStatus.RUNNING
        assert claimed.attempts == 1
    finally:
        await tx.close()


@pytest.mark.asyncio
async def test_concurrent_workers_cannot_claim_same_job(db_path: str) -> None:
    settings = SqliteSettings(path=db_path)
    await apply_migrations(settings)

    # Two independent transactions / queue gateways simulate two workers.
    tx_a = SqliteTransaction(settings)
    tx_b = SqliteTransaction(settings)
    repo_a = SqliteJobRepo(tx_a)
    repo_b = SqliteJobRepo(tx_b)
    clock = _FixedClock(datetime(2026, 1, 1, tzinfo=UTC))
    queue_a = SqliteQueueGateway(repo_a, tx_a, clock)
    queue_b = SqliteQueueGateway(repo_b, tx_b, clock)

    try:
        await queue_a.enqueue(JobKind.YT_VIDEO, "{}")
        results = await asyncio.gather(queue_a.claim_next(), queue_b.claim_next())
        successful = [r for r in results if r is not None]
        assert len(successful) == 1
    finally:
        await tx_a.close()
        await tx_b.close()


@pytest.mark.asyncio
async def test_future_jobs_not_claimed(db_path: str) -> None:
    settings = SqliteSettings(path=db_path)
    await apply_migrations(settings)
    tx = SqliteTransaction(settings)
    repo = SqliteJobRepo(tx)
    # Real wall clock so scheduled "now + 1h" is genuinely in the future
    # for the claim_next implementation, which uses datetime.now().
    real_now = datetime.now().astimezone()
    clock = _FixedClock(real_now)
    queue = SqliteQueueGateway(repo, tx, clock)
    try:
        future = real_now + timedelta(hours=1)
        await queue.enqueue(JobKind.YT_VIDEO, "{}", run_at=future)
        claimed = await queue.claim_next()
        assert claimed is None
    finally:
        await tx.close()


@pytest.mark.asyncio
async def test_cancel_pending_then_done_marks(db_path: str) -> None:
    settings = SqliteSettings(path=db_path)
    await apply_migrations(settings)
    tx = SqliteTransaction(settings)
    repo = SqliteJobRepo(tx)
    clock = _FixedClock(datetime(2026, 1, 1, tzinfo=UTC))
    queue = SqliteQueueGateway(repo, tx, clock)
    try:
        job_id = await queue.enqueue(JobKind.YT_VIDEO, "{}")
        ok = await queue.cancel_pending(job_id)
        assert ok is True
        async with tx:
            cancelled = await repo.get(job_id)
            assert cancelled is not None
            assert cancelled.status == JobStatus.CANCELLED

        # cancelling again must be a no-op (returns False).
        ok = await queue.cancel_pending(job_id)
        assert ok is False
    finally:
        await tx.close()
