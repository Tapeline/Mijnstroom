from dataclasses import dataclass

from mijnstroom.data import Playlist, Track
from mijnstroom.errors import NotFoundError
from mijnstroom.storage import LockedStorage


@dataclass
class SearchRequest:
    title_like: str | None = None
    artist_like: str | None = None
    album_like: str | None = None
    include_unset: bool = False


@dataclass
class SearchTracksInLibrary:
    storage: LockedStorage

    def __call__(self, request: SearchRequest) -> list[Track]:
        with self.storage.for_select() as session:
            return [
                track for track in session.tracks.values()
                if
                _filter_like(
                    track.title,
                    request.title_like,
                    request.include_unset
                ) and
                _filter_like(
                    track.album,
                    request.album_like,
                    request.include_unset
                ) and
                _filter_like(
                    track.artist,
                    request.artist_like,
                    request.include_unset
                )
            ]


@dataclass
class SearchPlaylistsInLibrary:
    storage: LockedStorage

    def __call__(self, request: SearchRequest) -> list[Playlist]:
        with self.storage.for_select() as session:
            return [
                playlist for playlist in session.playlists.values()
                if
                _filter_like(
                    playlist.title,
                    request.title_like,
                    request.include_unset
                ) and
                _filter_like(
                    playlist.album,
                    request.album_like,
                    request.include_unset
                ) and
                _filter_like(
                    playlist.artist,
                    request.artist_like,
                    request.include_unset
                )
            ]


@dataclass
class GetTrackInLibrary:
    storage: LockedStorage

    def __call__(self, uid: str) -> Track:
        with self.storage.for_select() as session:
            track = session.tracks.get(uid)
            if not track:
                raise NotFoundError("Track not found")
            return track



@dataclass
class GetTrackFormatsInLibrary:
    storage: LockedStorage

    def __call__(self, uid: str) -> list[str]:
        with self.storage.for_select() as session:
            track = session.tracks.get(uid)
            if not track:
                raise NotFoundError("Track not found")
            return list(session.list_formats(uid).keys())


@dataclass
class DownloadFileFromLibrary:
    storage: LockedStorage

    def __call__(self, uid: str, fmt: str) -> Path:
        with self.storage.for_select() as session:
            formats = session.list_formats(uid)
            if fmt not in formats:
                raise NotFoundError("Format not found")
            return formats[fmt]


@dataclass
class GetCoverInLibrary:
    storage: LockedStorage

    def __call__(self, uid: str) -> Path:
        with self.storage.for_select() as session:
            track = session.tracks.get(uid)
            if not track:
                raise NotFoundError("Track not found")
            cover = session.cover_for(uid)
            if not cover.exists():
                raise NotFoundError("No cover")
            return cover


@dataclass
class GetPlaylistInLibrary:
    storage: LockedStorage

    def __call__(self, uid: str) -> Playlist:
        with self.storage.for_select() as session:
            playlist = session.playlists.get(uid)
            if not playlist:
                raise NotFoundError("Playlist not found")
            return playlist


def _filter_like(
    field: str | None,
    filter_like: str | None,
    include_unset: bool
) -> bool:
    if field is None:
        return include_unset
    if filter_like is None:
        return True
    return filter_like in field
