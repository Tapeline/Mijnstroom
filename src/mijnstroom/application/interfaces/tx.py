from typing import Protocol


class Transaction(Protocol):
    """An async context manager wrapping a unit of work.

    Implementations open a database transaction on ``__aenter__`` and
    commit on successful ``__aexit__``; any exception causes a rollback.
    Repositories obtain their connection from the active transaction.
    """

    async def __aenter__(self) -> "Transaction": ...
    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None: ...
