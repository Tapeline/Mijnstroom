from abc import abstractmethod
from typing import Protocol


class FileStorage(Protocol):
    """Server-local file storage rooted under ``data_dir``.

    The interface is intentionally narrow; concrete implementations are
    responsible for building paths and ensuring atomicity of moves.
    """

    @abstractmethod
    def tracks_dir(self) -> str: ...

    @abstractmethod
    def covers_dir(self) -> str: ...

    @abstractmethod
    def incoming_dir(self) -> str: ...

    @abstractmethod
    def cache_dir(self) -> str: ...

    @abstractmethod
    async def move_to_tracks(self, tmp_path: str, ext: str, track_id: str) -> str: ...

    @abstractmethod
    async def write_cover(self, data: bytes, track_id: str) -> str: ...

    @abstractmethod
    async def delete(self, path: str) -> None: ...


