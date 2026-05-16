from dishka.integrations.litestar import FromDishka, inject
from litestar import Controller, Request, get, post
from litestar.response import Redirect, Template

from mijnstroom.application.interfaces.repos import PlaylistRepo, TrackQuery
from mijnstroom.application.playlists.create_playlist import CreatePlaylist
from mijnstroom.application.playlists.delete_playlist import DeletePlaylist
from mijnstroom.application.playlists.dto import (
    CreatePlaylistInput,
    RenamePlaylistInput,
    TrackPlaylistInput,
)
from mijnstroom.application.playlists.list_playlists import (
    GetPlaylistWithTracks,
    ListPlaylists,
)
from mijnstroom.application.playlists.rename_playlist import RenamePlaylist
from mijnstroom.application.playlists.track_membership import (
    AddTrackToPlaylist,
    RemoveTrackFromPlaylist,
)
from mijnstroom.application.tracks.list_tracks import ListTracks
from mijnstroom.common.errors import ValidationError
from mijnstroom.presentation.http.view_models.playlist import PlaylistRow


def _playlist_row(p, track_count: int, cover_url: str | None) -> PlaylistRow:
    return PlaylistRow(
        id=p.id,
        name=p.name,
        track_count=track_count,
        first_track_cover_url=cover_url,
    )


class PlaylistsController(Controller):
    path = "/playlists"

    @get("/")
    @inject
    async def index(
        self,
        list_playlists: FromDishka[ListPlaylists],
        playlist_repo: FromDishka[PlaylistRepo],
    ) -> Template:
        playlists = await list_playlists()
        rows = []
        for p in playlists:
            track_ids = await playlist_repo.list_tracks(p.id)
            track_count = len(track_ids)
            rows.append(_playlist_row(p, track_count, None))
        return Template(
            template_name="playlists_index.html",
            context={"playlists": rows, "error": None},
        )

    @post("/")
    @inject
    async def create(
        self,
        request: Request,  # type: ignore[type-arg]
        create_playlist: FromDishka[CreatePlaylist],
    ) -> Redirect:
        form = await request.form()
        name = form.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("Playlist name cannot be blank")
        playlist = await create_playlist(CreatePlaylistInput(name=name))
        return Redirect(path=f"/playlists/{playlist.id}")

    @get("/{playlist_id:str}")
    @inject
    async def show(
        self,
        playlist_id: str,
        get_playlist: FromDishka[GetPlaylistWithTracks],
        list_tracks: FromDishka[ListTracks],
    ) -> Template:
        playlist, tracks = await get_playlist(playlist_id)
        all_tracks = await list_tracks(TrackQuery(limit=1000, offset=0))
        return Template(
            template_name="playlist_detail.html",
            context={
                "playlist": playlist,
                "tracks": tracks,
                "all_tracks": all_tracks,
                "error": None,
            },
        )

    @post("/{playlist_id:str}/rename")
    @inject
    async def rename(
        self,
        playlist_id: str,
        request: Request,  # type: ignore[type-arg]
        rename_playlist: FromDishka[RenamePlaylist],
    ) -> Redirect:
        form = await request.form()
        name = form.get("name")
        if not isinstance(name, str):
            raise ValidationError("Missing name")
        await rename_playlist(RenamePlaylistInput(playlist_id=playlist_id, name=name))
        return Redirect(path=f"/playlists/{playlist_id}")

    @post("/{playlist_id:str}/delete")
    @inject
    async def delete(
        self,
        playlist_id: str,
        delete_playlist: FromDishka[DeletePlaylist],
    ) -> Redirect:
        await delete_playlist(playlist_id)
        return Redirect(path="/playlists")

    @post("/{playlist_id:str}/add")
    @inject
    async def add_track(
        self,
        playlist_id: str,
        request: Request,  # type: ignore[type-arg]
        add: FromDishka[AddTrackToPlaylist],
    ) -> Redirect:
        form = await request.form()
        track_id = form.get("track_id")
        if not isinstance(track_id, str) or not track_id:
            raise ValidationError("Missing track id")
        await add(TrackPlaylistInput(playlist_id=playlist_id, track_id=track_id))
        return Redirect(path=f"/playlists/{playlist_id}")

    @post("/{playlist_id:str}/remove")
    @inject
    async def remove_track(
        self,
        playlist_id: str,
        request: Request,  # type: ignore[type-arg]
        remove: FromDishka[RemoveTrackFromPlaylist],
    ) -> Redirect:
        form = await request.form()
        track_id = form.get("track_id")
        if not isinstance(track_id, str) or not track_id:
            raise ValidationError("Missing track id")
        await remove(TrackPlaylistInput(playlist_id=playlist_id, track_id=track_id))
        return Redirect(path=f"/playlists/{playlist_id}")
