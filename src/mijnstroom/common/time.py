from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    """Abstraction over wall-clock time, used by interactors."""

    def now(self) -> datetime: ...


class SystemClock:
    """Default clock returning the current UTC time."""

    def now(self) -> datetime:
        return datetime.now(UTC)
