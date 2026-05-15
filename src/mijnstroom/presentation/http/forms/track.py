from dataclasses import dataclass


@dataclass(slots=True)
class TrackMetadataForm:
    """Free-form metadata fields shared between upload and edit screens."""

    title: str
    artist: str | None
    album: str | None
    year: int | None
    genre: str | None
    lyrics: str | None


def parse_year(raw: str | None) -> int | None:
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def coalesce(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None
