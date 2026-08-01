import asyncio
import logging
import pprint
import uuid
from dataclasses import dataclass, replace
from enum import Enum

from mijnstroom.errors import NotFoundError


class PipelineStatus(Enum):
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class RunningPipeline:
    title: str
    status: PipelineStatus
    log: list[str]


class PipelineRegistry:
    def __init__(self):
        self._pipelines: dict[str, RunningPipeline] = {}
        self._tasks = {}

    def start_task(self, uid: str, coro):
        self._tasks[uid] = asyncio.create_task(coro)
        self._tasks[uid].add_done_callback(
            lambda *_: self._tasks.pop(uid)
        )

    def create(self, title: str) -> str:
        uid = str(uuid.uuid4())
        self._pipelines[uid] = RunningPipeline(
            title=title,
            status=PipelineStatus.RUNNING,
            log=["started"],
        )
        return uid

    def get_pipeline(self, uid: str) -> RunningPipeline | None:
        return self._pipelines.get(uid)

    def update_status(
        self,
        uid: str,
        status: PipelineStatus,
        extended_status: str
    ) -> None:
        self._pipelines[uid] = replace(
            self._pipelines[uid], status=status,
            log=[*self._pipelines[uid].log, extended_status]
        )
        logging.info(
            "process %s now %s: %s", uid, status.name, extended_status
        )


class Pipeline:
    registry: PipelineRegistry

    def notify_started(self, title: str):
        self.uid = self.registry.create(title)

    def notify_running(self, extended_status: str) -> None:
        self.registry.update_status(
            self.uid, PipelineStatus.RUNNING, extended_status
        )

    def notify_done(self, extended_status: str = "finished") -> None:
        self.registry.update_status(
            self.uid, PipelineStatus.DONE, extended_status
        )

    def notify_failed(self, extended_status: str = "failed") -> None:
        self.registry.update_status(
            self.uid, PipelineStatus.FAILED, extended_status
        )


@dataclass
class SeeRunningJobs:
    registry: PipelineRegistry

    def __call__(self) -> list[RunningPipeline]:
        return list(self.registry._pipelines.values())


@dataclass
class GetJobDetail:
    registry: PipelineRegistry

    def __call__(self, job_uid: str) -> RunningPipeline:
        pipeline = self.registry.get_pipeline(job_uid)
        if not pipeline:
            raise NotFoundError("Job not found")
        return pipeline
