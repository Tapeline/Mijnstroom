from dataclasses import dataclass

from dishka.integrations.litestar import FromDishka, inject
from litestar import Controller, get, post
from litestar.response import Redirect, Template

from mijnstroom.application.interfaces.repos import JobRepo, TrackRepo
from mijnstroom.application.queue.cancel_job import CancelJob, DeleteFailedJob
from mijnstroom.application.queue.list_jobs import ListJobs
from mijnstroom.domain.job import Job, JobStatus
from mijnstroom.domain.track import TrackId


@dataclass(slots=True)
class GroupedJobs:
    pending: list[Job]
    running: list[Job]
    failed: list[Job]
    cancelled: list[Job]
    done: list[Job]


@dataclass(slots=True)
class JobRow:
    job: Job
    track_title: str | None


class QueueController(Controller):
    path = "/queue"

    @get("/")
    @inject
    async def index(
        self,
        list_jobs: FromDishka[ListJobs],
        job_repo: FromDishka[JobRepo],
        track_repo: FromDishka[TrackRepo],
    ) -> Template:
        grouped = await list_jobs()
        view = GroupedJobs(
            pending=grouped.get(JobStatus.PENDING, []),
            running=grouped.get(JobStatus.RUNNING, []),
            failed=grouped.get(JobStatus.FAILED, []),
            cancelled=grouped.get(JobStatus.CANCELLED, []),
            done=grouped.get(JobStatus.DONE, []),
        )
        # Resolve track titles from job payloads.
        job_rows = await _resolve_track_titles(view, job_repo, track_repo)
        return Template(template_name="queue.html", context={"grouped": job_rows})

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


async def _resolve_track_titles(
    grouped: GroupedJobs,
    job_repo: JobRepo,
    track_repo: TrackRepo,
) -> dict[str, list[JobRow]]:
    """Attach track titles to jobs that have a track_id in their payload."""
    result: dict[str, list[JobRow]] = {}
    for status_name, jobs in [
        ("pending", grouped.pending),
        ("running", grouped.running),
        ("failed", grouped.failed),
        ("cancelled", grouped.cancelled),
        ("done", grouped.done),
    ]:
        rows = []
        for j in jobs:
            title = await _extract_track_title(j, track_repo)
            rows.append(JobRow(job=j, track_title=title))
        result[status_name] = rows
    return result


async def _extract_track_title(job: Job, track_repo: TrackRepo) -> str | None:
    import json

    try:
        payload = json.loads(job.payload_json)
    except (json.JSONDecodeError, TypeError):
        return None

    track_id = payload.get("track_id")
    if track_id:
        try:
            track = await track_repo.get(TrackId(track_id))
            if track:
                return track.title
        except Exception:
            pass

    # For YouTube jobs, show the URL or title.
    url = payload.get("url")
    if url:
        # Shorten URL for display.
        return url[:60] + ("..." if len(url) > 60 else "")

    return None
