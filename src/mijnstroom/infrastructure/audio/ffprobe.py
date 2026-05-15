import asyncio
import json
import logging

from mijnstroom.application.interfaces.audio import AudioProbe, ProbedAudio
from mijnstroom.common.errors import AppError
from mijnstroom.domain.audio import AudioFormat

logger = logging.getLogger(__name__)


class ProbeError(AppError):
    """ffprobe failed or produced unparseable output."""


_FORMAT_MAP: dict[str, AudioFormat] = {
    "mp3": AudioFormat.MP3,
    "ogg": AudioFormat.OGG,
    "flac": AudioFormat.FLAC,
    "wav": AudioFormat.WAV,
    "opus": AudioFormat.OPUS,
    "aac": AudioFormat.AAC,
    "m4a": AudioFormat.AAC,
    "mov,mp4,m4a,3gp,3g2,mj2": AudioFormat.AAC,
    "matroska,webm": AudioFormat.OPUS,
}


def _format_from_probe(format_name: str, codec_name: str | None) -> AudioFormat:
    if format_name in _FORMAT_MAP:
        return _FORMAT_MAP[format_name]
    # fall back to the codec name
    if codec_name:
        if codec_name in {"aac", "alac"}:
            return AudioFormat.AAC
        if codec_name == "mp3":
            return AudioFormat.MP3
        if codec_name == "vorbis":
            return AudioFormat.OGG
        if codec_name == "flac":
            return AudioFormat.FLAC
        if codec_name == "opus":
            return AudioFormat.OPUS
    return AudioFormat.AAC


class FfprobeAudioProbe(AudioProbe):
    """Audio probe implementation that shells out to ``ffprobe``."""

    __slots__ = ("_binary",)

    def __init__(self, binary: str = "ffprobe") -> None:
        self._binary = binary

    async def probe(self, path: str) -> ProbedAudio:
        proc = await asyncio.create_subprocess_exec(
            self._binary,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise ProbeError(f"ffprobe failed: {stderr.decode('utf-8', 'replace')}")
        try:
            data = json.loads(stdout.decode("utf-8"))
        except ValueError as exc:
            raise ProbeError(f"ffprobe produced invalid JSON: {exc}") from exc

        fmt = data.get("format", {})
        tags = {k.lower(): v for k, v in (fmt.get("tags") or {}).items()}
        streams = data.get("streams") or []
        audio_stream: dict[str, object] = {}
        has_cover = False
        for stream in streams:
            codec_type = stream.get("codec_type")
            if codec_type == "audio" and not audio_stream:
                audio_stream = stream
            if codec_type == "video":
                # mp3/m4a embedded covers show up as a video stream
                has_cover = True

        codec_name = audio_stream.get("codec_name") if audio_stream else None
        format_name = str(fmt.get("format_name") or "")
        audio_format = _format_from_probe(
            format_name, codec_name if isinstance(codec_name, str) else None
        )

        duration_str = fmt.get("duration")
        duration_ms: int | None = None
        if duration_str is not None:
            try:
                duration_ms = int(float(duration_str) * 1000)
            except (TypeError, ValueError):
                duration_ms = None

        year_raw = tags.get("date") or tags.get("year")
        year: int | None = None
        if year_raw:
            try:
                year = int(str(year_raw)[:4])
            except ValueError:
                year = None

        return ProbedAudio(
            format=audio_format,
            duration_ms=duration_ms,
            title=tags.get("title"),
            artist=tags.get("artist"),
            album=tags.get("album"),
            year=year,
            genre=tags.get("genre"),
            has_cover=has_cover,
        )
