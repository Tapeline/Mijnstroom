from mijnstroom.application.interfaces.idp import UserIdProvider
from mijnstroom.application.interfaces.repos import PlaylistRepo, TrackRepo
from mijnstroom.application.interfaces.tx import Transaction
from mijnstroom.common.decorators import interactor
from mijnstroom.common.errors import NotFound
from mijnstroom.domain.playlist import Playlist, PlaylistId
from mijnstroom.domain.track import Track


@interactor
class ListPlaylists:
    repo: PlaylistRepo
    tx: Transaction
    idp: UserIdProvider

    async def __call__(self) -> list[Playlist]:
        async with self.tx:
            await self.idp.require_user()
            return await self.repo.list_all()


@interactor
class GetPlaylistWithTracks:
    """Return a playlist together with its ordered list of tracks."""

    playlists: PlaylistRepo
    tracks: TrackRepo
    tx: Transaction
    idp: UserIdProvider

    async def __call__(self, playlist_id: str) -> tuple[Playlist, list[Track]]:
        async with self.tx:
            await self.idp.require_user()
            playlist = await self.playlists.get(PlaylistId(playlist_id))
            if playlist is None:
                raise NotFound(f"Playlist {playlist_id} does not exist")
            track_ids = await self.playlists.list_tracks(playlist.id)
            ordered: list[Track] = []
            for tid in track_ids:
                track = await self.tracks.get(tid)
                if track is not None:
                    ordered.append(track)
            return playlist, ordered
