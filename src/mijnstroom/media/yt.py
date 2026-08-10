import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
import yt_dlp

from mijnstroom.config import Config


def _parse_duration(duration: int | float | None) -> int:
    if duration is None:
        return 0
    return int(duration)


def _parse_timecode(time_str: str) -> int:
    parts = time_str.strip().split(":")
    parts = [int(p) for p in parts]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0]


@dataclass(frozen=True, slots=True)
class YTTimecode:
    seconds: int
    label: str


def _parse_timecodes_from_description(description: str | None) -> list[
    YTTimecode]:
    if not description:
        return []
    pattern = re.compile(
        r"^\s*(\d{1,2}:\d{2}(?::\d{2})?)\s*[-–—]?\s*(.+?)\s*$",
        re.MULTILINE,
    )
    return [
        YTTimecode(_parse_timecode(match.group(1)), match.group(2))
        for match in pattern.finditer(description)
    ]


def _best_thumbnail(thumbnails: list[dict[str, Any]] | None) -> str | None:
    if not thumbnails:
        return None
    # last one typically is the best
    for thumb in reversed(thumbnails):
        if url := thumb.get("url"):
            return url
    return None


@dataclass(frozen=True, slots=True)
class YTVideo:
    id: str
    title: str
    channel: str
    duration_seconds: int
    thumbnail_url: str
    url: str


@dataclass(frozen=True, slots=True)
class YTVideoDetailed(YTVideo):
    id: str
    title: str
    channel: str
    duration_seconds: int
    thumbnail_url: str
    url: str
    upload_date: str
    description: str
    timecodes: list[YTTimecode]

    @property
    def year(self) -> int | None:
        try:
            return int(self.upload_date[:4])
        except ValueError:
            return None


@dataclass(frozen=True, slots=True)
class YTPlaylist:
    title: str
    channel: str
    entries: list[YTVideo]


class YT:
    def __init__(self, config: Config, tmp_dir: Path) -> None:
        self._tmp_dir = tmp_dir
        self._config = config.youtube

    def search(self, query: str, max_results: int = 10) -> list[YTVideo]:
        with yt_dlp.YoutubeDL(
            dict(
                quiet=True,
                no_warnings=True,
                extract_flat=False,
                skip_download=True,
                ignoreerrors=True,
                cookiefile=self._config.cookie_file
            )
        ) as ydl:
            result = ydl.extract_info(
                f"ytsearch{max_results}:{query}", download=False
            )
        return [
            YTVideo(
                id=entry["id"],
                title=entry["title"],
                channel=entry.get("channel") or entry.get("uploader"),
                duration_seconds=_parse_duration(entry.get("duration")),
                thumbnail_url=(
                    _best_thumbnail(entry.get("thumbnails"))
                    or entry.get("thumbnail")
                ),
                url=(
                    entry.get("webpage_url")
                    or f"https://www.youtube.com/watch?v={entry.get('id')}"
                ),
            )
            for entry in result.get("entries", []) if entry is not None
        ]

    def get_video_info(self, url: str) -> YTVideoDetailed | None:
        with yt_dlp.YoutubeDL(
            {
                "quiet": True,
                "no_warnings": True,
                "cookiefile": self._config.cookie_file,
                "check_formats": False,
                "verbose": True,
                "format": "bestaudio/best",
                "js_runtimes": {"node": {"path": "node"}},
                "extractor_args": {
                    "youtube": {
                        "pot_from_cookies": True
                    }
                }
            }
        ) as ydl:
            info = ydl.extract_info(url, download=False)
        if info is None:
            return None
        return YTVideoDetailed(
            id=info.get("id"),
            title=info.get("title"),
            channel=info.get("channel") or info.get("uploader"),
            duration_seconds=_parse_duration(info.get("duration")),
            thumbnail_url=(
                _best_thumbnail(info.get("thumbnails"))
                or info.get("thumbnail")
            ),
            upload_date=info.get("upload_date"),
            description=info.get("description", ""),
            url=info.get("webpage_url") or url,
            timecodes=_parse_timecodes_from_description(
                info.get("description", "")
            ),
        )

    def get_playlist_info(self, url: str) -> YTPlaylist | None:
        with yt_dlp.YoutubeDL(
            {
                "quiet": True,
                "no_warnings": True,
                "cookiefile": self._config.cookie_file,
                "check_formats": False,
                "verbose": True,
                "format": "bestaudio/best",
                "js_runtimes": {"node": {"path": "node"}},
                "extractor_args": {
                    "youtube": {
                        "pot_from_cookies": True
                    }
                }
            }
        ) as ydl:
            info = ydl.extract_info(url, download=False)
        if info is None:
            return None
        return YTPlaylist(
            title=info.get("title"),
            channel=info.get("channel") or info.get("uploader"),
            entries=[
                YTVideo(
                    id=entry.get("id"),
                    title=entry.get("title"),
                    channel=entry.get("channel") or entry.get("uploader"),
                    duration_seconds=_parse_duration(entry.get("duration")),
                    thumbnail_url=(
                        _best_thumbnail(entry.get("thumbnails"))
                        or entry.get("thumbnail")
                    ),
                    url=(
                        entry.get("webpage_url")
                        or f"https://www.youtube.com/watch?v={entry.get('id')}"
                    ),
                )
                for entry in info.get("entries", []) if entry is not None
            ],
        )

    def download_best_video(self, url: str, output_path: Path) -> Path | None:
        output_template = str(output_path.with_suffix(""))
        with yt_dlp.YoutubeDL(
            {
                "quiet": True,
                "no_warnings": True,
                "cookiefile": self._config.cookie_file,
                "check_formats": False,
                "format": "bestaudio/best",
                "js_runtimes": {"node": {"path": "node"}},
                "extractor_args": {
                    "youtube": {
                        "pot_from_cookies": True
                    }
                },
                "outtmpl": output_template + ".%(ext)s",
            }
        ) as ydl:
            info = ydl.extract_info(url, download=True)
        if info is None:
            return None
        ext = info.get("ext", "")
        actual_path = Path(f"{output_template}.{ext}")
        # some hacky stuff
        if not actual_path.exists():
            return next(
                output_path.parent.glob(f"{output_path.stem}.*"),
                None
            )
        return actual_path

    def download_thumbnail(self, thumbnail_url: str) -> bytes | None:
        response = requests.get(thumbnail_url, stream=True)
        try:
            response.raise_for_status()
            return response.content
        except requests.exceptions.HTTPError:
            return None
