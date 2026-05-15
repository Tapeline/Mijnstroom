from datetime import datetime

import aiosqlite

from mijnstroom.application.interfaces.repos import TrackPatch, TrackQuery, TrackRepo
from mijnstroom.domain.audio import AudioFormat
from mijnstroom.domain.track import Track, TrackId
from mijnstroom.infrastructure.persistence.transaction import SqliteTransaction


def _row_to_track(row: aiosqlite.Row) -> Track:
    return Track(
        id=TrackId(row["id"]),
        storage_path=row["storage_path"],
        format=AudioFormat(row["format"]),
        duration_ms=row["duration_ms"],
        title=row["title"],
        artist=row["artist"],
        album=row["album"],
        year=row["year"],
        genre=row["genre"],
        cover_path=row["cover_path"],
        lyrics=row["lyrics"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


class SqliteTrackRepo(TrackRepo):
    """Hand-written SQL track repository on top of the active transaction."""

    __slots__ = ("_tx",)

    def __init__(self, tx: SqliteTransaction) -> None:
        self._tx = tx

    async def insert(self, track: Track) -> None:
        conn = await self._tx.connection()
        await conn.execute(
            """
            INSERT INTO tracks (
                id, storage_path, format, duration_ms, title, artist,
                album, year, genre, cover_path, lyrics, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                track.id,
                track.storage_path,
                track.format.value,
                track.duration_ms,
                track.title,
                track.artist,
                track.album,
                track.year,
                track.genre,
                track.cover_path,
                track.lyrics,
                track.created_at.isoformat(),
            ),
        )

    async def get(self, id: TrackId) -> Track | None:
        conn = await self._tx.connection()
        cursor = await conn.execute("SELECT * FROM tracks WHERE id = ?", (id,))
        row = await cursor.fetchone()
        return _row_to_track(row) if row else None

    async def list_all(self, query: TrackQuery) -> list[Track]:
        conn = await self._tx.connection()
        params: list[object] = []
        sql = "SELECT * FROM tracks"
        if query.search:
            like = f"%{query.search}%"
            sql += " WHERE title LIKE ? OR artist LIKE ? OR album LIKE ?"
            params.extend([like, like, like])
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([query.limit, query.offset])
        cursor = await conn.execute(sql, params)
        rows = await cursor.fetchall()
        return [_row_to_track(r) for r in rows]

    async def update(self, track: Track) -> None:
        conn = await self._tx.connection()
        await conn.execute(
            """
            UPDATE tracks SET
                storage_path = ?, format = ?, duration_ms = ?, title = ?,
                artist = ?, album = ?, year = ?, genre = ?, cover_path = ?,
                lyrics = ?
            WHERE id = ?
            """,
            (
                track.storage_path,
                track.format.value,
                track.duration_ms,
                track.title,
                track.artist,
                track.album,
                track.year,
                track.genre,
                track.cover_path,
                track.lyrics,
                track.id,
            ),
        )

    async def delete(self, id: TrackId) -> None:
        conn = await self._tx.connection()
        await conn.execute("DELETE FROM tracks WHERE id = ?", (id,))

    async def apply_patch(self, ids: list[TrackId], patch: TrackPatch) -> int:
        """Bulk-apply ``patch`` to multiple tracks; returns affected row count."""
        if not ids:
            return 0
        sets: list[str] = []
        params: list[object] = []
        for field, value in (
            ("title", patch.title),
            ("artist", patch.artist),
            ("album", patch.album),
            ("year", patch.year),
            ("genre", patch.genre),
            ("cover_path", patch.cover_path),
            ("lyrics", patch.lyrics),
        ):
            if value is not None:
                sets.append(f"{field} = ?")
                params.append(value)
        if not sets:
            return 0
        placeholders = ",".join(["?"] * len(ids))
        sql = f"UPDATE tracks SET {', '.join(sets)} WHERE id IN ({placeholders})"
        params.extend(ids)
        conn = await self._tx.connection()
        cursor = await conn.execute(sql, params)
        return cursor.rowcount or 0
