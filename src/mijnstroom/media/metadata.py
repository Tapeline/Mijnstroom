from pathlib import Path


def write_metadata(
    file: Path,
    title: str,
    artist: str | None = None,
    album: str | None = None,
    year: int | None = None,
    genre: str | None = None,
    album_cover: bytes | None = None,
) -> None:
    ...

