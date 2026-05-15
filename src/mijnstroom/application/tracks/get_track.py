from mijnstroom.application.interfaces.idp import UserIdProvider
from mijnstroom.application.interfaces.repos import TrackRepo
from mijnstroom.application.interfaces.tx import Transaction
from mijnstroom.common.decorators import interactor
from mijnstroom.common.errors import NotFound
from mijnstroom.domain.track import Track, TrackId


@interactor
class GetTrack:
    """Fetch a single track by id."""

    repo: TrackRepo
    tx: Transaction
    idp: UserIdProvider

    async def __call__(self, track_id: str) -> Track:
        async with self.tx:
            await self.idp.require_user()
            track = await self.repo.get(TrackId(track_id))
            if track is None:
                raise NotFound(f"Track {track_id} does not exist")
            return track
