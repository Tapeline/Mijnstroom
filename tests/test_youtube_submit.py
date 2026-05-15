from datetime import UTC, datetime, timedelta

import pytest

from mijnstroom.application.interfaces.idp import UserId, UserIdProvider
from mijnstroom.application.youtube.dto import (
    PlaylistEntryPlan,
    SubmitPlaylistDownloadInput,
    SubmitVideoDownloadInput,
    VideoPiece,
)
from mijnstroom.application.youtube.submit import (
    SubmitPlaylistDownload,
    SubmitVideoDownload,
)
from mijnstroom.common.errors import ValidationError
from mijnstroom.common.time import Clock
from mijnstroom.domain.job import JobKind
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


class _StaticUserIdProvider(UserIdProvider):
    async def current_user(self) -> UserId | None:
        return UserId("me")

    async def require_user(self) -> UserId:
        return UserId("me")


class _Rate:
    def __init__(self, interval: int) -> None:
        self.interval_seconds = interval


@pytest.mark.asyncio
async def test_submit_video_enqueues_one_job(db_path: str) -> None:
    settings = SqliteSettings(path=db_path)
    await apply_migrations(settings)
    tx = SqliteTransaction(settings)
    repo = SqliteJobRepo(tx)
    clock = _FixedClock(datetime(2026, 1, 1, tzinfo=UTC))
    queue = SqliteQueueGateway(repo, tx, clock)
    interactor = SubmitVideoDownload(
        queue=queue,
        repo=repo,
        tx=tx,
        idp=_StaticUserIdProvider(),
        clock=clock,
        rate_limit=_Rate(30),
    )
    try:
        pieces = (
            VideoPiece(
                start_ms=0,
                end_ms=10_000,
                title="One",
                artist=None,
                album=None,
                year=None,
                genre=None,
            ),
        )
        job_id = await interactor(
            SubmitVideoDownloadInput(url="https://example.com/v", pieces=pieces)
        )
        async with tx:
            job = await repo.get(job_id)
        assert job is not None
        assert job.kind == JobKind.YT_VIDEO
        # First job: spaced by interval from clock.now().
        assert job.next_run_at >= clock.now() + timedelta(seconds=30)
    finally:
        await tx.close()


@pytest.mark.asyncio
async def test_submit_video_rejects_no_enabled_pieces(db_path: str) -> None:
    settings = SqliteSettings(path=db_path)
    await apply_migrations(settings)
    tx = SqliteTransaction(settings)
    repo = SqliteJobRepo(tx)
    clock = _FixedClock(datetime(2026, 1, 1, tzinfo=UTC))
    queue = SqliteQueueGateway(repo, tx, clock)
    interactor = SubmitVideoDownload(
        queue=queue,
        repo=repo,
        tx=tx,
        idp=_StaticUserIdProvider(),
        clock=clock,
        rate_limit=_Rate(30),
    )
    try:
        with pytest.raises(ValidationError):
            await interactor(
                SubmitVideoDownloadInput(
                    url="https://example.com/v",
                    pieces=(
                        VideoPiece(
                            start_ms=0,
                            end_ms=1,
                            title="X",
                            artist=None,
                            album=None,
                            year=None,
                            genre=None,
                            enabled=False,
                        ),
                    ),
                )
            )
    finally:
        await tx.close()


@pytest.mark.asyncio
async def test_submit_playlist_enqueues_one_job_per_entry(db_path: str) -> None:
    settings = SqliteSettings(path=db_path)
    await apply_migrations(settings)
    tx = SqliteTransaction(settings)
    repo = SqliteJobRepo(tx)
    clock = _FixedClock(datetime(2026, 1, 1, tzinfo=UTC))
    queue = SqliteQueueGateway(repo, tx, clock)
    interactor = SubmitPlaylistDownload(
        queue=queue,
        repo=repo,
        tx=tx,
        idp=_StaticUserIdProvider(),
        clock=clock,
        rate_limit=_Rate(30),
    )
    try:
        entries = (
            PlaylistEntryPlan(
                url="https://e/1", title="A", artist=None, album=None, year=None, genre=None
            ),
            PlaylistEntryPlan(
                url="https://e/2", title="B", artist=None, album=None, year=None, genre=None
            ),
            PlaylistEntryPlan(
                url="https://e/3",
                title="C",
                artist=None,
                album=None,
                year=None,
                genre=None,
                enabled=False,
            ),
        )
        ids = await interactor(SubmitPlaylistDownloadInput(url="https://e", entries=entries))
        assert len(ids) == 2
    finally:
        await tx.close()
