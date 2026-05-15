from mijnstroom.application.interfaces.idp import UserIdProvider
from mijnstroom.application.interfaces.repos import PlaylistRepo, TrackRepo
from mijnstroom.application.interfaces.tx import Transaction
from mijnstroom.application.playlists.dto import TrackPlaylistInput
from mijnstroom.common.decorators import interactor
from mijnstroom.common.errors import NotFound
from mijnstroom.domain.playlist import PlaylistId
from mijnstroom.domain.track import TrackId


@interactor
class AddTrackToPlaylist:
    playlists: PlaylistRepo
    tracks: TrackRepo
    tx: Transaction
    idp: UserIdProvider

    async def __call__(self, input: TrackPlaylistInput) -> None:
        async with self.tx:
            await self.idp.require_user()
            playlist = await self.playlists.get(PlaylistId(input.playlist_id))
            if playlist is None:
                raise NotFound(f"Playlist {input.playlist_id} does not exist")
            track = await self.tracks.get(TrackId(input.track_id))
            if track is None:
                raise NotFound(f"Track {input.track_id} does not exist")
            await self.playlists.add_track(playlist.id, track.id)


@interactor
class RemoveTrackFromPlaylist:
    playlists: PlaylistRepo
    tx: Transaction
    idp: UserIdProvider

    async def __call__(self, input: TrackPlaylistInput) -> None:
        async with self.tx:
            await self.idp.require_user()
            playlist = await self.playlists.get(PlaylistId(input.playlist_id))
            if playlist is None:
                raise NotFound(f"Playlist {input.playlist_id} does not exist")
            await self.playlists.remove_track(playlist.id, TrackId(input.track_id))
