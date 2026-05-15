from abc import abstractmethod
from typing import Protocol

from mijnstroom.common.decorators import dto
from mijnstroom.domain.audio import AudioFormat


@dto
class ProbedAudio:
    """Result of probing an audio file."""

    format: AudioFormat
    duration_ms: int | None
    title: str | None
    artist: str | None
    album: str | None
    year: int | None
    genre: str | None
    has_cover: bool


@dto
class ConvertSpec:
    """How to convert a piece of audio."""

    target_format: AudioFormat
    target_bitrate_kbps: int
    start_ms: int | None = None
    end_ms: int | None = None


class AudioProbe(Protocol):
    @abstractmethod
    async def probe(self, path: str) -> ProbedAudio: ...


class AudioConverter(Protocol):
    @abstractmethod
    async def convert(self, source_path: str, dest_path: str, spec: ConvertSpec) -> None: ...


class TagWriter(Protocol):
    @abstractmethod
    async def write_tags(
        self,
        path: str,
        *,
        title: str | None,
        artist: str | None,
        album: str | None,
        year: int | None,
        genre: str | None,
        cover_path: str | None,
        lyrics: str | None,
    ) -> None: ...


class CoverExtractor(Protocol):
    """Extracts embedded album art from an audio file."""

    @abstractmethod
    async def extract(self, source_path: str) -> bytes | None: ...
