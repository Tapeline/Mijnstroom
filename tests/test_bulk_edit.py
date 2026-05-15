from datetime import UTC, datetime

import pytest

from mijnstroom.application.interfaces.idp import UserId, UserIdProvider
from mijnstroom.application.tracks.bulk_edit_metadata import BulkEditTrackMetadata
from mijnstroom.application.tracks.dto import BulkEditMetadataInput
from mijnstroom.common.ids import generate_id
from mijnstroom.domain.audio import AudioFormat
from mijnstroom.domain.track import Track, TrackId
from mijnstroom.infrastructure.persistence.sqlite import SqliteSettings, apply_migrations
from mijnstroom.infrastructure.persistence.track_repo import SqliteTrackRepo
from mijnstroom.infrastructure.persistence.transaction import SqliteTransaction


class _StaticIdp(UserIdProvider):
    async def current_user(self) -> UserId | None:
        return UserId("me")

    async def require_user(self) -> UserId:
        return UserId("me")


def _track(title: str = "T") -> Track:
    return Track(
        id=generate_id(TrackId),
        storage_path=f"/data/tracks/{title}.m4a",
        format=AudioFormat.AAC,
        duration_ms=1000,
        title=title,
        artist=None,
        album=None,
        year=None,
        genre=None,
        cover_path=None,
        lyrics=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_bulk_edit_applies_only_checked_fields(db_path: str) -> None:
    settings = SqliteSettings(path=db_path)
    await apply_migrations(settings)
    tx = SqliteTransaction(settings)
    repo = SqliteTrackRepo(tx)
    interactor = BulkEditTrackMetadata(repo=repo, tx=tx, idp=_StaticIdp())
    try:
        async with tx:
            t1 = _track("One")
            t2 = _track("Two")
            await repo.insert(t1)
            await repo.insert(t2)
        affected = await interactor(
            BulkEditMetadataInput(
                track_ids=(t1.id, t2.id),
                title="Should not stick",
                apply_title=False,
                artist="The Beatles",
                apply_artist=True,
                year=1969,
                apply_year=True,
            )
        )
        assert affected == 2
        async with tx:
            r1 = await repo.get(t1.id)
            r2 = await repo.get(t2.id)
        assert r1 is not None and r1.artist == "The Beatles"
        assert r1.year == 1969
        assert r1.title == "One"  # title not changed
        assert r2 is not None and r2.artist == "The Beatles"
    finally:
        await tx.close()


@pytest.mark.asyncio
async def test_bulk_edit_no_apply_no_change(db_path: str) -> None:
    settings = SqliteSettings(path=db_path)
    await apply_migrations(settings)
    tx = SqliteTransaction(settings)
    repo = SqliteTrackRepo(tx)
    interactor = BulkEditTrackMetadata(repo=repo, tx=tx, idp=_StaticIdp())
    try:
        async with tx:
            t = _track("Untouched")
            await repo.insert(t)
        affected = await interactor(
            BulkEditMetadataInput(
                track_ids=(t.id,),
                title="anything",
                # No apply_* flags set.
            )
        )
        assert affected == 0
    finally:
        await tx.close()
