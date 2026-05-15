from datetime import datetime

import aiosqlite

from mijnstroom.application.interfaces.repos import JobRepo
from mijnstroom.domain.job import Job, JobId, JobKind, JobStatus
from mijnstroom.infrastructure.persistence.transaction import SqliteTransaction


def _row_to_job(row: aiosqlite.Row) -> Job:
    return Job(
        id=JobId(row["id"]),
        kind=JobKind(row["kind"]),
        payload_json=row["payload_json"],
        status=JobStatus(row["status"]),
        attempts=row["attempts"],
        error=row["error"],
        parent_job_id=JobId(row["parent_job_id"]) if row["parent_job_id"] else None,
        created_at=datetime.fromisoformat(row["created_at"]),
        started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
        finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
        next_run_at=datetime.fromisoformat(row["next_run_at"]),
    )


class SqliteJobRepo(JobRepo):
    """Job repository backed by SQLite."""

    __slots__ = ("_tx",)

    def __init__(self, tx: SqliteTransaction) -> None:
        self._tx = tx

    async def insert(self, job: Job) -> None:
        conn = await self._tx.connection()
        await conn.execute(
            """
            INSERT INTO jobs (
                id, kind, payload_json, status, attempts, error,
                parent_job_id, created_at, started_at, finished_at, next_run_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.id,
                job.kind.value,
                job.payload_json,
                job.status.value,
                job.attempts,
                job.error,
                job.parent_job_id,
                job.created_at.isoformat(),
                job.started_at.isoformat() if job.started_at else None,
                job.finished_at.isoformat() if job.finished_at else None,
                job.next_run_at.isoformat(),
            ),
        )

    async def get(self, id: JobId) -> Job | None:
        conn = await self._tx.connection()
        cursor = await conn.execute("SELECT * FROM jobs WHERE id = ?", (id,))
        row = await cursor.fetchone()
        return _row_to_job(row) if row else None

    async def list_by_status(self, status: JobStatus) -> list[Job]:
        conn = await self._tx.connection()
        cursor = await conn.execute(
            "SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC",
            (status.value,),
        )
        rows = await cursor.fetchall()
        return [_row_to_job(r) for r in rows]

    async def claim_next(self) -> Job | None:
        """Atomically claim the next due pending job.

        Caller is expected to be inside ``async with tx``; the transaction
        guarantees the SELECT/UPDATE happen as a single unit. The
        connection-level ``BEGIN IMMEDIATE`` ensures only one writer can
        successfully claim a job.
        """
        conn = await self._tx.connection()
        now = datetime.now().astimezone().isoformat()
        cursor = await conn.execute(
            """
            SELECT * FROM jobs
            WHERE status = 'pending' AND next_run_at <= ?
            ORDER BY next_run_at ASC
            LIMIT 1
            """,
            (now,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        job_id = row["id"]
        await conn.execute(
            """
            UPDATE jobs
            SET status = 'running', started_at = ?, attempts = attempts + 1
            WHERE id = ?
            """,
            (now, job_id),
        )
        cursor = await conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        updated = await cursor.fetchone()
        return _row_to_job(updated) if updated else None

    async def mark_running(self, id: JobId) -> None:
        conn = await self._tx.connection()
        now = datetime.now().astimezone().isoformat()
        await conn.execute(
            "UPDATE jobs SET status = 'running', started_at = ? WHERE id = ?",
            (now, id),
        )

    async def mark_done(self, id: JobId) -> None:
        conn = await self._tx.connection()
        now = datetime.now().astimezone().isoformat()
        await conn.execute(
            "UPDATE jobs SET status = 'done', finished_at = ? WHERE id = ?",
            (now, id),
        )

    async def mark_failed(self, id: JobId, error: str) -> None:
        conn = await self._tx.connection()
        now = datetime.now().astimezone().isoformat()
        await conn.execute(
            "UPDATE jobs SET status = 'failed', error = ?, finished_at = ? WHERE id = ?",
            (error, now, id),
        )

    async def cancel_pending(self, id: JobId) -> bool:
        conn = await self._tx.connection()
        cursor = await conn.execute(
            "UPDATE jobs SET status = 'cancelled' WHERE id = ? AND status = 'pending'",
            (id,),
        )
        return (cursor.rowcount or 0) > 0

    async def delete(self, id: JobId) -> None:
        conn = await self._tx.connection()
        await conn.execute("DELETE FROM jobs WHERE id = ?", (id,))
