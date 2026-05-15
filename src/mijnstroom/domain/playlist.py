from datetime import datetime
from typing import NewType

from mijnstroom.common.decorators import entity
from mijnstroom.common.errors import ValidationError

PlaylistId = NewType("PlaylistId", str)


@entity
class Playlist:
    """A named, ordered collection of tracks."""

    id: PlaylistId
    name: str
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.id:
            raise ValidationError("Playlist id cannot be blank")
        if not self.name or not self.name.strip():
            raise ValidationError("Playlist name cannot be blank")
