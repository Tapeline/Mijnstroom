import os

from dishka import Provider, Scope, provide
from litestar import Request

from mijnstroom.application.interfaces.idp import UserIdProvider
from mijnstroom.application.interfaces.tx import Transaction
from mijnstroom.bootstrap.config import (
    AudioConfig,
    Config,
    HttpConfig,
    OIDCConfig,
    QueueConfig,
    SessionConfig,
    StorageConfig,
    YoutubeConfig,
)
from mijnstroom.common.time import Clock, SystemClock
from mijnstroom.infrastructure.auth.oidc_client import OIDCClient
from mijnstroom.infrastructure.auth.session import SessionCodec
from mijnstroom.infrastructure.auth.session_idp import (
    SessionIdProvider,
    SystemUserIdProvider,
)
from mijnstroom.infrastructure.persistence.sqlite import SqliteSettings
from mijnstroom.infrastructure.persistence.transaction import SqliteTransaction


class ConfigProvider(Provider):
    scope = Scope.APP

    def __init__(self, config: Config) -> None:
        super().__init__()
        self._config = config

    @provide
    def config(self) -> Config:
        return self._config

    @provide
    def storage_config(self, config: Config) -> StorageConfig:
        return config.storage

    @provide
    def http_config(self, config: Config) -> HttpConfig:
        return config.http

    @provide
    def oidc_config(self, config: Config) -> OIDCConfig:
        return config.oidc

    @provide
    def session_config(self, config: Config) -> SessionConfig:
        return config.session

    @provide
    def audio_config(self, config: Config) -> AudioConfig:
        return config.audio

    @provide
    def youtube_config(self, config: Config) -> YoutubeConfig:
        return config.youtube

    @provide
    def queue_config(self, config: Config) -> QueueConfig:
        return config.queue

    @provide
    def sqlite_settings(self, storage: StorageConfig) -> SqliteSettings:
        db_path = os.path.join(storage.data_dir, "mijnstroom.sqlite")
        return SqliteSettings(path=db_path)


class InfraProvider(Provider):
    scope = Scope.APP

    @provide
    def clock(self) -> Clock:
        return SystemClock()

    @provide
    def session_codec(self, session: SessionConfig) -> SessionCodec:
        return SessionCodec(session)

    @provide
    def oidc_client(self, oidc: OIDCConfig) -> OIDCClient:
        return OIDCClient(oidc)


class RequestProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def transaction(self, settings: SqliteSettings) -> Transaction:
        return SqliteTransaction(settings)

    @provide
    def user_id_provider(
        self,
        request: Request,  # type: ignore[type-arg]  # Dishka resolves by exact unparameterized type
        codec: SessionCodec,
        oidc: OIDCConfig,
    ) -> UserIdProvider:
        return SessionIdProvider(request, codec, oidc)


class WorkerRequestProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def transaction(self, settings: SqliteSettings) -> Transaction:
        return SqliteTransaction(settings)

    @provide
    def user_id_provider(self, oidc: OIDCConfig) -> UserIdProvider:
        return SystemUserIdProvider(oidc)
