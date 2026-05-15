from dishka.integrations.litestar import FromDishka, inject
from litestar import Controller, Request, get
from litestar.response import Template

from mijnstroom.application.interfaces.repos import TrackQuery
from mijnstroom.application.tracks.list_tracks import ListTracks
from mijnstroom.presentation.http.view_models.track import track_to_row


class LibraryController(Controller):
    path = "/"

    @get("/")
    async def index(self) -> Template:
        # Plain redirect via Template? We instead use a simple Redirect.
        from litestar.response import Redirect

        return Redirect(path="/library")  # type: ignore[return-value]

    @get("/library")
    @inject
    async def library(
        self,
        request: Request,  # type: ignore[type-arg]
        list_tracks: FromDishka[ListTracks],
    ) -> Template:
        q = request.query_params.get("q") or None
        tracks = await list_tracks(TrackQuery(search=q, limit=500, offset=0))
        rows = [track_to_row(t) for t in tracks]
        return Template(
            template_name="library.html",
            context={
                "tracks": rows,
                "total": len(rows),
                "query": q,
            },
        )
