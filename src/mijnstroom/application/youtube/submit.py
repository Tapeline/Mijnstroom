import json
from datetime import datetime, timedelta

from mijnstroom.application.interfaces.idp import UserIdProvider
from mijnstroom.application.interfaces.queue import QueueGateway
from mijnstroom.application.interfaces.rate_limit import YoutubeRateLimit
from mijnstroom.application.interfaces.repos import JobRepo
from mijnstroom.application.interfaces.tx import Transaction
from mijnstroom.application.youtube.dto import (
    SubmitPlaylistDownloadInput,
    SubmitVideoDownloadInput,
    VideoPiece,
)
from mijnstroom.common.decorators import interactor
from mijnstroom.common.errors import ValidationError
from mijnstroom.common.time import Clock
from mijnstroom.domain.job import JobId, JobKind, JobStatus


def _piece_to_dict(piece: VideoPiece) -> dict[str, object]:
    return {
        "start_ms": piece.start_ms,
        "end_ms": piece.end_ms,
        "title": piece.title,
        "artist": piece.artist,
        "album": piece.album,
        "year": piece.year,
        "genre": piece.genre,
    }


@interactor
class SubmitVideoDownload:
    """Enqueue a single ``yt_video`` job describing the user's plan."""

    queue: QueueGateway
    repo: JobRepo
    tx: Transaction
    idp: UserIdProvider
    clock: Clock
    rate_limit: YoutubeRateLimit

    async def __call__(self, input: SubmitVideoDownloadInput) -> JobId:
        enabled_pieces = [p for p in input.pieces if p.enabled]
        if not enabled_pieces:
            raise ValidationError("At least one piece must be enabled")
        for piece in enabled_pieces:
            if not piece.title.strip():
                raise ValidationError("Each piece needs a non-blank title")

        async with self.tx:
            await self.idp.require_user()
            run_at = await self._next_run_at()
            payload = {
                "url": input.url,
                "pieces": [_piece_to_dict(p) for p in enabled_pieces],
                "has_cover": input.cover_bytes is not None,
            }
            return await self.queue.enqueue(
                JobKind.YT_VIDEO,
                json.dumps(payload),
                run_at=run_at,
            )

    async def _next_run_at(self) -> datetime:
        # Space new YouTube jobs by ``interval_seconds`` after the most
        # recent pending YT job to avoid spamblocking.
        now = self.clock.now()
        latest: datetime = now
        for status in (JobStatus.PENDING, JobStatus.RUNNING):
            jobs = await self.repo.list_by_status(status)
            for job in jobs:
                if (
                    job.kind in (JobKind.YT_VIDEO, JobKind.YT_PLAYLIST_ITEM)
                    and job.next_run_at > latest
                ):
                    latest = job.next_run_at
        return latest + timedelta(seconds=self.rate_limit.interval_seconds)


@interactor
class SubmitPlaylistDownload:
    """Enqueue one ``yt_playlist_item`` job per enabled entry."""

    queue: QueueGateway
    repo: JobRepo
    tx: Transaction
    idp: UserIdProvider
    clock: Clock
    rate_limit: YoutubeRateLimit

    async def __call__(self, input: SubmitPlaylistDownloadInput) -> list[JobId]:
        enabled = [e for e in input.entries if e.enabled]
        if not enabled:
            raise ValidationError("At least one entry must be enabled")
        async with self.tx:
            await self.idp.require_user()
            ids: list[JobId] = []
            cursor = self.clock.now()
            for entry in enabled:
                cursor = cursor + timedelta(seconds=self.rate_limit.interval_seconds)
                payload = {
                    "url": entry.url,
                    "title": entry.title,
                    "artist": entry.artist,
                    "album": entry.album,
                    "year": entry.year,
                    "genre": entry.genre,
                }
                ids.append(
                    await self.queue.enqueue(
                        JobKind.YT_PLAYLIST_ITEM,
                        json.dumps(payload),
                        run_at=cursor,
                    )
                )
            return ids
