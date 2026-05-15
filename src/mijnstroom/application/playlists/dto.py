from mijnstroom.common.decorators import dto


@dto
class CreatePlaylistInput:
    name: str


@dto
class RenamePlaylistInput:
    playlist_id: str
    name: str


@dto
class TrackPlaylistInput:
    """Add or remove a track from a playlist."""

    playlist_id: str
    track_id: str
