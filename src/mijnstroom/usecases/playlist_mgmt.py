import uuid
from dataclasses import dataclass, replace
from enum import Enum

from mijnstroom.data import Playlist, Track
from mijnstroom.errors import NotFoundError
from mijnstroom.storage import LockedStorage


@dataclass
class CreatePlaylistRequest:
    title: str
    artist: str
    year: int
    genre: str
    tracks: list[str]


@dataclass
class CreatePlaylistInLibrary:
    storage: LockedStorage

    def __call__(self, request: CreatePlaylistRequest) -> Playlist:
        with self.storage.for_update() as session:
            playlist = Playlist(
                uid=str(uuid.uuid4()),
                title=request.title,
                artist=request.artist,
                year=request.year,
                genre=request.genre,
                tracks=request.tracks,
            )
            _ensure_all_tracks_exist(request.tracks, session.tracks)
            session.save_all_playlists(
                {**session.playlists, playlist.uid: playlist}
            )
            return playlist


@dataclass
class UpdatePlaylistMetaRequest:
    title: str | None = None
    artist: str | None = None
    year: int | None = None
    genre: str | None = None


@dataclass
class UpdatePlaylistMetaInLibrary:
    storage: LockedStorage

    def __call__(
        self,
        uid: str,
        request: UpdatePlaylistMetaRequest
    ) -> Playlist:
        with self.storage.for_update() as session:
            playlist = session.playlists.get(uid)
            if not playlist:
                raise NotFoundError("Playlist not found")
            playlist = replace(
                playlist,
                title=request.title or playlist.title,
                artist=request.artist or playlist.artist,
                year=request.year or playlist.year,
                genre=request.genre or playlist.genre,
            )
            session.save_all_playlists(
                {**session.playlists, playlist.uid: playlist}
            )
            return playlist


class UpdatePlaylistTracksAction(Enum):
    INSERT = "insert"
    SET = "set"
    REMOVE = "remove"


@dataclass
class UpdatePlaylistTracksRequest:
    tracks: list[str]
    operation: UpdatePlaylistTracksAction


@dataclass
class UpdatePlaylistTracksInLibrary:
    storage: LockedStorage

    def __call__(
        self,
        uid: str,
        request: UpdatePlaylistTracksRequest
    ) -> Playlist:
        with self.storage.for_update() as session:
            playlist = session.playlists.get(uid)
            if not playlist:
                raise NotFoundError("Playlist not found")
            if request.operation == UpdatePlaylistTracksAction.SET:
                playlist = replace(
                    playlist, tracks=request.tracks
                )
            elif request.operation == UpdatePlaylistTracksAction.INSERT:
                playlist = replace(
                    playlist, tracks=playlist.tracks + request.tracks
                )
            elif request.operation == UpdatePlaylistTracksAction.REMOVE:
                to_remove = set(request.tracks)
                playlist = replace(
                    playlist, tracks=[
                        track for track in playlist.tracks
                        if track not in to_remove
                    ]
                )
            _ensure_all_tracks_exist(playlist.tracks, session.tracks)
            session.save_all_playlists(
                {**session.playlists, playlist.uid: playlist}
            )
            return playlist


@dataclass
class DeletePlaylistFromLibrary:
    storage: LockedStorage

    def __call__(self, uid: str) -> None:
        with self.storage.for_update() as session:
            playlists = session.playlists
            playlists.pop(uid, None)
            session.save_all_playlists(playlists)


@dataclass
class DeleteTrackFromLibrary:
    storage: LockedStorage

    def __call__(self, uid: str) -> None:
        with self.storage.for_update() as session:
            playlists = session.playlists
            tracks = session.tracks
            for playlist_id in playlists:
                playlists[playlist_id] = replace(
                    playlists[playlist_id],
                    tracks=[
                        track
                        for track in playlists[playlist_id].tracks
                        if track != uid
                    ]
                )
            tracks.pop(uid, None)
            session.save_all_playlists(playlists)
            session.save_all_tracks(playlists)


def _ensure_all_tracks_exist(ids: list[str], tracks: dict[str, Track]) -> None:
    for uid in ids:
        if uid not in tracks:
            raise NotFoundError(f"Track {uid} not found")
