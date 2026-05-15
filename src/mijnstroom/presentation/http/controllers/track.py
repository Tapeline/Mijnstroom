import os
from collections.abc import AsyncIterator
from typing import cast

from dishka.integrations.litestar import FromDishka, inject
from litestar import Controller, Request, get, post
from litestar.datastructures import UploadFile
from litestar.exceptions import NotFoundException
from litestar.response import File, Redirect, Response, Stream, Template

from mijnstroom.application.tracks.delete_track import DeleteTrack
from mijnstroom.application.tracks.dto import EditMetadataInput
from mijnstroom.application.tracks.edit_metadata import EditTrackMetadata
from mijnstroom.application.tracks.get_track import GetTrack
from mijnstroom.presentation.http.forms.track import TrackMetadataForm, coalesce, parse_year
from mijnstroom.presentation.http.view_models.track import _format_duration


def _content_type_for(ext: str) -> str:
    ext = ext.lstrip(".").lower()
    return {
        "m4a": "audio/mp4",
        "mp4": "audio/mp4",
        "mp3": "audio/mpeg",
        "ogg": "audio/ogg",
        "opus": "audio/ogg",
        "flac": "audio/flac",
        "wav": "audio/wav",
    }.get(ext, "application/octet-stream")


def _parse_range(header: str, file_size: int) -> tuple[int, int] | None:
    if not header.startswith("bytes="):
        return None
    spec = header[len("bytes=") :].strip()
    if "," in spec:
        spec = spec.split(",", 1)[0].strip()
    if "-" not in spec:
        return None
    start_s, end_s = spec.split("-", 1)
    try:
        if start_s == "":
            length = int(end_s)
            start = max(file_size - length, 0)
            end = file_size - 1
        else:
            start = int(start_s)
            end = int(end_s) if end_s else file_size - 1
    except ValueError:
        return None
    if start < 0 or end >= file_size or start > end:
        return None
    return start, end


async def _file_range_iterator(
    path: str, start: int, end: int, chunk: int = 64 * 1024
) -> AsyncIterator[bytes]:
    remaining = end - start + 1
    with open(path, "rb") as fh:
        fh.seek(start)
        while remaining > 0:
            data = fh.read(min(chunk, remaining))
            if not data:
                break
            remaining -= len(data)
            yield data


class TrackController(Controller):
    path = "/track"

    @get("/{track_id:str}")
    @inject
    async def show(
        self,
        track_id: str,
        get_track: FromDishka[GetTrack],
    ) -> Template:
        track = await get_track(track_id)
        return Template(
            template_name="track_detail.html",
            context={
                "track": track,
                "duration": _format_duration(track.duration_ms),
            },
        )

    @get("/{track_id:str}/stream")
    @inject
    async def stream(
        self,
        track_id: str,
        request: Request,  # type: ignore[type-arg]
        get_track: FromDishka[GetTrack],
    ) -> Response[object]:
        track = await get_track(track_id)
        path = track.storage_path
        if not os.path.exists(path):
            raise NotFoundException("Track file is missing on disk")
        size = os.path.getsize(path)
        ext = os.path.splitext(path)[1]
        content_type = _content_type_for(ext)
        range_header = request.headers.get("range")
        if range_header:
            parsed = _parse_range(range_header, size)
            if parsed is not None:
                start, end = parsed
                length = end - start + 1
                return cast(
                    Response[object],
                    Stream(
                        content=_file_range_iterator(path, start, end),
                        status_code=206,
                        media_type=content_type,
                        headers={
                            "content-range": f"bytes {start}-{end}/{size}",
                            "accept-ranges": "bytes",
                            "content-length": str(length),
                        },
                    ),
                )
        return cast(
            Response[object],
            File(
                path=path,
                media_type=content_type,
                headers={"accept-ranges": "bytes"},
            ),
        )

    @get("/{track_id:str}/cover")
    @inject
    async def cover(
        self,
        track_id: str,
        get_track: FromDishka[GetTrack],
    ) -> Response[object]:
        track = await get_track(track_id)
        if not track.cover_path or not os.path.exists(track.cover_path):
            raise NotFoundException("No cover")
        return cast(Response[object], File(path=track.cover_path, media_type="image/jpeg"))

    @get("/{track_id:str}/download")
    @inject
    async def download(
        self,
        track_id: str,
        get_track: FromDishka[GetTrack],
    ) -> Response[object]:
        """Serve the track file with a Content-Disposition: attachment.

        Format conversion is currently a no-op: the source file is
        returned as-is. A future ``ProcessConvertJob`` worker handler
        will produce alternative formats on demand.
        """
        track = await get_track(track_id)
        if not os.path.exists(track.storage_path):
            raise NotFoundException("Track file is missing on disk")
        ext = os.path.splitext(track.storage_path)[1].lstrip(".") or "bin"
        safe_title = (track.title or "track").replace('"', "'")
        filename = f"{safe_title}.{ext}"
        return cast(
            Response[object],
            File(
                path=track.storage_path,
                media_type=_content_type_for(ext),
                filename=filename,
                content_disposition_type="attachment",
            ),
        )

    @get("/{track_id:str}/edit")
    @inject
    async def edit_form(
        self,
        track_id: str,
        get_track: FromDishka[GetTrack],
    ) -> Template:
        track = await get_track(track_id)
        form = TrackMetadataForm(
            title=track.title,
            artist=track.artist,
            album=track.album,
            year=track.year,
            genre=track.genre,
            lyrics=track.lyrics,
        )
        return Template(
            template_name="track_form.html",
            context={
                "heading": f"Edit: {track.title}",
                "action": f"/track/{track.id}/edit",
                "submit_label": "Save changes",
                "form": form,
                "incoming_path": None,
                "probed": None,
                "has_cover": track.cover_path is not None,
                "cancel_url": f"/track/{track.id}",
                "error": None,
            },
        )

    @post("/{track_id:str}/edit")
    @inject
    async def edit_submit(
        self,
        track_id: str,
        request: Request,  # type: ignore[type-arg]
        edit: FromDishka[EditTrackMetadata],
    ) -> Redirect:
        data = await request.form()
        title = _as_str(data.get("title")) or ""
        artist = coalesce(_as_str(data.get("artist")))
        album = coalesce(_as_str(data.get("album")))
        year = parse_year(_as_str(data.get("year")))
        genre = coalesce(_as_str(data.get("genre")))
        lyrics = coalesce(_as_str(data.get("lyrics")))
        clear_cover = _as_str(data.get("clear_cover")) == "1"
        cover_bytes = await _read_optional_upload(data.get("cover"))

        await edit(
            EditMetadataInput(
                track_id=track_id,
                title=title,
                artist=artist,
                album=album,
                year=year,
                genre=genre,
                lyrics=lyrics,
                cover_bytes=cover_bytes,
                clear_cover=clear_cover,
            )
        )
        return Redirect(path=f"/track/{track_id}")

    @get("/{track_id:str}/delete")
    @inject
    async def delete(
        self,
        track_id: str,
        delete_track: FromDishka[DeleteTrack],
    ) -> Redirect:
        await delete_track(track_id)
        return Redirect(path="/library")


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
