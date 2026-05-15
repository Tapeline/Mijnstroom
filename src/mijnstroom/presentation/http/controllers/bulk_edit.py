from dishka.integrations.litestar import FromDishka, inject
from litestar import Controller, Request, get, post
from litestar.response import Redirect, Template

from mijnstroom.application.tracks.bulk_edit_metadata import BulkEditTrackMetadata
from mijnstroom.application.tracks.dto import BulkEditMetadataInput
from mijnstroom.presentation.http.forms.track import coalesce, parse_year


class BulkEditController(Controller):
    path = "/bulk-edit"

    @get("/")
    async def show_form(
        self,
        request: Request,  # type: ignore[type-arg]
    ) -> Template:
        ids_raw = request.query_params.get("ids") or ""
        track_ids = [t.strip() for t in ids_raw.split(",") if t.strip()]
        return Template(
            template_name="bulk_edit.html",
            context={"track_ids": track_ids, "error": None},
        )

    @post("/")
    @inject
    async def submit(
        self,
        request: Request,  # type: ignore[type-arg]
        bulk_edit: FromDishka[BulkEditTrackMetadata],
    ) -> Redirect:
        form = await request.form()
        ids_raw = form.get("track_ids")
        track_ids = [t.strip() for t in str(ids_raw).split(",") if t.strip()]
        title = coalesce(form.get("title") if isinstance(form.get("title"), str) else None)
        artist = coalesce(form.get("artist") if isinstance(form.get("artist"), str) else None)
        album = coalesce(form.get("album") if isinstance(form.get("album"), str) else None)
        year = parse_year(form.get("year") if isinstance(form.get("year"), str) else None)
        genre = coalesce(form.get("genre") if isinstance(form.get("genre"), str) else None)
        apply_title = form.get("apply_title") == "1"
        apply_artist = form.get("apply_artist") == "1"
        apply_album = form.get("apply_album") == "1"
        apply_year = form.get("apply_year") == "1"
        apply_genre = form.get("apply_genre") == "1"

        await bulk_edit(
            BulkEditMetadataInput(
                track_ids=tuple(track_ids),
                title=title,
                apply_title=apply_title,
                artist=artist,
                apply_artist=apply_artist,
                album=album,
                apply_album=apply_album,
                year=year,
                apply_year=apply_year,
                genre=genre,
                apply_genre=apply_genre,
            )
        )
        return Redirect(path="/library")
