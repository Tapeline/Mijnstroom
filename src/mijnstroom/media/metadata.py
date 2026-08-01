from pathlib import Path

import music_tag


def write_metadata(
    file: Path,
    title: str,
    artist: str | None = None,
    album: str | None = None,
    year: int | None = None,
    genre: str | None = None,
    album_cover: bytes | None = None,
) -> None:
    file_meta = music_tag.load_file(file)
    file_meta['title'] = title
    if artist:
        file_meta['artist'] = artist
    if album:
        file_meta['album'] = album
    if year:
        file_meta['year'] = year
    if genre:
        file_meta['genre'] = genre
    if album_cover:
        file_meta['artwork'] = album_cover
    file_meta.save()
