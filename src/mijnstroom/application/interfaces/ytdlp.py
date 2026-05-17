from abc import abstractmethod
from typing import Protocol

from mijnstroom.common.decorators import dto


@dto
class YtChapter:
    start_ms: int
    end_ms: int
    title: str


@dto
class YtVideoInfo:
    id: str
    url: str
    title: str
    uploader: str | None
    upload_date: str | None  # YYYYMMDD
    duration_ms: int | None
    description: str | None
    thumbnail_url: str | None
    chapters: tuple[YtChapter, ...]


@dto
class YtPlaylistEntry:
    id: str
    url: str
    title: str
    uploader: str | None
    duration_ms: int | None
    thumbnail_url: str | None


@dto
class YtPlaylistInfo:
    id: str
    url: str
    title: str
    entries: tuple[YtPlaylistEntry, ...]


@dto
class YtSearchResult:
    id: str
    url: str
    title: str
    uploader: str | None
    duration_ms: int | None
    thumbnail_url: str | None


class YoutubeClient(Protocol):
    @abstractmethod
    async def search(self, query: str, limit: int = 20) -> list[YtSearchResult]: ...

    @abstractmethod
    async def video_info(self, url: str) -> YtVideoInfo: ...

    @abstractmethod
    async def playlist_info(self, url: str) -> YtPlaylistInfo: ...

    @abstractmethod
    async def download_audio(self, url: str, dest_path: str) -> str:
        """Download best audio; return the resulting file path (may differ)."""

    @abstractmethod
    async def try_download_cover(self, url: str, dest_path: str) -> str | None:
        ...
