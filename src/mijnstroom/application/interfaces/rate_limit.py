from typing import Protocol


class YoutubeRateLimit(Protocol):
    """Spacing (in seconds) between consecutive YouTube downloads."""

    @property
    def interval_seconds(self) -> int: ...
