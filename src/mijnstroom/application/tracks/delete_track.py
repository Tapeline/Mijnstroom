from mijnstroom.application.interfaces.idp import UserIdProvider
from mijnstroom.application.interfaces.repos import TrackRepo
from mijnstroom.application.interfaces.storage import FileStorage
from mijnstroom.application.interfaces.tx import Transaction
from mijnstroom.common.decorators import interactor
from mijnstroom.common.errors import NotFound
from mijnstroom.domain.track import TrackId


@interactor
class DeleteTrack:
    """Remove a track row and its on-disk audio + cover files."""

    repo: TrackRepo
    storage: FileStorage
    tx: Transaction
    idp: UserIdProvider

    async def __call__(self, track_id: str) -> None:
        async with self.tx:
            await self.idp.require_user()
            existing = await self.repo.get(TrackId(track_id))
            if existing is None:
                raise NotFound(f"Track {track_id} does not exist")
            await self.repo.delete(existing.id)
            await self.storage.delete(existing.storage_path)
            if existing.cover_path:
                await self.storage.delete(existing.cover_path)
