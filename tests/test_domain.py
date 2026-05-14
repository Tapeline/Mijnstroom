from datetime import UTC, datetime

import pytest

from mijnstroom.common.errors import ValidationError
from mijnstroom.common.ids import generate_id
from mijnstroom.domain.audio import AudioFormat
from mijnstroom.domain.job import Job, JobId, JobKind, JobStatus
from mijnstroom.domain.playlist import Playlist, PlaylistId
from mijnstroom.domain.track import Track, TrackId


def _now() -> datetime:
    return datetime(2026, 1, 1, tzinfo=UTC)


def test_track_blank_title_rejected() -> None:
    with pytest.raises(ValidationError):
        Track(
            id=generate_id(TrackId),
            storage_path="/data/tracks/x.m4a",
            format=AudioFormat.AAC,
            duration_ms=1000,
            title="",
            artist=None,
            album=None,
            year=None,
            genre=None,
            cover_path=None,
            lyrics=None,
            created_at=_now(),
        )


def test_track_negative_duration_rejected() -> None:
    with pytest.raises(ValidationError):
        Track(
            id=generate_id(TrackId),
            storage_path="/data/tracks/x.m4a",
            format=AudioFormat.AAC,
            duration_ms=-1,
            title="Hello",
            artist=None,
            album=None,
            year=None,
            genre=None,
            cover_path=None,
            lyrics=None,
            created_at=_now(),
        )


def test_track_invalid_year_rejected() -> None:
    with pytest.raises(ValidationError):
        Track(
            id=generate_id(TrackId),
            storage_path="/data/tracks/x.m4a",
            format=AudioFormat.AAC,
            duration_ms=None,
            title="Hello",
            artist=None,
            album=None,
            year=0,
            genre=None,
            cover_path=None,
            lyrics=None,
            created_at=_now(),
        )


def test_playlist_blank_name_rejected() -> None:
    with pytest.raises(ValidationError):
        Playlist(id=generate_id(PlaylistId), name="   ", created_at=_now())


def test_job_negative_attempts_rejected() -> None:
    with pytest.raises(ValidationError):
        Job(
            id=generate_id(JobId),
            kind=JobKind.YT_VIDEO,
            payload_json="{}",
            status=JobStatus.PENDING,
            attempts=-1,
            error=None,
            parent_job_id=None,
            created_at=_now(),
            started_at=None,
            finished_at=None,
            next_run_at=_now(),
        )
