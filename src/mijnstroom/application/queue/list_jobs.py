from mijnstroom.application.interfaces.idp import UserIdProvider
from mijnstroom.application.interfaces.repos import JobRepo
from mijnstroom.application.interfaces.tx import Transaction
from mijnstroom.common.decorators import interactor
from mijnstroom.domain.job import Job, JobStatus


@interactor
class ListJobs:
    """List jobs grouped by status."""

    repo: JobRepo
    tx: Transaction
    idp: UserIdProvider

    async def __call__(self) -> dict[JobStatus, list[Job]]:
        async with self.tx:
            await self.idp.require_user()
            result: dict[JobStatus, list[Job]] = {}
            for status in JobStatus:
                result[status] = await self.repo.list_by_status(status)
            return result
