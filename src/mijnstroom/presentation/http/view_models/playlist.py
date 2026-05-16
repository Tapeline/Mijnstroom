from dataclasses import dataclass


@dataclass(slots=True)
class PlaylistRow:
    id: str
    name: str
    track_count: int
    first_track_cover_url: str | None
