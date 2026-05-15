import asyncio
import logging
import os
from pathlib import Path

from mijnstroom.application.interfaces.audio import (
    AudioConverter,
    ConvertSpec,
    CoverExtractor,
    TagWriter,
)
from mijnstroom.common.errors import AppError
from mijnstroom.domain.audio import AudioFormat

logger = logging.getLogger(__name__)


class FfmpegError(AppError):
    """ffmpeg returned a non-zero exit status."""


# Map our AudioFormat enum to the (ffmpeg codec, file extension) pair used
# when transcoding to that format.
_CODEC_MAP: dict[AudioFormat, tuple[str, str]] = {
    AudioFormat.AAC: ("aac", "m4a"),
    AudioFormat.MP3: ("libmp3lame", "mp3"),
    AudioFormat.OGG: ("libvorbis", "ogg"),
    AudioFormat.FLAC: ("flac", "flac"),
    AudioFormat.WAV: ("pcm_s16le", "wav"),
    AudioFormat.OPUS: ("libopus", "opus"),
}


def codec_for(target: AudioFormat) -> tuple[str, str]:
    return _CODEC_MAP[target]


async def _run_ffmpeg(args: list[str], binary: str = "ffmpeg") -> None:
    proc = await asyncio.create_subprocess_exec(
        binary,
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise FfmpegError(f"ffmpeg failed: {stderr.decode('utf-8', 'replace')}")


class FfmpegAudioConverter(AudioConverter):
    """Audio converter shelling out to ``ffmpeg``.

    ``convert`` reads ``source_path``, optionally trims to
    ``[start_ms, end_ms]`` and re-encodes to ``spec.target_format`` at the
    requested bitrate, writing to ``dest_path`` atomically (via a temp
    suffix, then ``os.replace``).
    """

    __slots__ = ("_binary",)

    def __init__(self, binary: str = "ffmpeg") -> None:
        self._binary = binary

    async def convert(self, source_path: str, dest_path: str, spec: ConvertSpec) -> None:
        codec, _ = _CODEC_MAP[spec.target_format]
        path_name, path_ext = dest_path.rsplit(".", 1)
        tmp_path = path_name + ".tmp." + path_ext
        Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
        args: list[str] = ["-y", "-hide_banner", "-loglevel", "error"]
        if spec.start_ms is not None:
            args += ["-ss", f"{spec.start_ms / 1000:.3f}"]
        args += ["-i", source_path]
        if spec.end_ms is not None and spec.start_ms is not None:
            duration = max(spec.end_ms - spec.start_ms, 0) / 1000
            args += ["-t", f"{duration:.3f}"]
        elif spec.end_ms is not None:
            args += ["-to", f"{spec.end_ms / 1000:.3f}"]
        args += [
            "-vn",
            "-c:a",
            codec,
            "-b:a",
            f"{spec.target_bitrate_kbps}k",
            tmp_path,
        ]
        try:
            await _run_ffmpeg(args, self._binary)
        except Exception:
            await asyncio.to_thread(_safe_unlink, tmp_path)
            raise
        await asyncio.to_thread(os.replace, tmp_path, dest_path)


def _safe_unlink(path: str) -> None:
    import contextlib

    with contextlib.suppress(FileNotFoundError):
        os.remove(path)


class FfmpegTagWriter(TagWriter):
    """Tag writer that re-muxes a file in place to update embedded tags.

    ffmpeg cannot edit metadata in place reliably across formats, so we
    write to a temp file and atomically replace the original.
    """

    __slots__ = ("_binary",)

    def __init__(self, binary: str = "ffmpeg") -> None:
        self._binary = binary

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
    ) -> None:
        tmp_path = path + ".tagging.tmp"
        args: list[str] = ["-y", "-hide_banner", "-loglevel", "error", "-i", path]
        if cover_path is not None:
            args += [
                "-i",
                cover_path,
                "-map",
                "0:a",
                "-map",
                "1:v",
                "-disposition:v",
                "attached_pic",
            ]
        else:
            args += ["-map", "0:a"]
        args += ["-c", "copy"]
        for key, value in (
            ("title", title),
            ("artist", artist),
            ("album", album),
            ("date", str(year) if year is not None else None),
            ("genre", genre),
            ("lyrics", lyrics),
        ):
            if value is not None:
                args += ["-metadata", f"{key}={value}"]
        # ffmpeg picks the muxer from the extension; we keep the original
        # extension on the temp file so the right muxer runs.
        ext = Path(path).suffix or ".m4a"
        tmp_with_ext = tmp_path + ext
        args.append(tmp_with_ext)
        try:
            await _run_ffmpeg(args, self._binary)
        except Exception:
            await asyncio.to_thread(_safe_unlink, tmp_with_ext)
            raise
        await asyncio.to_thread(os.replace, tmp_with_ext, path)


class FfmpegCoverExtractor(CoverExtractor):
    """Extracts embedded album art from an audio file using ffmpeg."""

    __slots__ = ("_binary",)

    def __init__(self, binary: str = "ffmpeg") -> None:
        self._binary = binary

    async def extract(self, source_path: str) -> bytes | None:
        tmp_path = source_path + ".cover.tmp.jpg"
        args = [
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            source_path,
            "-map",
            "0:v",
            "-c",
            "copy",
            "-frames:v",
            "1",
            tmp_path,
        ]
        try:
            await _run_ffmpeg(args, self._binary)
        except FfmpegError:
            # No embedded cover or extraction failed.
            await asyncio.to_thread(_safe_unlink, tmp_path)
            return None
        except Exception:
            await asyncio.to_thread(_safe_unlink, tmp_path)
            return None

        def _read() -> bytes | None:
            try:
                with open(tmp_path, "rb") as fh:
                    data = fh.read()
                os.remove(tmp_path)
                return data if data else None
            except OSError:
                return None

        return await asyncio.to_thread(_read)
