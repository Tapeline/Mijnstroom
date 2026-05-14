from typing import NewType, Protocol

UserId = NewType("UserId", str)


class UserIdProvider(Protocol):
    """Resolves the identifier of the caller for the current scope."""

    async def current_user(self) -> UserId | None: ...

    async def require_user(self) -> UserId: ...


