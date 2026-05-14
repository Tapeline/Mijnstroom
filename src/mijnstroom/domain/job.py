from datetime import datetime
from enum import StrEnum
from typing import NewType

from mijnstroom.common.decorators import entity
from mijnstroom.common.errors import ValidationError

JobId = NewType("JobId", str)


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobKind(StrEnum):
    YT_VIDEO = "yt_video"
    YT_PLAYLIST_ITEM = "yt_playlist_item"
    CONVERT = "convert"


@entity
class Job:
    """A unit of background work processed by the worker."""

    id: JobId
    kind: JobKind
    payload_json: str
    status: JobStatus
    attempts: int
    error: str | None
    parent_job_id: JobId | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    next_run_at: datetime

    def __post_init__(self) -> None:
        if not self.id:
            raise ValidationError("Job id cannot be blank")
        if self.attempts < 0:
            raise ValidationError("Job attempts cannot be negative")


