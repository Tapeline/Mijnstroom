from datetime import datetime

from mijnstroom.application.interfaces.queue import QueueGateway
from mijnstroom.application.interfaces.repos import JobRepo
from mijnstroom.application.interfaces.tx import Transaction
from mijnstroom.common.ids import generate_id
from mijnstroom.common.time import Clock
from mijnstroom.domain.job import Job, JobId, JobKind, JobStatus


class SqliteQueueGateway(QueueGateway):
    """Queue gateway implemented on top of the ``jobs`` table.

    Each operation is wrapped in the active transaction so callers may
    enqueue/claim/finish jobs atomically with their other state changes.
    """

    __slots__ = ("_clock", "_repo", "_tx")

    def __init__(self, repo: JobRepo, tx: Transaction, clock: Clock) -> None:
        self._repo = repo
        self._tx = tx
        self._clock = clock

    async def enqueue(
        self,
        kind: JobKind,
        payload_json: str,
        *,
        parent_job_id: JobId | None = None,
        run_at: datetime | None = None,
    ) -> JobId:
        async with self._tx:
            now = self._clock.now()
            job = Job(
                id=generate_id(JobId),
                kind=kind,
                payload_json=payload_json,
                status=JobStatus.PENDING,
                attempts=0,
                error=None,
                parent_job_id=parent_job_id,
                created_at=now,
                started_at=None,
                finished_at=None,
                next_run_at=run_at if run_at is not None else now,
            )
            await self._repo.insert(job)
            return job.id

    async def claim_next(self) -> Job | None:
        async with self._tx:
            return await self._repo.claim_next()

    async def mark_done(self, id: JobId) -> None:
        async with self._tx:
            await self._repo.mark_done(id)

    async def mark_failed(self, id: JobId, error: str) -> None:
        async with self._tx:
            await self._repo.mark_failed(id, error)

    async def cancel_pending(self, id: JobId) -> bool:
        async with self._tx:
            return await self._repo.cancel_pending(id)

    async def delete(self, id: JobId) -> None:
        async with self._tx:
            await self._repo.delete(id)
