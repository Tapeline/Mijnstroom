from litestar import Litestar, Request, Response, Router
from litestar.di import Provide
from litestar.openapi import OpenAPIConfig
from litestar.openapi.plugins import SwaggerRenderPlugin

from mijnstroom.config import Config
from mijnstroom.errors import AppError, NotFoundError
from mijnstroom.http import endpoints, frontend
from mijnstroom.http.container import AppContainer
from mijnstroom.http.frontend import frontend_router
from mijnstroom.media.yt import YT
from mijnstroom.storage import LockedStorage
from mijnstroom.usecases.library_search import (
    GetPlaylistInLibrary, GetTrackInLibrary, SearchPlaylistsInLibrary,
    SearchTracksInLibrary,
)
from mijnstroom.usecases.playlist_mgmt import (
    CreatePlaylistInLibrary,
    DeletePlaylistFromLibrary,
    DeleteTrackFromLibrary, UpdatePlaylistMetaInLibrary,
    UpdatePlaylistTracksInLibrary,
)
from mijnstroom.usecases.registry import (
    GetJobDetail, PipelineRegistry, SeeRunningJobs,
)
from mijnstroom.usecases.yt_video_flow import ImportYTVideoFlow, PrepareYTVideo


def _provide_container(request: Request) -> AppContainer:
    return request.app.state.container


def _provide_config(container: AppContainer) -> Config:
    return container.config


def _provide_storage(container: AppContainer) -> LockedStorage:
    return container.storage


def _provide_registry(container: AppContainer) -> PipelineRegistry:
    return container.registry


def _provide_yt(container: AppContainer) -> YT:
    return container.yt


async def app_error_handler(_: Request, exc: AppError) -> Response:
    if isinstance(exc, NotFoundError):
        status_code = 404
    else:
        status_code = 400
    return Response(content={"error": str(exc)}, status_code=status_code)


def create_app(container: AppContainer) -> Litestar:
    api_router = Router(
        path="/api",
        route_handlers=[
            endpoints.health,
            endpoints.search_tracks,
            endpoints.get_track,
            endpoints.search_playlists,
            endpoints.get_playlist,
            endpoints.create_playlist,
            endpoints.update_playlist_meta,
            endpoints.update_playlist_tracks,
            endpoints.delete_playlist,
            endpoints.delete_track,
            endpoints.list_jobs,
            endpoints.get_job,
            endpoints.prepare_yt_video,
            endpoints.import_yt_video,
        ],
        dependencies={
            "container": Provide(_provide_container),
            "config": Provide(_provide_config),
            "storage": Provide(_provide_storage),
            "registry": Provide(_provide_registry),
            "yt": Provide(_provide_yt),
            "search_tracks": Provide(SearchTracksInLibrary),
            "search_playlists": Provide(SearchPlaylistsInLibrary),
            "get_track": Provide(GetTrackInLibrary),
            "get_playlist": Provide(GetPlaylistInLibrary),
            "create_playlist": Provide(CreatePlaylistInLibrary),
            "update_playlist_meta": Provide(UpdatePlaylistMetaInLibrary),
            "update_playlist_tracks": Provide(UpdatePlaylistTracksInLibrary),
            "delete_playlist": Provide(DeletePlaylistFromLibrary),
            "delete_track": Provide(DeleteTrackFromLibrary),
            "see_jobs": Provide(SeeRunningJobs),
            "get_job": Provide(GetJobDetail),
            "prepare_yt_video": Provide(PrepareYTVideo),
            "import_yt_video": Provide(ImportYTVideoFlow),
        },
    )

    app = Litestar(
        route_handlers=[frontend_router, api_router],
        debug=True,
        exception_handlers={
            AppError: app_error_handler,
        },
        openapi_config=OpenAPIConfig(
            title="Mijnstroom",
            version="0.1.0",
            path="/docs",
            render_plugins=[SwaggerRenderPlugin()]
        )
    )
    app.state.container = container
    return app
