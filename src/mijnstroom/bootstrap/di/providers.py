import os

from dishka import Provider, Scope, provide
from litestar import Request

from mijnstroom.application.interfaces.audio import (
    AudioConverter,
    AudioProbe,
    CoverExtractor,
    TagWriter,
)
from mijnstroom.application.interfaces.chapters import DescriptionChapterParser
from mijnstroom.application.interfaces.idp import UserIdProvider
from mijnstroom.application.interfaces.queue import QueueGateway
from mijnstroom.application.interfaces.rate_limit import YoutubeRateLimit
from mijnstroom.application.interfaces.repos import JobRepo, PlaylistRepo, TrackRepo
from mijnstroom.application.interfaces.storage import FileStorage
from mijnstroom.application.interfaces.tx import Transaction
from mijnstroom.application.interfaces.ytdlp import YoutubeClient
from mijnstroom.application.playlists.create_playlist import CreatePlaylist
from mijnstroom.application.playlists.delete_playlist import DeletePlaylist
from mijnstroom.application.playlists.list_playlists import (
    GetPlaylistWithTracks,
    ListPlaylists,
)
from mijnstroom.application.playlists.rename_playlist import RenamePlaylist
from mijnstroom.application.playlists.track_membership import (
    AddTrackToPlaylist,
    RemoveTrackFromPlaylist,
)
from mijnstroom.application.queue.cancel_job import CancelJob, DeleteFailedJob
from mijnstroom.application.queue.list_jobs import ListJobs
from mijnstroom.application.tracks.bulk_edit_metadata import BulkEditTrackMetadata
from mijnstroom.application.tracks.delete_track import DeleteTrack
from mijnstroom.application.tracks.edit_metadata import EditTrackMetadata
from mijnstroom.application.tracks.get_track import GetTrack
from mijnstroom.application.tracks.list_tracks import ListTracks
from mijnstroom.application.tracks.upload_track import UploadTrack
from mijnstroom.application.worker.process_yt_video_job import (
    ProcessYtPlaylistItemJob,
    ProcessYtVideoJob,
)
from mijnstroom.application.youtube.prepare import (
    PreparePlaylist,
    PrepareVideo,
    SearchYoutube,
)
from mijnstroom.application.youtube.submit import (
    SubmitPlaylistDownload,
    SubmitVideoDownload,
)
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
from mijnstroom.infrastructure.audio.ffmpeg import (
    FfmpegAudioConverter,
    FfmpegCoverExtractor,
    FfmpegTagWriter,
)
from mijnstroom.infrastructure.audio.ffprobe import FfprobeAudioProbe
from mijnstroom.infrastructure.auth.oidc_client import OIDCClient
from mijnstroom.infrastructure.auth.session import SessionCodec
from mijnstroom.infrastructure.auth.session_idp import (
    GuestIdProvider,
    SessionIdProvider,
    SystemUserIdProvider,
)
from mijnstroom.infrastructure.persistence.job_repo import SqliteJobRepo
from mijnstroom.infrastructure.persistence.playlist_repo import SqlitePlaylistRepo
from mijnstroom.infrastructure.persistence.sqlite import SqliteSettings
from mijnstroom.infrastructure.persistence.track_repo import SqliteTrackRepo
from mijnstroom.infrastructure.persistence.transaction import SqliteTransaction
from mijnstroom.infrastructure.queue.sqlite_queue import SqliteQueueGateway
from mijnstroom.infrastructure.storage.local_fs import LocalFileStorage
from mijnstroom.infrastructure.youtube.description_parser import (
    RegexDescriptionChapterParser,
)
from mijnstroom.infrastructure.youtube.ytdlp_client import YtDlpYoutubeClient


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

    @provide
    def file_storage(self, storage: StorageConfig) -> FileStorage:
        return LocalFileStorage(storage)

    @provide
    def audio_probe(self) -> AudioProbe:
        return FfprobeAudioProbe()

    @provide
    def audio_converter(self) -> AudioConverter:
        return FfmpegAudioConverter()

    @provide
    def tag_writer(self) -> TagWriter:
        return FfmpegTagWriter()

    @provide
    def cover_extractor(self) -> CoverExtractor:
        return FfmpegCoverExtractor()

    @provide
    def youtube_client(self) -> YoutubeClient:
        return YtDlpYoutubeClient()

    @provide
    def chapter_parser(self) -> DescriptionChapterParser:
        return RegexDescriptionChapterParser()

    @provide
    def youtube_rate_limit(self, youtube: YoutubeConfig) -> YoutubeRateLimit:
        return youtube


class RequestProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def sqlite_transaction(self, settings: SqliteSettings) -> SqliteTransaction:
        return SqliteTransaction(settings)

    @provide
    def transaction(self, tx: SqliteTransaction) -> Transaction:
        return tx

    @provide
    def track_repo(self, tx: SqliteTransaction) -> TrackRepo:
        return SqliteTrackRepo(tx)

    @provide
    def playlist_repo(self, tx: SqliteTransaction) -> PlaylistRepo:
        return SqlitePlaylistRepo(tx)

    @provide
    def job_repo(self, tx: SqliteTransaction) -> JobRepo:
        return SqliteJobRepo(tx)

    @provide
    def queue_gateway(self, repo: JobRepo, tx: Transaction, clock: Clock) -> QueueGateway:
        return SqliteQueueGateway(repo, tx, clock)

    @provide
    def user_id_provider(
        self,
        config: Config,
        request: Request,  # type: ignore[type-arg]  # Dishka resolves by exact unparameterized type
        codec: SessionCodec,
        oidc: OIDCConfig,
    ) -> UserIdProvider:
        if not config.auth_enabled:
            return GuestIdProvider()
        return SessionIdProvider(request, codec, oidc)


class InteractorProvider(Provider):
    scope = Scope.REQUEST

    upload_track = provide(UploadTrack)
    edit_track_metadata = provide(EditTrackMetadata)
    bulk_edit_track_metadata = provide(BulkEditTrackMetadata)
    delete_track = provide(DeleteTrack)
    list_tracks = provide(ListTracks)
    get_track = provide(GetTrack)
    create_playlist = provide(CreatePlaylist)
    rename_playlist = provide(RenamePlaylist)
    delete_playlist = provide(DeletePlaylist)
    list_playlists = provide(ListPlaylists)
    get_playlist_with_tracks = provide(GetPlaylistWithTracks)
    add_track_to_playlist = provide(AddTrackToPlaylist)
    remove_track_from_playlist = provide(RemoveTrackFromPlaylist)
    list_jobs = provide(ListJobs)
    cancel_job = provide(CancelJob)
    delete_failed_job = provide(DeleteFailedJob)
    search_youtube = provide(SearchYoutube)
    prepare_video = provide(PrepareVideo)
    prepare_playlist = provide(PreparePlaylist)
    submit_video_download = provide(SubmitVideoDownload)
    submit_playlist_download = provide(SubmitPlaylistDownload)
    process_yt_video_job = provide(ProcessYtVideoJob)
    process_yt_playlist_item_job = provide(ProcessYtPlaylistItemJob)


class WorkerRequestProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def sqlite_transaction(self, settings: SqliteSettings) -> SqliteTransaction:
        return SqliteTransaction(settings)

    @provide
    def transaction(self, tx: SqliteTransaction) -> Transaction:
        return tx

    @provide
    def track_repo(self, tx: SqliteTransaction) -> TrackRepo:
        return SqliteTrackRepo(tx)

    @provide
    def playlist_repo(self, tx: SqliteTransaction) -> PlaylistRepo:
        return SqlitePlaylistRepo(tx)

    @provide
    def job_repo(self, tx: SqliteTransaction) -> JobRepo:
        return SqliteJobRepo(tx)

    @provide
    def queue_gateway(self, repo: JobRepo, tx: Transaction, clock: Clock) -> QueueGateway:
        return SqliteQueueGateway(repo, tx, clock)

    @provide
    def user_id_provider(self, oidc: OIDCConfig) -> UserIdProvider:
        return SystemUserIdProvider(oidc)
