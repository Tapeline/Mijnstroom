from mijnstroom.common.decorators import dto


@dto
class SearchYoutubeInput:
    query: str
    limit: int = 20


@dto
class PrepareVideoInput:
    """Identifier of the video the user wants to download (URL or watch id)."""

    url: str


@dto
class VideoPiece:
    """A single piece (or "the only piece") of a video the user is going to save."""

    start_ms: int | None
    end_ms: int | None
    title: str
    artist: str | None
    album: str | None
    year: int | None
    genre: str | None
    enabled: bool = True


@dto
class SubmitVideoDownloadInput:
    """User-confirmed plan to download a single video as one or more tracks."""

    url: str
    pieces: tuple[VideoPiece, ...]
    cover_bytes: bytes | None = None


@dto
class PlaylistEntryPlan:
    url: str
    title: str
    artist: str | None
    album: str | None
    year: int | None
    genre: str | None
    enabled: bool = True


@dto
class SubmitPlaylistDownloadInput:
    url: str
    entries: tuple[PlaylistEntryPlan, ...]
