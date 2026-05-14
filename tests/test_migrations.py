import aiosqlite
import pytest

from mijnstroom.infrastructure.persistence.sqlite import SqliteSettings, apply_migrations


@pytest.mark.asyncio
async def test_apply_migrations_creates_tables(db_path: str) -> None:
    settings = SqliteSettings(path=db_path)
    await apply_migrations(settings)

    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        rows = await cursor.fetchall()
    names = {r[0] for r in rows}
    assert {"tracks", "playlists", "playlist_tracks", "jobs", "schema_version"}.issubset(
        names
    )


@pytest.mark.asyncio
async def test_apply_migrations_is_idempotent(db_path: str) -> None:
    settings = SqliteSettings(path=db_path)
    await apply_migrations(settings)
    await apply_migrations(settings)

    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute("SELECT MAX(version) FROM schema_version")
        row = await cursor.fetchone()
    assert row is not None
    assert row[0] == 1
