from mijnstroom.application.interfaces.idp import UserIdProvider
from mijnstroom.application.interfaces.repos import TrackPatch, TrackRepo
from mijnstroom.application.interfaces.tx import Transaction
from mijnstroom.application.tracks.dto import BulkEditMetadataInput
from mijnstroom.common.decorators import interactor
from mijnstroom.domain.track import TrackId


@interactor
class BulkEditTrackMetadata:
    """Apply a partial metadata patch to multiple tracks at once.

    Only fields for which ``apply_*`` is True are updated."""

    repo: TrackRepo
    tx: Transaction
    idp: UserIdProvider

    async def __call__(self, input: BulkEditMetadataInput) -> int:
        if not input.track_ids:
            return 0
        patch = TrackPatch(
            title=input.title if input.apply_title else None,
            artist=input.artist if input.apply_artist else None,
            album=input.album if input.apply_album else None,
            year=input.year if input.apply_year else None,
            genre=input.genre if input.apply_genre else None,
        )
        if not any(
            (
                input.apply_title,
                input.apply_artist,
                input.apply_album,
                input.apply_year,
                input.apply_genre,
            )
        ):
            return 0
        async with self.tx:
            await self.idp.require_user()
            track_ids = [TrackId(id_str) for id_str in input.track_ids]
            return await self.repo.apply_patch(track_ids, patch)
