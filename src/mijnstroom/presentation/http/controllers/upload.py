import os
import uuid

from dishka.integrations.litestar import FromDishka, inject
from litestar import Controller, Request, get, post
from litestar.datastructures import UploadFile
from litestar.response import Redirect, Template

from mijnstroom.application.interfaces.audio import AudioProbe
from mijnstroom.application.interfaces.storage import FileStorage
from mijnstroom.application.tracks.dto import FinalizeUploadInput
from mijnstroom.application.tracks.upload_track import UploadTrack
from mijnstroom.common.errors import ValidationError
from mijnstroom.presentation.http.forms.track import TrackMetadataForm, coalesce, parse_year


class UploadController(Controller):
    path = "/upload"

    @get("/")
    async def show_form(self, request: Request) -> Template:  # type: ignore[type-arg]
        error = request.query_params.get("error") or None
        return Template(
            template_name="upload.html",
            context={"error": error},
        )

    @post("/")
    @inject
    async def upload_audio(
        self,
        request: Request,  # type: ignore[type-arg]
        storage: FromDishka[FileStorage],
        probe: FromDishka[AudioProbe],
    ) -> Template:
        multipart = await request.form()
        upload = multipart.get("audio")
        if not isinstance(upload, UploadFile) or not upload.filename:
            return Template(
                template_name="upload.html",
                context={"error": "No file selected"},
                status_code=400,
            )
        original_filename = upload.filename
        ext = os.path.splitext(original_filename)[1] or ".bin"
        incoming_name = f"{uuid.uuid4().hex}{ext}"
        incoming_path = os.path.join(storage.incoming_dir(), incoming_name)
        content = await upload.read()
        with open(incoming_path, "wb") as fh:
            fh.write(content)

        try:
            probed = await probe.probe(incoming_path)
        except Exception as exc:
            import contextlib

            with contextlib.suppress(OSError):
                os.remove(incoming_path)
            return Template(
                template_name="upload.html",
                context={"error": f"Could not read audio file: {exc}"},
                status_code=400,
            )

        form = TrackMetadataForm(
            title=probed.title or os.path.splitext(original_filename)[0],
            artist=probed.artist,
            album=probed.album,
            year=probed.year,
            genre=probed.genre,
            lyrics=None,
        )
        return Template(
            template_name="track_form.html",
            context={
                "heading": "Confirm metadata",
                "action": "/upload/finalize",
                "submit_label": "Save track",
                "form": form,
                "incoming_path": incoming_path,
                "probed": {"format": probed.format.value, "duration": probed.duration_ms or 0},
                "has_cover": probed.has_cover,
                "cancel_url": "/upload",
                "error": None,
            },
        )


class FinalizeUploadController(Controller):
    path = "/upload/finalize"

    @post("/")
    @inject
    async def finalize(
        self,
        request: Request,  # type: ignore[type-arg]
        upload_track: FromDishka[UploadTrack],
    ) -> Redirect:
        data = await request.form()
        incoming_path = _as_str(data.get("incoming_path"))
        title = _as_str(data.get("title")) or ""
        if not incoming_path:
            raise ValidationError("Missing incoming_path")
        artist = coalesce(_as_str(data.get("artist")))
        album = coalesce(_as_str(data.get("album")))
        year = parse_year(_as_str(data.get("year")))
        genre = coalesce(_as_str(data.get("genre")))
        lyrics = coalesce(_as_str(data.get("lyrics")))
        cover_bytes = await _read_optional_upload(data.get("cover"))

        result = await upload_track(
            FinalizeUploadInput(
                incoming_path=incoming_path,
                title=title,
                artist=artist,
                album=album,
                year=year,
                genre=genre,
                lyrics=lyrics,
                cover_bytes=cover_bytes,
            )
        )
        return Redirect(path=f"/track/{result.id}")


def _as_str(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return None


async def _read_optional_upload(value: object) -> bytes | None:
    if not isinstance(value, UploadFile):
        return None
    if not value.filename:
        return None
    content = await value.read()
    return content if content else None
