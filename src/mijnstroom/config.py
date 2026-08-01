import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

import dature


@dataclass(frozen=True, slots=True)
class StorageConfig:
    data_dir: str = "/data"

    @property
    def data_dir_path(self) -> Path:
        return Path(self.data_dir)


@dataclass(frozen=True, slots=True)
class HttpConfig:
    host: str = "0.0.0.0"
    port: int = 8000


@dataclass(frozen=True, slots=True)
class YoutubeConfig:
    interval_seconds: int = 30
    cookie_file: str = "data/cookiefile.txt"


@dataclass(frozen=True, slots=True)
class AudioFormat:
    codec: str
    kbps: int
    ext: str


@dataclass(frozen=True, slots=True)
class AppConfig:
    convert_to: list[AudioFormat] = field(default_factory=list)

    def __post_init__(self):
        if not self.convert_to:
            raise ValueError("Specify at least one format in app.covert_to")


@dataclass(frozen=True, slots=True)
class SecurityConfig:
    enable_auth: bool = False
    secret: str = "change-me"
    password: str = "change-me"


@dataclass(frozen=True, slots=True)
class Config:
    storage: StorageConfig = field(default_factory=StorageConfig)
    http: HttpConfig = field(default_factory=HttpConfig)
    youtube: YoutubeConfig = field(default_factory=YoutubeConfig)
    app: AppConfig = field(default_factory=AppConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)


_loaded_config: Config | None = None
_DEFAULT_CONFIG_PATH: Final = "config.yml"


def load_config(path: str = _DEFAULT_CONFIG_PATH) -> Config:
    global _loaded_config
    _loaded_config = dature.load(
        dature.EnvSource(prefix="MS_"),
        dature.Yaml12Source(file=path),
        schema=Config,
    )
    return _loaded_config


def get_config():
    global _loaded_config
    if _loaded_config is None:
        _loaded_config = load_config()
    return _loaded_config
