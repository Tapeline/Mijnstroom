from dataclasses import dataclass
from pathlib import Path

from litestar import MediaType, Response, get, post
from litestar.di import NamedDependency
from litestar.response import File

from mijnstroom.data import Playlist, Track
from mijnstroom.media.yt import YTVideoDetailed
from mijnstroom.usecases.library_search import (
    DownloadFileFromLibrary, GetPlaylistInLibrary,
    GetTrackFormatsInLibrary, GetTrackInLibrary,
    SearchPlaylistsInLibrary,
    SearchRequest,
    SearchTracksInLibrary,
    GetCoverInLibrary,
)
from mijnstroom.usecases.playlist_mgmt import (
    CreatePlaylistInLibrary,
    CreatePlaylistRequest,
    DeletePlaylistFromLibrary,
    DeleteTrackFromLibrary,
    UpdatePlaylistMetaInLibrary,
    UpdatePlaylistMetaRequest,
    UpdatePlaylistTracksInLibrary,
    UpdatePlaylistTracksRequest,
)
from mijnstroom.usecases.registry import (
    GetJobDetail,
    RunningPipeline,
    SeeRunningJobs,
)
from mijnstroom.usecases.yt_video_flow import (
    ImportYTVideoFlow,
    ImportYTVideoRequest,
    ImportYTVideoSegment,
    PrepareYTVideo,
    PrepareYTVideoRequest,
)


@get("/health", media_type=MediaType.TEXT)
async def health() -> Response:
    return Response("ok")


@get("/tracks")
async def search_tracks(
    search_tracks: NamedDependency[SearchTracksInLibrary],
    title: str | None = None,
    artist: str | None = None,
    album: str | None = None,
    include_unset: bool = False,
) -> list[Track]:
    return search_tracks(
        SearchRequest(
            title_like=title,
            artist_like=artist,
            album_like=album,
            include_unset=include_unset,
        )
    )


@get("/tracks/{uid:str}")
async def get_track(uid: str, get_track: GetTrackInLibrary) -> Track:
    return get_track(uid)
    


@get("/tracks/{uid:str}/formats")
async def get_track_formats(uid: str, get_track_formats: GetTrackFormatsInLibrary) -> list[str]:
    return get_track_formats(uid)


@get("/tracks/{uid:str}/cover.png")
async def get_cover(uid: str, get_cover: GetCoverInLibrary) -> File:
    return File(get_cover(uid))


@get("/tracks/{uid:str}/formats/{fmt:str}")
async def download_track(uid: str, fmt: str, download_track: DownloadFileFromLibrary) -> File:
    path: Path = download_track(uid, fmt)
    return File(
        path,
        filename=f"{uid}.{path.name.split('.')[-1]}"
    )


@get("/playlists")
async def search_playlists(
    search_playlists: SearchPlaylistsInLibrary,
    title: str | None = None,
    artist: str | None = None,
    album: str | None = None,
    include_unset: bool = False,
) -> list[Playlist]:
    return search_playlists(
        SearchRequest(
            title_like=title,
            artist_like=artist,
            album_like=album,
            include_unset=include_unset,
        )
    )


@get("/playlists/{uid:str}")
async def get_playlist(
    uid: str,
    get_playlist: GetPlaylistInLibrary
) -> Playlist:
    return get_playlist(uid)


@post("/playlists")
async def create_playlist(
    data: CreatePlaylistRequest,
    create_playlist: CreatePlaylistInLibrary,
) -> Playlist:
    return create_playlist(data)


@post("/playlists/{uid:str}/meta")
async def update_playlist_meta(
    uid: str,
    data: UpdatePlaylistMetaRequest,
    update_playlist_meta: UpdatePlaylistMetaInLibrary,
) -> Playlist:
    return update_playlist_meta(uid, data)


@post("/playlists/{uid:str}/tracks")
async def update_playlist_tracks(
    uid: str,
    data: UpdatePlaylistTracksRequest,
    update_playlist_tracks: UpdatePlaylistTracksInLibrary,
) -> Playlist:
    return update_playlist_tracks(uid, data)


@post("/playlists/{uid:str}/delete")
async def delete_playlist(
    uid: str,
    delete_playlist: DeletePlaylistFromLibrary
) -> None:
    delete_playlist(uid)


@post("/tracks/{uid:str}/delete")
async def delete_track(uid: str, delete_track: DeleteTrackFromLibrary) -> None:
    delete_track(uid)


@get("/jobs")
async def list_jobs(see_jobs: SeeRunningJobs) -> list[RunningPipeline]:
    return see_jobs()


@get("/jobs/{uid:str}")
async def get_job(uid: str, get_job: GetJobDetail) -> RunningPipeline:
    return get_job(uid)


@post("/yt/prepare")
async def prepare_yt_video(
    data: PrepareYTVideoRequest,
    prepare_yt_video: PrepareYTVideo,
) -> YTVideoDetailed:
    return await prepare_yt_video(data)


@dataclass
class ImportYTVideoBody:
    url: str
    override_title: str | None = None
    override_artist: str | None = None
    override_album: str | None = None
    override_year: int | None = None
    override_genre: str | None = None
    segments: list[ImportYTVideoSegment] | None = None


@post("/yt/import")
async def import_yt_video(
    data: ImportYTVideoBody,
    import_yt_video: ImportYTVideoFlow,
) -> dict:
    await import_yt_video(
        ImportYTVideoRequest(
            url=data.url,
            override_title=data.override_title,
            override_artist=data.override_artist,
            override_album=data.override_album,
            override_year=data.override_year,
            override_genre=data.override_genre,
            segments=data.segments,
        )
    )
    return {"job_uid": import_yt_video.uid}
