import asyncio
import json
from asyncio import gather
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Final

_CODEC_MAP: Final = MappingProxyType(
    {
        "flac": "flac",
        "aac": "aac",
        "mp3": "libmp3lame",
        "ogg": "libvorbis",
        "wav": "pcm_s16le",
    }
)

_BITRATE_CODECS: Final = frozenset(("aac", "mp3", "ogg"))


@dataclass(frozen=True, slots=True)
class TimeRange:
    start: float
    end: float

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError("start must be >= 0")
        if self.end <= self.start:
            raise ValueError("end must be > start")


async def transcode(
    input_path: Path,
    output_path: Path,
    codec: str,
    bitrate_kbps: int | None = None,
) -> Path:
    await _run_ffmpeg(
        *_with_codec_or_copy(
            [
                "ffmpeg",
                "-y",
                "-i", str(input_path),
                "-vn",
            ],
            codec=codec,
            bitrate_kbps=bitrate_kbps
        ),
        str(output_path)
    )
    return output_path


async def apply_metadata(
    input_path: Path,
    output_path: Path,
    *,
    title: str | None = None,
    artist: str | None = None,
    album: str | None = None,
    year: str | None = None,
    genre: str | None = None,
    cover_path: Path | None = None,
) -> Path:
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(input_path),
    ]
    if cover_path is not None:
        cmd.extend(("-i", str(cover_path)))

    cmd.extend(("-map", "0:a"))
    if cover_path is not None:
        cmd += [
            "-map", "1:0",
            "-c:v", "mjpeg",
            "-disposition:v:0", "attached_pic",
        ]
    cmd.extend(("-c:a", "copy"))

    if title is not None:
        cmd.extend(("-metadata", f"title={title}"))
    if artist is not None:
        cmd.extend(("-metadata", f"artist={artist}"))
    if album is not None:
        cmd.extend(("-metadata", f"album={album}"))
    if year is not None:
        cmd.extend(("-metadata", f"year={year}"))
    if genre is not None:
        cmd.extend(("-metadata", f"genre={genre}"))

    await _run_ffmpeg(*cmd, str(output_path))
    return output_path


async def split(
    input_path: Path,
    output_dir: Path,
    ranges: list[TimeRange],
    *,
    output_ext: str | None = None,
    recode_to_codec: str | None = None,
    bitrate_kbps: int | None = None,
) -> list[Path]:
    output_ext = (output_ext or input_path.suffix).removeprefix(".")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_paths: list[Path] = []
    commands: list[list[str]] = []

    for idx, time_range in enumerate(ranges):
        segment_path = (
            output_dir / f"{input_path.stem}_segment{idx:03d}.{output_ext}"
        )
        cmd = _with_codec_or_copy(
            [
                "ffmpeg",
                "-y",
                "-ss", f"{time_range.start:.6f}",
                "-to", f"{time_range.end:.6f}",
                "-i", str(input_path),
            ], codec=recode_to_codec, bitrate_kbps=bitrate_kbps
        )
        commands.append([*cmd, str(segment_path)])
        output_paths.append(segment_path)

    await gather(*(_run_ffmpeg(*cmd) for cmd in commands))

    return output_paths


async def get_duration(file_path: Path) -> float:
    stdout, _ = await _run_ffmpeg(
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        str(file_path),
    )
    try:
        info = json.loads(stdout)
        duration = float(info["format"]["duration"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(
            f"Could not determine duration of {file_path}: {exc}"
        ) from exc
    return duration


async def extract_audio(
    video_path: Path,
    output_path: Path,
    *,
    codec: str | None = None,
    bitrate_kbps: int | None = None,
) -> Path:
    await _run_ffmpeg(
        *_with_codec_or_copy(
            [
                "ffmpeg",
                "-y",
                "-i", str(video_path),
                "-vn",
            ],
            codec=codec,
            bitrate_kbps=bitrate_kbps,
        ),
        str(output_path)
    )
    return output_path


async def _run_ffmpeg(*args: str) -> tuple[bytes, bytes]:
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        cmd = " ".join(args)
        raise RuntimeError(
            f"Command failed (exit {proc.returncode}): {cmd}\n"
            f"stderr: {stderr.decode(errors='replace')}"
        )
    return stdout, stderr


def _with_codec_or_copy(
    cmd: list[str],
    codec: str | None = None,
    bitrate_kbps: int | None = None,
) -> list[str]:
    if codec is not None:
        if codec not in _CODEC_MAP:
            raise ValueError(
                f"Unsupported codec '{codec}'. "
                f"Supported: {', '.join(sorted(_CODEC_MAP))}"
            )
        if bitrate_kbps and codec in _BITRATE_CODECS:
            return [
                *cmd,
                "-c:a", _CODEC_MAP[codec],
                "-b:a", f"{bitrate_kbps}k"
            ]
        else:
            return [*cmd, "-c:a", _CODEC_MAP[codec]]
    else:
        return [*cmd, "-c:a", "copy"]
