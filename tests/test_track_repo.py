from datetime import UTC, datetime

import pytest

from mijnstroom.application.interfaces.repos import TrackQuery
from mijnstroom.common.ids import generate_id
from mijnstroom.domain.audio import AudioFormat
from mijnstroom.domain.track import Track, TrackId
from mijnstroom.infrastructure.persistence.sqlite import SqliteSettings, apply_migrations
from mijnstroom.infrastructure.persistence.track_repo import SqliteTrackRepo
from mijnstroom.infrastructure.persistence.transaction import SqliteTransaction


def _make_track(title: str = "Hello", artist: str | None = "Artist") -> Track:
    return Track(
        id=generate_id(TrackId),
        storage_path=f"/data/tracks/{title}.m4a",
        format=AudioFormat.AAC,
        duration_ms=1000,
        title=title,
        artist=artist,
        album="Album",
        year=2024,
        genre="Pop",
        cover_path=None,
        lyrics=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_track_repo_insert_get(db_path: str) -> None:
    settings = SqliteSettings(path=db_path)
    await apply_migrations(settings)
    tx = SqliteTransaction(settings)
    repo = SqliteTrackRepo(tx)
    try:
        async with tx:
            track = _make_track("My Song")
            await repo.insert(track)
            fetched = await repo.get(track.id)
        assert fetched is not None
        assert fetched.title == "My Song"
        assert fetched.artist == "Artist"
        assert fetched.format == AudioFormat.AAC
    finally:
        await tx.close()


@pytest.mark.asyncio
async def test_track_repo_search(db_path: str) -> None:
    settings = SqliteSettings(path=db_path)
    await apply_migrations(settings)
    tx = SqliteTransaction(settings)
    repo = SqliteTrackRepo(tx)
    try:
        async with tx:
            await repo.insert(_make_track("Alpha"))
            await repo.insert(_make_track("Beta"))
            await repo.insert(_make_track("Charlie"))
        async with tx:
            results = await repo.list_all(TrackQuery(search="lph"))
        assert {t.title for t in results} == {"Alpha"}
    finally:
        await tx.close()


@pytest.mark.asyncio
async def test_track_repo_delete(db_path: str) -> None:
    settings = SqliteSettings(path=db_path)
    await apply_migrations(settings)
    tx = SqliteTransaction(settings)
    repo = SqliteTrackRepo(tx)
    try:
        async with tx:
            track = _make_track()
            await repo.insert(track)
            await repo.delete(track.id)
            fetched = await repo.get(track.id)
        assert fetched is None
    finally:
        await tx.close()


@pytest.mark.asyncio
async def test_track_repo_apply_patch(db_path: str) -> None:
    from mijnstroom.application.interfaces.repos import TrackPatch

    settings = SqliteSettings(path=db_path)
    await apply_migrations(settings)
    tx = SqliteTransaction(settings)
    repo = SqliteTrackRepo(tx)
    try:
        async with tx:
            t1 = _make_track("One")
            t2 = _make_track("Two")
            await repo.insert(t1)
            await repo.insert(t2)
            count = await repo.apply_patch([t1.id, t2.id], TrackPatch(genre="Rock"))
        assert count == 2
        async with tx:
            r1 = await repo.get(t1.id)
            r2 = await repo.get(t2.id)
        assert r1 is not None and r1.genre == "Rock"
        assert r2 is not None and r2.genre == "Rock"
    finally:
        await tx.close()
