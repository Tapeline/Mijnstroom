from mijnstroom.application.interfaces.idp import UserIdProvider
from mijnstroom.application.interfaces.repos import PlaylistRepo
from mijnstroom.application.interfaces.tx import Transaction
from mijnstroom.common.decorators import interactor
from mijnstroom.common.errors import NotFound
from mijnstroom.domain.playlist import PlaylistId


@interactor
class DeletePlaylist:
    repo: PlaylistRepo
    tx: Transaction
    idp: UserIdProvider

    async def __call__(self, playlist_id: str) -> None:
        async with self.tx:
            await self.idp.require_user()
            existing = await self.repo.get(PlaylistId(playlist_id))
            if existing is None:
                raise NotFound(f"Playlist {playlist_id} does not exist")
            await self.repo.delete(existing.id)
