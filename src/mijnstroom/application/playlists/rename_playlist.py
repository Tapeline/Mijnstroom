from dataclasses import replace

from mijnstroom.application.interfaces.idp import UserIdProvider
from mijnstroom.application.interfaces.repos import PlaylistRepo
from mijnstroom.application.interfaces.tx import Transaction
from mijnstroom.application.playlists.dto import RenamePlaylistInput
from mijnstroom.common.decorators import interactor
from mijnstroom.common.errors import NotFound, ValidationError
from mijnstroom.domain.playlist import Playlist, PlaylistId


@interactor
class RenamePlaylist:
    repo: PlaylistRepo
    tx: Transaction
    idp: UserIdProvider

    async def __call__(self, input: RenamePlaylistInput) -> Playlist:
        if not input.name.strip():
            raise ValidationError("Playlist name cannot be blank")
        async with self.tx:
            await self.idp.require_user()
            existing = await self.repo.get(PlaylistId(input.playlist_id))
            if existing is None:
                raise NotFound(f"Playlist {input.playlist_id} does not exist")
            await self.repo.rename(existing.id, input.name.strip())
            return replace(existing, name=input.name.strip())
