from abc import abstractmethod
from typing import Protocol

from mijnstroom.common.decorators import dto
from mijnstroom.domain.job import Job, JobId, JobStatus
from mijnstroom.domain.playlist import Playlist, PlaylistId
from mijnstroom.domain.track import Track, TrackId


@dto
class TrackQuery:
    """Filters for listing tracks."""

    search: str | None = None
    limit: int = 100
    offset: int = 0


@dto
class TrackPatch:
    """Partial update for a track. ``None`` fields are left untouched.

    The presentation layer is responsible for distinguishing
    "field not present" from "set to NULL"; that distinction is encoded
    explicitly in the corresponding bulk-edit DTO.
    """

    title: str | None = None
    artist: str | None = None
    album: str | None = None
    year: int | None = None
    genre: str | None = None
    cover_path: str | None = None
    lyrics: str | None = None


class TrackRepo(Protocol):
    @abstractmethod
    async def insert(self, track: Track) -> None: ...

    @abstractmethod
    async def get(self, id: TrackId) -> Track | None: ...

    @abstractmethod
    async def list_all(self, query: TrackQuery) -> list[Track]: ...

    @abstractmethod
    async def update(self, track: Track) -> None: ...

    @abstractmethod
    async def delete(self, id: TrackId) -> None: ...

    @abstractmethod
    async def apply_patch(self, ids: list[TrackId], patch: TrackPatch) -> int: ...


class PlaylistRepo(Protocol):
    @abstractmethod
    async def insert(self, playlist: Playlist) -> None: ...

    @abstractmethod
    async def get(self, id: PlaylistId) -> Playlist | None: ...

    @abstractmethod
    async def list_all(self) -> list[Playlist]: ...

    @abstractmethod
    async def rename(self, id: PlaylistId, name: str) -> None: ...

    @abstractmethod
    async def delete(self, id: PlaylistId) -> None: ...

    @abstractmethod
    async def add_track(self, id: PlaylistId, track_id: TrackId) -> None: ...

    @abstractmethod
    async def remove_track(self, id: PlaylistId, track_id: TrackId) -> None: ...

    @abstractmethod
    async def list_tracks(self, id: PlaylistId) -> list[TrackId]: ...

    #@abstractmethod
    #async def list_with_track_membership(self, track_id: TrackId) -> list[tuple[Playlist, bool]]: ...

    #@abstractmethod
    #async def toggle_track(self, id: PlaylistId, track_id: TrackId, add: bool) -> None: ...


class JobRepo(Protocol):
    @abstractmethod
    async def insert(self, job: Job) -> None: ...

    @abstractmethod
    async def get(self, id: JobId) -> Job | None: ...

    @abstractmethod
    async def list_by_status(self, status: JobStatus) -> list[Job]: ...

    @abstractmethod
    async def claim_next(self) -> Job | None: ...

    @abstractmethod
    async def mark_running(self, id: JobId) -> None: ...

    @abstractmethod
    async def mark_done(self, id: JobId) -> None: ...

    @abstractmethod
    async def mark_failed(self, id: JobId, error: str) -> None: ...

    @abstractmethod
    async def cancel_pending(self, id: JobId) -> bool: ...

    @abstractmethod
    async def delete(self, id: JobId) -> None: ...
