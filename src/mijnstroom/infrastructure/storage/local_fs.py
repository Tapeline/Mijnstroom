import asyncio
import os
from pathlib import Path

from mijnstroom.application.interfaces.storage import FileStorage
from mijnstroom.bootstrap.config import StorageConfig


class LocalFileStorage(FileStorage):
    """Stores files under ``<data_dir>/{tracks,covers,incoming,cache}``.

    All path operations are routed through :func:`os.replace` to keep
    moves atomic on POSIX filesystems; directories are created lazily.
    """

    __slots__ = ("_data_dir",)

    def __init__(self, config: StorageConfig) -> None:
        self._data_dir = config.data_dir
        for sub in ("tracks", "covers", "incoming", "cache"):
            Path(self._data_dir, sub).mkdir(parents=True, exist_ok=True)

    def tracks_dir(self) -> str:
        return os.path.join(self._data_dir, "tracks")

    def covers_dir(self) -> str:
        return os.path.join(self._data_dir, "covers")

    def incoming_dir(self) -> str:
        return os.path.join(self._data_dir, "incoming")

    def cache_dir(self) -> str:
        return os.path.join(self._data_dir, "cache")

    async def move_to_tracks(self, tmp_path: str, ext: str, track_id: str) -> str:
        ext_clean = ext.lstrip(".")
        dest = os.path.join(self.tracks_dir(), f"{track_id}.{ext_clean}")

        def _move() -> None:
            os.replace(tmp_path, dest)

        await asyncio.to_thread(_move)
        return dest

    async def write_cover(self, data: bytes, track_id: str) -> str:
        dest = os.path.join(self.covers_dir(), f"{track_id}.jpg")
        tmp = dest + ".tmp"

        def _write() -> None:
            with open(tmp, "wb") as fh:
                fh.write(data)
            os.replace(tmp, dest)

        await asyncio.to_thread(_write)
        return dest

    async def delete(self, path: str) -> None:
        def _delete() -> None:
            import contextlib

            with contextlib.suppress(FileNotFoundError):
                os.remove(path)

        await asyncio.to_thread(_delete)
