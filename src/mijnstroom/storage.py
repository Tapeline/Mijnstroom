import json
import os
from pathlib import Path
import threading

import adaptix

from mijnstroom.config import Config
from mijnstroom.data import Track, Playlist


class Storage:
    def __init__(self, config: Config) -> None:
        data_dir = config.storage.data_dir_path
        self._track_file = data_dir / "tracks.json"
        self._playlist_file = data_dir / "playlists.json"
        self._tmp_dir = data_dir / "tmp"
        self._audio_dir = data_dir / "audio"
        self._covers_dir = data_dir / "covers"
        self._track_storage: dict[str, Track] = {}
        self._playlist_storage: dict[str, Playlist] = {}
        self._lock = threading.Lock()

    def init(self) -> None:
        for directory in (self._tmp_dir, self._audio_dir, self._covers_dir):
            directory.mkdir(parents=True, exist_ok=True)
        if not self._track_file.exists():
            self.save_all_tracks({})
        if not self._playlist_file.exists():
            self.save_all_playlists({})

    def save_all_tracks(self, tracks: dict[str, Track]) -> None:
        with self._lock:
            new_json = json.dumps(
                adaptix.dump(tracks, dict[str, Track]), indent=2
            )
            _safely_write(self._track_file, new_json)
            self._track_storage = tracks

    def save_all_playlists(self, playlists: dict[str, Playlist]) -> None:
        with self._lock:
            new_json = json.dumps(
                adaptix.dump(playlists, dict[str, Playlist]), indent=2
            )
            _safely_write(self._playlist_file, new_json)
            self._playlist_storage = playlists

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


def _safely_write(file: Path, text: str) -> None:
    tmp_file = file.with_name(f"{file.name}.tmp")
    tmp_file.write_text(text)
    os.replace(tmp_file, file)
    tmp_file.unlink()
