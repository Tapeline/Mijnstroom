from dataclasses import dataclass

from mijnstroom.domain.track import Track


@dataclass(slots=True)
class TrackRow:
    id: str
    title: str
    artist: str
    album: str
    duration: str
    has_cover: bool


def _format_duration(duration_ms: int | None) -> str:
    if duration_ms is None or duration_ms <= 0:
        return "-"
    total_seconds = duration_ms // 1000
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def track_to_row(track: Track) -> TrackRow:
    return TrackRow(
        id=track.id,
        title=track.title,
        artist=track.artist or "-",
        album=track.album or "-",
        duration=_format_duration(track.duration_ms),
        has_cover=track.cover_path is not None,
    )
