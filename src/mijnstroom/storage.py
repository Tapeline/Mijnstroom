import json
import os
import shutil
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
import threading
from typing import Any, Generator

import adaptix
from typing_extensions import ContextManager

from mijnstroom.config import AudioFormat, Config
from mijnstroom.data import Track, Playlist
from mijnstroom.rwlock import RWLock


class ReadAccessor:
    def __init__(self, config: Config, lock: RWLock) -> None:
        data_dir = config.storage.data_dir_path
        self._track_file = data_dir / "tracks.json"
        self._playlist_file = data_dir / "playlists.json"
        self._tmp_dir = data_dir / "tmp"
        self._audio_dir = data_dir / "audio"
        self._covers_dir = data_dir / "covers"
        self._track_storage: dict[str, Track] = {}
        self._playlist_storage: dict[str, Playlist] = {}
        self._lock = lock

    def init(self) -> None:
        if self._track_file.exists():
            self._track_storage = adaptix.load(
                json.loads(self._track_file.read_text()),
                dict[str, Track]
            )
        if self._playlist_file.exists():
            self._playlist_storage = adaptix.load(
                json.loads(self._playlist_file.read_text()),
                dict[str, Playlist]
            )

    @property
    def tracks(self) -> dict[str, Track]:
        return dict(self._track_storage)

    @property
    def playlists(self) -> dict[str, Playlist]:
        return dict(self._playlist_storage)

    @property
    def audio_path(self) -> Path:
        return self._audio_dir

    @property
    def covers_path(self) -> Path:
        return self._covers_dir

    @property
    def tmp_path(self) -> Path:
        return self._tmp_dir
        
    def list_formats(self, track_id: str) -> dict[str, Path]:
        return {
            path.name.split(".", maxsplit=1)[0].removeprefix(f"{track_id}_"): path
            for path in self.audio_path.glob(f"{track_id}*")
        }
    
    def cover_for(self, track_id: str) -> Path:
        return self.covers_path / f"{track_id}.png"


class ReadWriteAccessor(ReadAccessor):
    def init(self) -> None:
        for directory in (self._tmp_dir, self._audio_dir, self._covers_dir):
            directory.mkdir(parents=True, exist_ok=True)
        if not self._track_file.exists():
            self.save_all_tracks({})
        if not self._playlist_file.exists():
            self.save_all_playlists({})
        super().init()

    def save_all_tracks(self, tracks: dict[str, Track]) -> None:
        with self._lock.lock_for_write():
            new_json = json.dumps(
                adaptix.dump(tracks, dict[str, Track]), indent=2
            )
            _safely_write(self._track_file, new_json)
            self._track_storage = tracks

    def save_all_playlists(self, playlists: dict[str, Playlist]) -> None:
        with self._lock.lock_for_write():
            new_json = json.dumps(
                adaptix.dump(playlists, dict[str, Playlist]), indent=2
            )
            _safely_write(self._playlist_file, new_json)
            self._playlist_storage = playlists

    def copy_track_file(
        self,
        from_path: Path,
        uid: str,
        fmt: AudioFormat
    ) -> None:
        shutil.copy2(
            from_path,
            self.audio_path / f"{uid}_{fmt.codec}{fmt.kbps}.{fmt.ext}"
        )

    def write_cover(self, uid: str, contents: bytes) -> None:
        (self.covers_path / f"{uid}.png").write_bytes(contents)


class LockedStorage:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._tmp_dir = config.storage.data_dir_path / "tmp"
        self._lock = RWLock()

    def init(self) -> None:
        with self.for_update() as storage:
            storage.init()

    @contextmanager
    def for_update(self) -> Iterator[ReadWriteAccessor]:
        with self._lock.lock_for_write():
            accessor = ReadWriteAccessor(self._config, self._lock)
            accessor.init()
            yield accessor

    @contextmanager
    def for_select(self) -> Iterator[ReadAccessor]:
        with self._lock.lock_for_read():
            accessor = ReadAccessor(self._config, self._lock)
            accessor.init()
            yield accessor

    @contextmanager
    def with_tmp_dir(self, uid: str) -> Iterator[Path]:
        tmp_dir = self._tmp_dir / uid
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        tmp_dir.mkdir(parents=True, exist_ok=True)
        try:
            yield tmp_dir
        finally:
            shutil.rmtree(tmp_dir)

    @property
    def tmp_path(self) -> Path:
        return self._tmp_dir


def _safely_write(file: Path, text: str) -> None:
    tmp_file = file.with_name(f"{file.name}.tmp")
    tmp_file.write_text(text)
    os.replace(tmp_file, file)
