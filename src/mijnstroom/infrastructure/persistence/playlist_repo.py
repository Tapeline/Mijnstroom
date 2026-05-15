from datetime import datetime

import aiosqlite

from mijnstroom.application.interfaces.repos import PlaylistRepo
from mijnstroom.domain.playlist import Playlist, PlaylistId
from mijnstroom.domain.track import TrackId
from mijnstroom.infrastructure.persistence.transaction import SqliteTransaction


def _row_to_playlist(row: aiosqlite.Row) -> Playlist:
    return Playlist(
        id=PlaylistId(row["id"]),
        name=row["name"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


class SqlitePlaylistRepo(PlaylistRepo):
    """Playlist repository backed by SQLite."""

    __slots__ = ("_tx",)

    def __init__(self, tx: SqliteTransaction) -> None:
        self._tx = tx

    async def insert(self, playlist: Playlist) -> None:
        conn = await self._tx.connection()
        await conn.execute(
            "INSERT INTO playlists (id, name, created_at) VALUES (?, ?, ?)",
            (playlist.id, playlist.name, playlist.created_at.isoformat()),
        )

    async def get(self, id: PlaylistId) -> Playlist | None:
        conn = await self._tx.connection()
        cursor = await conn.execute("SELECT * FROM playlists WHERE id = ?", (id,))
        row = await cursor.fetchone()
        return _row_to_playlist(row) if row else None

    async def list_all(self) -> list[Playlist]:
        conn = await self._tx.connection()
        cursor = await conn.execute("SELECT * FROM playlists ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [_row_to_playlist(r) for r in rows]

    async def rename(self, id: PlaylistId, name: str) -> None:
        conn = await self._tx.connection()
        await conn.execute(
            "UPDATE playlists SET name = ? WHERE id = ?",
            (name, id),
        )

    async def delete(self, id: PlaylistId) -> None:
        conn = await self._tx.connection()
        # ON DELETE CASCADE removes the playlist_tracks rows automatically.
        await conn.execute("DELETE FROM playlists WHERE id = ?", (id,))

    async def add_track(self, id: PlaylistId, track_id: TrackId) -> None:
        conn = await self._tx.connection()
        cursor = await conn.execute(
            "SELECT COALESCE(MAX(position), -1) FROM playlist_tracks WHERE playlist_id = ?",
            (id,),
        )
        row = await cursor.fetchone()
        next_position = (int(row[0]) if row else -1) + 1
        await conn.execute(
            """
            INSERT OR IGNORE INTO playlist_tracks (playlist_id, track_id, position)
            VALUES (?, ?, ?)
            """,
            (id, track_id, next_position),
        )

    async def remove_track(self, id: PlaylistId, track_id: TrackId) -> None:
        conn = await self._tx.connection()
        await conn.execute(
            "DELETE FROM playlist_tracks WHERE playlist_id = ? AND track_id = ?",
            (id, track_id),
        )

    async def list_tracks(self, id: PlaylistId) -> list[TrackId]:
        conn = await self._tx.connection()
        cursor = await conn.execute(
            "SELECT track_id FROM playlist_tracks WHERE playlist_id = ? ORDER BY position",
            (id,),
        )
        rows = await cursor.fetchall()
        return [TrackId(r[0]) for r in rows]
