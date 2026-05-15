from mijnstroom.common.decorators import dto


@dto
class UploadTrackInput:
    """Initial upload from the multipart form: a file already saved on disk."""

    incoming_path: str
    original_filename: str


@dto
class FinalizeUploadInput:
    """Second-step submission with the user-edited metadata."""

    incoming_path: str
    title: str
    artist: str | None
    album: str | None
    year: int | None
    genre: str | None
    lyrics: str | None
    cover_bytes: bytes | None


@dto
class EditMetadataInput:
    track_id: str
    title: str
    artist: str | None
    album: str | None
    year: int | None
    genre: str | None
    lyrics: str | None
    cover_bytes: bytes | None
    clear_cover: bool = False


@dto
class BulkEditMetadataInput:
    """Patch applied to several tracks; only the ``apply_*`` flags trigger writes."""

    track_ids: tuple[str, ...]
    title: str | None = None
    apply_title: bool = False
    artist: str | None = None
    apply_artist: bool = False
    album: str | None = None
    apply_album: bool = False
    year: int | None = None
    apply_year: bool = False
    genre: str | None = None
    apply_genre: bool = False
    cover_bytes: bytes | None = None
    apply_cover: bool = False
