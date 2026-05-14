from abc import abstractmethod
from datetime import datetime
from typing import Protocol

from mijnstroom.domain.job import Job, JobId, JobKind


class QueueGateway(Protocol):
    @abstractmethod
    async def enqueue(
        self,
        kind: JobKind,
        payload_json: str,
        *,
        parent_job_id: JobId | None = None,
        run_at: datetime | None = None,
    ) -> JobId: ...

    @abstractmethod
    async def claim_next(self) -> Job | None: ...

    @abstractmethod
    async def mark_done(self, id: JobId) -> None: ...

    @abstractmethod
    async def mark_failed(self, id: JobId, error: str) -> None: ...

    @abstractmethod
    async def cancel_pending(self, id: JobId) -> bool: ...

    @abstractmethod
    async def delete(self, id: JobId) -> None: ...


