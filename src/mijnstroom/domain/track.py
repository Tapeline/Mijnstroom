from datetime import datetime
from typing import NewType

from mijnstroom.common.decorators import entity
from mijnstroom.common.errors import ValidationError
from mijnstroom.domain.audio import AudioFormat

TrackId = NewType("TrackId", str)


@entity
class Track:
    """A single playable audio item in the library."""

    id: TrackId
    storage_path: str
    format: AudioFormat
    duration_ms: int | None
    title: str
    artist: str | None
    album: str | None
    year: int | None
    genre: str | None
    cover_path: str | None
    lyrics: str | None
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.id:
            raise ValidationError("Track id cannot be blank")
        if not self.storage_path:
            raise ValidationError("Track storage path cannot be blank")
        if not self.title or not self.title.strip():
            raise ValidationError("Track title cannot be blank")
        if self.duration_ms is not None and self.duration_ms < 0:
            raise ValidationError("Track duration cannot be negative")
        if self.year is not None and (self.year < 1 or self.year > 9999):
            raise ValidationError(f"Invalid track year: {self.year}")
