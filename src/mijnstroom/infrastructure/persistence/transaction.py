import aiosqlite

from mijnstroom.application.interfaces.tx import Transaction
from mijnstroom.infrastructure.persistence.sqlite import SqliteSettings, connect


class SqliteTransaction(Transaction):
    """Transaction over a single aiosqlite connection.

    Repositories ask for the active connection via :meth:`connection`;
    if no transaction is currently open, a connection is created and the
    repository performs auto-committed reads.
    """

    __slots__ = ("_conn", "_depth", "_in_tx", "_settings")

    def __init__(self, settings: SqliteSettings) -> None:
        self._settings = settings
        self._conn: aiosqlite.Connection | None = None
        self._in_tx = False
        self._depth = 0

    async def connection(self) -> aiosqlite.Connection:
        if self._conn is None:
            self._conn = await connect(self._settings)
        return self._conn

    async def __aenter__(self) -> "SqliteTransaction":
        conn = await self.connection()
        if self._depth == 0:
            await conn.execute("BEGIN IMMEDIATE")
            self._in_tx = True
        self._depth += 1
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        tb: object,
    ) -> None:
        self._depth -= 1
        if self._depth > 0:
            return
        assert self._conn is not None
        try:
            if exc is not None:
                await self._conn.execute("ROLLBACK")
            else:
                await self._conn.execute("COMMIT")
        finally:
            self._in_tx = False

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
