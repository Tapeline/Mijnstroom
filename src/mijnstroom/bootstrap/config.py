from dataclasses import dataclass, field

import dature


@dataclass(frozen=True, slots=True)
class StorageConfig:
    data_dir: str = "/data"


@dataclass(frozen=True, slots=True)
class HttpConfig:
    host: str = "0.0.0.0"
    port: int = 8000


@dataclass(frozen=True, slots=True)
class OIDCConfig:
    issuer: str = ""
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = ""
    allowed_sub: str = ""


@dataclass(frozen=True, slots=True)
class YoutubeConfig:
    interval_seconds: int = 30


@dataclass(frozen=True, slots=True)
class QueueConfig:
    poll_interval_seconds: int = 2


@dataclass(frozen=True, slots=True)
class AudioConfig:
    default_format: str = "aac"
    default_bitrate_kbps: int = 256


@dataclass(frozen=True, slots=True)
class SessionConfig:
    secret: str = "change-me"


@dataclass(frozen=True, slots=True)
class Config:
    storage: StorageConfig = field(default_factory=StorageConfig)
    http: HttpConfig = field(default_factory=HttpConfig)
    oidc: OIDCConfig = field(default_factory=OIDCConfig)
    youtube: YoutubeConfig = field(default_factory=YoutubeConfig)
    queue: QueueConfig = field(default_factory=QueueConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    session: SessionConfig = field(default_factory=SessionConfig)
    auth_enabled: bool = True


def load_config(path: str) -> Config:  # pragma: no cover
    return dature.load(
        dature.EnvSource(prefix="MS_"),
        dature.Yaml12Source(file=path),
        schema=Config,
    )
