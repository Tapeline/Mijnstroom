import asyncio
import logging
from typing import Any, cast

from yt_dlp import YoutubeDL  # type: ignore[import-untyped]

from mijnstroom.application.interfaces.ytdlp import (
    YoutubeClient,
    YtChapter,
    YtPlaylistEntry,
    YtPlaylistInfo,
    YtSearchResult,
    YtVideoInfo,
)
from mijnstroom.common.errors import AppError

logger = logging.getLogger(__name__)


class YoutubeClientError(AppError):
    """Wrapper for yt-dlp failures surfaced to higher layers."""


def _ms(seconds: float | int | None) -> int | None:
    if seconds is None:
        return None
    return int(float(seconds) * 1000)


def _entry_thumbnail(info: dict[str, Any]) -> str | None:
    thumbnails = info.get("thumbnails")
    if isinstance(thumbnails, list) and thumbnails:
        last = thumbnails[-1]
        if isinstance(last, dict):
            url = last.get("url")
            if isinstance(url, str):
                return url
    thumbnail = info.get("thumbnail")
    return thumbnail if isinstance(thumbnail, str) else None


def _info_to_video(info: dict[str, Any]) -> YtVideoInfo:
    raw_chapters = info.get("chapters") or []
    chapters: list[YtChapter] = []
    if isinstance(raw_chapters, list):
        for ch in raw_chapters:
            if not isinstance(ch, dict):
                continue
            start = _ms(ch.get("start_time"))
            end = _ms(ch.get("end_time"))
            title = ch.get("title")
            if start is None or end is None or not isinstance(title, str):
                continue
            chapters.append(YtChapter(start_ms=start, end_ms=end, title=title))
    return YtVideoInfo(
        id=str(info.get("id") or ""),
        url=str(info.get("webpage_url") or info.get("url") or ""),
        title=str(info.get("title") or ""),
        uploader=info.get("uploader") if isinstance(info.get("uploader"), str) else None,
        upload_date=info.get("upload_date") if isinstance(info.get("upload_date"), str) else None,
        duration_ms=_ms(info.get("duration")),
        description=info.get("description") if isinstance(info.get("description"), str) else None,
        thumbnail_url=_entry_thumbnail(info),
        chapters=tuple(chapters),
    )


def _info_to_playlist(info: dict[str, Any]) -> YtPlaylistInfo:
    entries_raw = info.get("entries") or []
    entries: list[YtPlaylistEntry] = []
    if isinstance(entries_raw, list):
        for entry in entries_raw:
            if not isinstance(entry, dict):
                continue
            entries.append(
                YtPlaylistEntry(
                    id=str(entry.get("id") or ""),
                    url=str(entry.get("url") or entry.get("webpage_url") or ""),
                    title=str(entry.get("title") or ""),
                    uploader=entry.get("uploader")
                    if isinstance(entry.get("uploader"), str)
                    else None,
                    duration_ms=_ms(entry.get("duration")),
                    thumbnail_url=_entry_thumbnail(entry),
                )
            )
    return YtPlaylistInfo(
        id=str(info.get("id") or ""),
        url=str(info.get("webpage_url") or ""),
        title=str(info.get("title") or ""),
        entries=tuple(entries),
    )


class YtDlpYoutubeClient(YoutubeClient):
    """yt-dlp adapter implementing :class:`YoutubeClient`.

    All blocking yt-dlp work is run via :func:`asyncio.to_thread`.
    """

    __slots__ = ("_quiet",)

    def __init__(self, quiet: bool = True) -> None:
        self._quiet = quiet

    def _options(self, **extra: object) -> dict[str, object]:
        opts: dict[str, object] = {
            "quiet": self._quiet,
            "no_warnings": self._quiet,
            "skip_download": True,
        }
        opts.update(extra)
        return opts

    async def search(self, query: str, limit: int = 20) -> list[YtSearchResult]:
        def _do() -> list[YtSearchResult]:
            opts = self._options(extract_flat=True)
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
            entries = info.get("entries") if isinstance(info, dict) else None
            results: list[YtSearchResult] = []
            if not isinstance(entries, list):
                return results
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                results.append(
                    YtSearchResult(
                        id=str(entry.get("id") or ""),
                        url=str(entry.get("url") or entry.get("webpage_url") or ""),
                        title=str(entry.get("title") or ""),
                        uploader=entry.get("uploader")
                        if isinstance(entry.get("uploader"), str)
                        else None,
                        duration_ms=_ms(entry.get("duration")),
                        thumbnail_url=_entry_thumbnail(entry),
                    )
                )
            return results

        try:
            return await asyncio.to_thread(_do)
        except Exception as exc:
            raise YoutubeClientError(f"yt-dlp search failed: {exc}") from exc

    async def video_info(self, url: str) -> YtVideoInfo:
        def _do() -> YtVideoInfo:
            opts = self._options()
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            if not isinstance(info, dict):
                raise YoutubeClientError("yt-dlp returned no info for video")
            return _info_to_video(info)

        try:
            return await asyncio.to_thread(_do)
        except Exception as exc:
            raise YoutubeClientError(f"yt-dlp video info failed: {exc}") from exc

    async def playlist_info(self, url: str) -> YtPlaylistInfo:
        def _do() -> YtPlaylistInfo:
            opts = self._options(extract_flat=True)
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            if not isinstance(info, dict):
                raise YoutubeClientError("yt-dlp returned no info for playlist")
            return _info_to_playlist(info)

        try:
            return await asyncio.to_thread(_do)
        except Exception as exc:
            raise YoutubeClientError(f"yt-dlp playlist info failed: {exc}") from exc

    async def download_audio(self, url: str, dest_path: str) -> str:
        def _do() -> str:
            # ``dest_path`` is the desired prefix; yt-dlp picks the actual
            # extension. We let it write to ``<dest_path>.%(ext)s`` and
            # return the resulting filename.
            outtmpl = dest_path + ".%(ext)s"
            opts = self._options(
                skip_download=False,
                outtmpl=outtmpl,
                format="bestaudio/best",
                noprogress=True,
            )
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not isinstance(info, dict):
                    raise YoutubeClientError("yt-dlp returned no info for download")
                filename = ydl.prepare_filename(info)
                return cast(str, filename)

        try:
            return await asyncio.to_thread(_do)
        except Exception as exc:
            raise YoutubeClientError(f"yt-dlp download failed: {exc}") from exc

    async def try_download_cover(self, url: str, dest_path: str) -> str | None:
        def _do() -> str:
            outtmpl = dest_path + ".%(ext)s"
            opts = self._options(
                skip_download=True,
                outtmpl=outtmpl,
                writethumbnail=True,
            )
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not isinstance(info, dict):
                    raise YoutubeClientError("yt-dlp returned no info for download")
                # WRITE HERE
                return cast(str, filename)
        try:
            return await asyncio.to_thread(_do)
        except Exception as exc:
            print(exc)
            return None
