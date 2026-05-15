from dataclasses import replace

from mijnstroom.application.interfaces.audio import TagWriter
from mijnstroom.application.interfaces.idp import UserIdProvider
from mijnstroom.application.interfaces.repos import TrackRepo
from mijnstroom.application.interfaces.storage import FileStorage
from mijnstroom.application.interfaces.tx import Transaction
from mijnstroom.application.tracks.dto import EditMetadataInput
from mijnstroom.common.decorators import interactor
from mijnstroom.common.errors import NotFound, ValidationError
from mijnstroom.domain.track import Track, TrackId


@interactor
class EditTrackMetadata:
    """Update metadata for an existing track and rewrite embedded tags."""

    repo: TrackRepo
    storage: FileStorage
    tags: TagWriter
    tx: Transaction
    idp: UserIdProvider

    async def __call__(self, input: EditMetadataInput) -> Track:
        if not input.title.strip():
            raise ValidationError("Track title cannot be blank")

        async with self.tx:
            await self.idp.require_user()
            existing = await self.repo.get(TrackId(input.track_id))
            if existing is None:
                raise NotFound(f"Track {input.track_id} does not exist")

            cover_path = existing.cover_path
            if input.clear_cover and cover_path is not None:
                await self.storage.delete(cover_path)
                cover_path = None
            if input.cover_bytes:
                cover_path = await self.storage.write_cover(input.cover_bytes, existing.id)

            updated = replace(
                existing,
                title=input.title.strip(),
                artist=input.artist,
                album=input.album,
                year=input.year,
                genre=input.genre,
                cover_path=cover_path,
                lyrics=input.lyrics,
            )
            await self.repo.update(updated)
            await self.tags.write_tags(
                updated.storage_path,
                title=updated.title,
                artist=updated.artist,
                album=updated.album,
                year=updated.year,
                genre=updated.genre,
                cover_path=updated.cover_path,
                lyrics=updated.lyrics,
            )
        return updated
