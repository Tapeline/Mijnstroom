from mijnstroom.application.interfaces.idp import UserIdProvider
from mijnstroom.application.interfaces.repos import PlaylistRepo
from mijnstroom.application.interfaces.tx import Transaction
from mijnstroom.application.playlists.dto import CreatePlaylistInput
from mijnstroom.common.decorators import interactor
from mijnstroom.common.ids import generate_id
from mijnstroom.common.time import Clock
from mijnstroom.domain.playlist import Playlist, PlaylistId


@interactor
class CreatePlaylist:
    repo: PlaylistRepo
    tx: Transaction
    idp: UserIdProvider
    clock: Clock

    async def __call__(self, input: CreatePlaylistInput) -> Playlist:
        async with self.tx:
            await self.idp.require_user()
            playlist = Playlist(
                id=generate_id(PlaylistId),
                name=input.name.strip(),
                created_at=self.clock.now(),
            )
            await self.repo.insert(playlist)
            return playlist
