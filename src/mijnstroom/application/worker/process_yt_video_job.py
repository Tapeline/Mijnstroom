import json
import logging
import os
from typing import Any

from mijnstroom.application.interfaces.audio import (
    AudioConverter,
    AudioProbe,
    ConvertSpec,
    TagWriter,
)
from mijnstroom.application.interfaces.repos import TrackRepo
from mijnstroom.application.interfaces.storage import FileStorage
from mijnstroom.application.interfaces.tx import Transaction
from mijnstroom.application.interfaces.ytdlp import YoutubeClient
from mijnstroom.common.decorators import interactor
from mijnstroom.common.errors import AppError
from mijnstroom.common.ids import generate_id
from mijnstroom.common.time import Clock
from mijnstroom.domain.audio import AudioFormat
from mijnstroom.domain.job import Job
from mijnstroom.domain.track import Track, TrackId

logger = logging.getLogger(__name__)


def _parse_payload(job: Job) -> dict[str, Any]:
    try:
        data = json.loads(job.payload_json)
    except ValueError as exc:
        raise AppError(f"Invalid job payload: {exc}") from exc
    if not isinstance(data, dict):
        raise AppError("Job payload must be an object")
    return data


@interactor
class ProcessYtVideoJob:
    """Worker handler for ``yt_video`` jobs.

    The payload is::

        {
          "url": "https://...",
          "pieces": [
            {
              "start_ms": int|null,
              "end_ms": int|null,
              "title": str,
              "artist": str|null,
              "album": str|null,
              "year": int|null,
              "genre": str|null
            },
            ...
          ],
          "has_cover": bool   # currently informational only
        }

    Each enabled piece becomes one ``Track``, sharing the source audio
    downloaded once via yt-dlp.
    """

    client: YoutubeClient
    converter: AudioConverter
    probe: AudioProbe
    tags: TagWriter
    storage: FileStorage
    repo: TrackRepo
    tx: Transaction
    clock: Clock

    async def __call__(self, job: Job) -> None:
        payload = _parse_payload(job)
        url = payload.get("url")
        if not isinstance(url, str):
            raise AppError("Missing url in payload")
        pieces_raw = payload.get("pieces")
        if not isinstance(pieces_raw, list) or not pieces_raw:
            raise AppError("Missing pieces in payload")

        incoming_dir = self.storage.incoming_dir()
        tmp_prefix = os.path.join(incoming_dir, f"yt-{job.id}")
        downloaded = await self.client.download_audio(url, tmp_prefix)
        try:
            for piece in pieces_raw:
                if not isinstance(piece, dict):
                    continue
                await self._save_piece(downloaded, piece)
        finally:
            if os.path.exists(downloaded):
                import contextlib

                with contextlib.suppress(OSError):
                    os.remove(downloaded)

    async def _save_piece(self, source_path: str, piece: dict[str, Any]) -> None:
        title = str(piece.get("title") or "").strip()
        if not title:
            raise AppError("Piece title cannot be blank")
        start_ms = _opt_int(piece.get("start_ms"))
        end_ms = _opt_int(piece.get("end_ms"))
        track_id = generate_id(TrackId)
        ext = "m4a"
        dest = os.path.join(self.storage.tracks_dir(), f"{track_id}.{ext}")
        spec = ConvertSpec(
            target_format=AudioFormat.AAC,
            target_bitrate_kbps=256,
            start_ms=start_ms,
            end_ms=end_ms,
        )
        await self.converter.convert(source_path, dest, spec)
        # Probe the saved file to compute duration; the converter may have
        # picked an exact value but we keep it accurate.
        probed = await self.probe.probe(dest)
        track = Track(
            id=track_id,
            storage_path=dest,
            format=AudioFormat.AAC,
            duration_ms=probed.duration_ms,
            title=title,
            artist=_opt_str(piece.get("artist")),
            album=_opt_str(piece.get("album")),
            year=_opt_int(piece.get("year")),
            genre=_opt_str(piece.get("genre")),
            cover_path=None,
            lyrics=None,
            created_at=self.clock.now(),
        )
        await self.tags.write_tags(
            track.storage_path,
            title=track.title,
            artist=track.artist,
            album=track.album,
            year=track.year,
            genre=track.genre,
            cover_path=None,
            lyrics=None,
        )
        async with self.tx:
            await self.repo.insert(track)


@interactor
class ProcessYtPlaylistItemJob:
    """Worker handler for a single playlist entry. Delegates to the same
    pipeline as ``ProcessYtVideoJob`` with a single piece covering the
    whole video.
    """

    video_handler: ProcessYtVideoJob

    async def __call__(self, job: Job) -> None:
        payload = _parse_payload(job)
        url = payload.get("url")
        if not isinstance(url, str):
            raise AppError("Missing url in payload")
        # Repack as a single-piece YT_VIDEO payload and delegate.
        single_piece_payload = {
            "url": url,
            "pieces": [
                {
                    "start_ms": None,
                    "end_ms": None,
                    "title": str(payload.get("title") or "Untitled"),
                    "artist": _opt_str(payload.get("artist")),
                    "album": _opt_str(payload.get("album")),
                    "year": _opt_int(payload.get("year")),
                    "genre": _opt_str(payload.get("genre")),
                }
            ],
            "has_cover": False,
        }
        adapted = Job(
            id=job.id,
            kind=job.kind,
            payload_json=json.dumps(single_piece_payload),
            status=job.status,
            attempts=job.attempts,
            error=job.error,
            parent_job_id=job.parent_job_id,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            next_run_at=job.next_run_at,
        )
        await self.video_handler(adapted)


def _opt_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _opt_str(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None
