from datetime import UTC, datetime

import pytest

from mijnstroom.common.errors import ValidationError
from mijnstroom.common.ids import generate_id
from mijnstroom.domain.audio import AudioFormat
from mijnstroom.domain.playlist import Playlist, PlaylistId
from mijnstroom.domain.track import Track, TrackId
from mijnstroom.infrastructure.persistence.playlist_repo import SqlitePlaylistRepo
from mijnstroom.infrastructure.persistence.sqlite import SqliteSettings, apply_migrations
from mijnstroom.infrastructure.persistence.track_repo import SqliteTrackRepo
from mijnstroom.infrastructure.persistence.transaction import SqliteTransaction


def _now() -> datetime:
    return datetime(2026, 1, 1, tzinfo=UTC)


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
        created_at=_now(),
    )


@pytest.mark.asyncio
async def test_playlist_crud(db_path: str) -> None:
    settings = SqliteSettings(path=db_path)
    await apply_migrations(settings)
    tx = SqliteTransaction(settings)
    repo = SqlitePlaylistRepo(tx)
    try:
        async with tx:
            playlist = Playlist(
                id=generate_id(PlaylistId),
                name="My Mix",
                created_at=_now(),
            )
            await repo.insert(playlist)
            fetched = await repo.get(playlist.id)
            assert fetched is not None
            assert fetched.name == "My Mix"

            await repo.rename(playlist.id, "Renamed")
            renamed = await repo.get(playlist.id)
            assert renamed is not None and renamed.name == "Renamed"

            all_p = await repo.list_all()
            assert any(p.id == playlist.id for p in all_p)

            await repo.delete(playlist.id)
            assert await repo.get(playlist.id) is None
    finally:
        await tx.close()


@pytest.mark.asyncio
async def test_playlist_track_membership(db_path: str) -> None:
    settings = SqliteSettings(path=db_path)
    await apply_migrations(settings)
    tx = SqliteTransaction(settings)
    p_repo = SqlitePlaylistRepo(tx)
    t_repo = SqliteTrackRepo(tx)
    try:
        async with tx:
            t1 = _track("One")
            t2 = _track("Two")
            await t_repo.insert(t1)
            await t_repo.insert(t2)
            playlist = Playlist(id=generate_id(PlaylistId), name="Mix", created_at=_now())
            await p_repo.insert(playlist)
            await p_repo.add_track(playlist.id, t1.id)
            await p_repo.add_track(playlist.id, t2.id)

            order = await p_repo.list_tracks(playlist.id)
            assert order == [t1.id, t2.id]

            await p_repo.remove_track(playlist.id, t1.id)
            order = await p_repo.list_tracks(playlist.id)
            assert order == [t2.id]
    finally:
        await tx.close()


@pytest.mark.asyncio
async def test_playlist_delete_cascades_membership(db_path: str) -> None:
    settings = SqliteSettings(path=db_path)
    await apply_migrations(settings)
    tx = SqliteTransaction(settings)
    p_repo = SqlitePlaylistRepo(tx)
    t_repo = SqliteTrackRepo(tx)
    try:
        async with tx:
            track = _track("Hello")
            await t_repo.insert(track)
            playlist = Playlist(id=generate_id(PlaylistId), name="Mix", created_at=_now())
            await p_repo.insert(playlist)
            await p_repo.add_track(playlist.id, track.id)
            await p_repo.delete(playlist.id)
            # The track must still exist; only the membership row is gone.
            assert await t_repo.get(track.id) is not None
    finally:
        await tx.close()


def test_playlist_blank_name_rejected() -> None:
    with pytest.raises(ValidationError):
        Playlist(id=generate_id(PlaylistId), name="   ", created_at=_now())
