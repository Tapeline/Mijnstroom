from mijnstroom.application.interfaces.idp import UserIdProvider
from mijnstroom.application.interfaces.queue import QueueGateway
from mijnstroom.application.interfaces.repos import JobRepo
from mijnstroom.application.interfaces.storage import FileStorage
from mijnstroom.application.interfaces.tx import Transaction
from mijnstroom.common.decorators import interactor
from mijnstroom.common.errors import Conflict, NotFound
from mijnstroom.domain.job import JobId, JobStatus


@interactor
class CancelJob:
    """Cancel a still-pending job."""

    queue: QueueGateway
    repo: JobRepo
    tx: Transaction
    idp: UserIdProvider

    async def __call__(self, job_id: str) -> None:
        async with self.tx:
            await self.idp.require_user()
            existing = await self.repo.get(JobId(job_id))
            if existing is None:
                raise NotFound(f"Job {job_id} does not exist")
            ok = await self.repo.cancel_pending(existing.id)
            if not ok:
                raise Conflict(f"Job {job_id} is no longer pending")


_TERMINAL_STATES: frozenset[JobStatus] = frozenset(
    {JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.DONE}
)


@interactor
class DeleteFailedJob:
    """Delete a job in a terminal state (failed/cancelled/done) and
    clean up any half-written files referenced by its payload.

    Despite the name, this interactor accepts any terminal-status job;
    pending and running jobs must be cancelled first.
    """

    repo: JobRepo
    storage: FileStorage
    tx: Transaction
    idp: UserIdProvider

    async def __call__(self, job_id: str) -> None:
        import json

        async with self.tx:
            await self.idp.require_user()
            existing = await self.repo.get(JobId(job_id))
            if existing is None:
                raise NotFound(f"Job {job_id} does not exist")
            if existing.status not in _TERMINAL_STATES:
                raise Conflict(f"Job {job_id} is not in a terminal state")
            try:
                payload = json.loads(existing.payload_json) if existing.payload_json else {}
            except ValueError:
                payload = {}
            paths_to_clean: list[str] = []
            if isinstance(payload, dict):
                for key in ("incoming_path", "tmp_path", "download_path"):
                    value = payload.get(key)
                    if isinstance(value, str):
                        paths_to_clean.append(value)
            await self.repo.delete(existing.id)
            for path in paths_to_clean:
                await self.storage.delete(path)
