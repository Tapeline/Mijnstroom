from dataclasses import dataclass

from dishka.integrations.litestar import FromDishka, inject
from litestar import Controller, get, post
from litestar.response import Redirect, Template

from mijnstroom.application.queue.cancel_job import CancelJob, DeleteFailedJob
from mijnstroom.application.queue.list_jobs import ListJobs
from mijnstroom.domain.job import Job, JobStatus


@dataclass(slots=True)
class GroupedJobs:
    pending: list[Job]
    running: list[Job]
    failed: list[Job]
    cancelled: list[Job]
    done: list[Job]


class QueueController(Controller):
    path = "/queue"

    @get("/")
    @inject
    async def index(
        self,
        list_jobs: FromDishka[ListJobs],
    ) -> Template:
        grouped = await list_jobs()
        view = GroupedJobs(
            pending=grouped.get(JobStatus.PENDING, []),
            running=grouped.get(JobStatus.RUNNING, []),
            failed=grouped.get(JobStatus.FAILED, []),
            cancelled=grouped.get(JobStatus.CANCELLED, []),
            done=grouped.get(JobStatus.DONE, []),
        )
        return Template(template_name="queue.html", context={"grouped": view})

    @post("/{job_id:str}/cancel")
    @inject
    async def cancel(
        self,
        job_id: str,
        cancel_job: FromDishka[CancelJob],
    ) -> Redirect:
        await cancel_job(job_id)
        return Redirect(path="/queue")

    @post("/{job_id:str}/delete")
    @inject
    async def delete_failed(
        self,
        job_id: str,
        delete_job: FromDishka[DeleteFailedJob],
    ) -> Redirect:
        await delete_job(job_id)
        return Redirect(path="/queue")
