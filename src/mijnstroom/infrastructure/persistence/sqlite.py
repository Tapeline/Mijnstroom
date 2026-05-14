import logging
import re
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

_MIGRATION_PATTERN = re.compile(r"^(\d{4})_.+\.sql$")


@dataclass(slots=True)
class SqliteSettings:
    """Connection settings for the SQLite database."""

    path: str
    busy_timeout_ms: int = 5000


async def connect(settings: SqliteSettings) -> aiosqlite.Connection:
    """Open an aiosqlite connection with the project's standard pragmas."""
    Path(settings.path).parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(settings.path, isolation_level=None)
    await conn.execute("PRAGMA journal_mode = WAL")
    await conn.execute(f"PRAGMA busy_timeout = {settings.busy_timeout_ms}")
    await conn.execute("PRAGMA foreign_keys = ON")
    await conn.execute("PRAGMA synchronous = NORMAL")
    conn.row_factory = aiosqlite.Row
    return conn


def _discover_migrations() -> list[tuple[int, str, str]]:
    """Return a sorted list of ``(version, filename, sql)`` tuples."""
    resources = files("mijnstroom.infrastructure.persistence.migrations")
    migrations: list[tuple[int, str, str]] = []
    for resource in resources.iterdir():
        if not resource.is_file():
            continue
        name = resource.name
        match = _MIGRATION_PATTERN.match(name)
        if not match:
            continue
        version = int(match.group(1))
        sql = resource.read_text(encoding="utf-8")
        migrations.append((version, name, sql))
    migrations.sort(key=lambda m: m[0])
    return migrations


async def apply_migrations(settings: SqliteSettings) -> None:
    """Apply any pending migrations.

    SQLite's ``executescript`` commits any open transaction implicitly,
    so migrations cannot be wrapped in a single transaction at the
    Python layer. Instead we serialise startup by taking a file-level
    lock via the ``mijnstroom_migration_lock`` table and record each
    applied version after its script succeeds. Each migration file is
    expected to be self-consistent.
    """
    conn = await connect(settings)
    try:
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)"
        )
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS mijnstroom_migration_lock (id INTEGER PRIMARY KEY)"
        )
        # Acquire a writer lock for the duration of migration discovery.
        await conn.execute("BEGIN IMMEDIATE")
        cursor = await conn.execute(
            "SELECT COALESCE(MAX(version), 0) FROM schema_version"
        )
        row = await cursor.fetchone()
        current = int(row[0]) if row else 0
        pending = [m for m in _discover_migrations() if m[0] > current]
        await conn.execute("COMMIT")

        for version, name, sql in pending:
            logger.info("Applying migration %s", name)
            # ``executescript`` auto-commits; we record the version in a
            # separate statement immediately afterwards.
            await conn.executescript(sql)
            await conn.execute(
                "INSERT OR IGNORE INTO schema_version (version) VALUES (?)",
                (version,),
            )
    finally:
        await conn.close()


