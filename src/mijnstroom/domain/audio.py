from enum import StrEnum

from mijnstroom.common.decorators import value_object
from mijnstroom.common.errors import ValidationError


class AudioFormat(StrEnum):
    """Container/codec the on-disk audio file uses."""

    AAC = "aac"
    MP3 = "mp3"
    OGG = "ogg"
    FLAC = "flac"
    WAV = "wav"
    OPUS = "opus"


@value_object
class Bitrate:
    """Audio bitrate in kbit/s."""

    kbps: int

    def __post_init__(self) -> None:
        if self.kbps <= 0 or self.kbps > 10_000:
            raise ValidationError(f"Invalid bitrate: {self.kbps} kbps")


@value_object
class FilePath:
    """An absolute, server-side filesystem path."""

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValidationError("File path cannot be blank")
