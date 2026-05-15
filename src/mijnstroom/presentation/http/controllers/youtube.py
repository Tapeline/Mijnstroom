import re

from dishka.integrations.litestar import FromDishka, inject
from litestar import Controller, Request, get, post
from litestar.response import Redirect, Template

from mijnstroom.application.interfaces.ytdlp import YtVideoInfo
from mijnstroom.application.youtube.dto import (
    PlaylistEntryPlan,
    PrepareVideoInput,
    SearchYoutubeInput,
    SubmitPlaylistDownloadInput,
    SubmitVideoDownloadInput,
    VideoPiece,
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
from mijnstroom.common.errors import AppError
from mijnstroom.presentation.http.forms.track import parse_year

# Patterns that indicate a YouTube URL rather than a search query.
_YT_URL_RE = re.compile(
    r"(?:https?://)?(?:"
    r"(?:www\.)?(?:youtube\.com/(?:watch\?v=|playlist\?|shorts/|embed/)|"
    r"youtu\.be/|music\.youtube\.com/)"
    r")",
    re.IGNORECASE,
)


def _looks_like_url(value: str) -> bool:
    return bool(_YT_URL_RE.search(value))


class YoutubeController(Controller):
    path = "/youtube"

    @get("/")
    async def index(self) -> Template:
        return Template(
            template_name="youtube_index.html",
            context={"error": None, "results": None, "query": None},
        )

    @get("/go")
    @inject
    async def go(
        self,
        request: Request,  # type: ignore[type-arg]
        prepare_video: FromDishka[PrepareVideo],
        prepare_playlist: FromDishka[PreparePlaylist],
        search_youtube: FromDishka[SearchYoutube],
    ) -> Template:
        """Unified entry point: detects URL vs search query."""
        q = request.query_params.get("q")
        if not isinstance(q, str) or not q.strip():
            return Template(
                template_name="youtube_index.html",
                context={
                    "error": "Enter a search query or YouTube URL",
                    "results": None,
                    "query": None,
                },
                status_code=400,
            )
        q = q.strip()

        if _looks_like_url(q):
            # Treat as URL — delegate to prepare logic.
            return await self._prepare_url(q, prepare_video, prepare_playlist)

        # Treat as search query.
        results = await search_youtube(SearchYoutubeInput(query=q))
        return Template(
            template_name="youtube_index.html",
            context={"error": None, "results": results, "query": q},
        )

    async def _prepare_url(
        self,
        url: str,
        prepare_video: PrepareVideo,
        prepare_playlist: PreparePlaylist,
    ) -> Template:
        try:
            if "list=" in url or "playlist" in url.lower():
                playlist = await prepare_playlist(PrepareVideoInput(url=url))
                return Template(
                    template_name="youtube_prepare_playlist.html",
                    context={"playlist": playlist},
                )
            video = await prepare_video(PrepareVideoInput(url=url))
            pieces: list[dict[str, object]] = []
            if video.chapters:
                for ch in video.chapters:
                    pieces.append(
                        {
                            "start_ms": ch.start_ms,
                            "end_ms": ch.end_ms,
                            "title": ch.title,
                            "artist": video.uploader,
                        }
                    )
            else:
                pieces.append(
                    {
                        "start_ms": None,
                        "end_ms": None,
                        "title": video.title,
                        "artist": video.uploader,
                    }
                )
            return Template(
                template_name="youtube_prepare_video.html",
                context={"video": video, "pieces": pieces},
            )
        except AppError as exc:
            return Template(
                template_name="youtube_index.html",
                context={"error": str(exc), "results": None, "query": url},
                status_code=400,
            )

    @post("/submit")
    @inject
    async def submit(
        self,
        request: Request,  # type: ignore[type-arg]
        submit_video: FromDishka[SubmitVideoDownload],
    ) -> Redirect:
        form = await request.form()
        url = form.get("url")
        if not isinstance(url, str):
            raise AppError("Missing url")
        piece_count = _opt_int(form.get("piece_count")) or 0
        pieces: list[VideoPiece] = []
        for i in range(piece_count):
            enabled = form.get(f"enabled_{i}") == "1"
            title = _opt_str(form.get(f"title_{i}")) or ""
            start_ms = _opt_int(form.get(f"start_ms_{i}"))
            end_ms = _opt_int(form.get(f"end_ms_{i}"))
            artist = _opt_str(form.get(f"artist_{i}"))
            album = _opt_str(form.get(f"album_{i}"))
            year = parse_year(_opt_str(form.get(f"year_{i}")))
            genre = _opt_str(form.get(f"genre_{i}"))
            pieces.append(
                VideoPiece(
                    start_ms=start_ms,
                    end_ms=end_ms,
                    title=title,
                    artist=artist,
                    album=album,
                    year=year,
                    genre=genre,
                    enabled=enabled,
                )
            )
        await submit_video(SubmitVideoDownloadInput(url=url, pieces=tuple(pieces)))
        return Redirect(path="/queue")

    @post("/submit-playlist")
    @inject
    async def submit_playlist(
        self,
        request: Request,  # type: ignore[type-arg]
        submit_playlist: FromDishka[SubmitPlaylistDownload],
    ) -> Redirect:
        form = await request.form()
        url = form.get("url")
        if not isinstance(url, str):
            raise AppError("Missing url")
        entry_count = _opt_int(form.get("entry_count")) or 0
        entries: list[PlaylistEntryPlan] = []
        for i in range(entry_count):
            enabled = form.get(f"enabled_{i}") == "1"
            entry_url = _opt_str(form.get(f"url_{i}")) or ""
            title = _opt_str(form.get(f"title_{i}")) or ""
            artist = _opt_str(form.get(f"artist_{i}"))
            album = _opt_str(form.get(f"album_{i}"))
            year = parse_year(_opt_str(form.get(f"year_{i}")))
            genre = _opt_str(form.get(f"genre_{i}"))
            entries.append(
                PlaylistEntryPlan(
                    url=entry_url,
                    title=title,
                    artist=artist,
                    album=album,
                    year=year,
                    genre=genre,
                    enabled=enabled,
                )
            )
        await submit_playlist(SubmitPlaylistDownloadInput(url=url, entries=tuple(entries)))
        return Redirect(path="/queue")


def _opt_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _opt_str(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


# Silence unused-import warnings for helpers we imported from ytdlp types.
_ = YtVideoInfo
