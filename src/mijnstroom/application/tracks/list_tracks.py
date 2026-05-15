from mijnstroom.application.interfaces.idp import UserIdProvider
from mijnstroom.application.interfaces.repos import TrackQuery, TrackRepo
from mijnstroom.application.interfaces.tx import Transaction
from mijnstroom.common.decorators import interactor
from mijnstroom.domain.track import Track


@interactor
class ListTracks:
    """List tracks, optionally filtered by free-text search."""

    repo: TrackRepo
    tx: Transaction
    idp: UserIdProvider

    async def __call__(self, query: TrackQuery) -> list[Track]:
        async with self.tx:
            await self.idp.require_user()
            return await self.repo.list_all(query)
