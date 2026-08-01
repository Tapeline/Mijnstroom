from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LyricFragment:
    from_s: int
    to_s: int
    text: str


@dataclass(frozen=True, slots=True)
class Track:
    uid: str
    title: str
    artist: str
    album: str
    year: int | None
    genre: str


@dataclass(frozen=True, slots=True)
class Playlist:
    title: str
    artist: str
    year: int
    genre: str
    tracks: list[str]
