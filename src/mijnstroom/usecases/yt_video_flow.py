import asyncio
import uuid
from dataclasses import dataclass

from mijnstroom.config import Config
from mijnstroom.data import Track
from mijnstroom.errors import AppError
from mijnstroom.media import coding, metadata
from mijnstroom.media.coding import TimeRange
from mijnstroom.media.covers import fit_cover_art
from mijnstroom.media.yt import YT, YTVideoDetailed
from mijnstroom.usecases.registry import Pipeline, PipelineRegistry
from mijnstroom.storage import LockedStorage


@dataclass(frozen=True, slots=True)
class PrepareYTVideoRequest:
    url: str


@dataclass(frozen=True, slots=True)
class ImportYTVideoSegment:
    from_second: int
    to_second: int
    override_title: str | None = None
    override_artist: str | None = None
    override_album: str | None = None
    override_year: int | None = None
    override_genre: str | None = None
    override_album_cover: bytes | None = None


@dataclass(frozen=True, slots=True)
class _ConcreteSegment:
    from_second: int
    to_second: int
    title: str
    artist: str | None = None
    album: str | None = None
    year: int | None = None
    genre: str | None = None
    album_cover: bytes | None = None


@dataclass(frozen=True, slots=True)
class ImportYTVideoRequest:
    url: str
    override_title: str | None = None
    override_artist: str | None = None
    override_album: str | None = None
    override_year: int | None = None
    override_genre: str | None = None
    override_album_cover: bytes | None = None
    segments: list[ImportYTVideoSegment] | None = None


@dataclass
class PrepareYTVideo:
    yt: YT

    async def __call__(
        self,
        request: PrepareYTVideoRequest
    ) -> YTVideoDetailed:
        video = await asyncio.to_thread(self.yt.get_video_info, request.url)
        if not video:
            raise AppError(f"Video {request.url} not found")
        return video


@dataclass
class ImportYTVideoFlow(Pipeline):
    yt: YT
    registry: PipelineRegistry
    storage: LockedStorage
    config: Config

    async def __call__(self, request: ImportYTVideoRequest):
        self.notify_started(f"Import {request.url}")
        self.registry.start_task(self.uid, self.run(request))

    async def run(self, request: ImportYTVideoRequest) -> None:
        video = await asyncio.to_thread(self.yt.get_video_info, request.url)
        if not video:
            raise AppError(f"Video {request.url} not found")

        self.notify_running("Downloading source video")
        with self.storage.with_tmp_dir(self.uid) as tmp_dir:
            source_path = await asyncio.to_thread(
                self.yt.download_best_video,
                request.url, tmp_dir / "source_video"
            )

            self.notify_running("Downloading thumbnail")
            thumb_bytes = await asyncio.to_thread(
                self.yt.download_thumbnail,
                video.thumbnail_url
            )

            self.notify_running("Arranging parts and cropping covers")
            parts = _make_parts(request, video, thumb_bytes)

            converted = []
            base_fmt = self.config.app.convert_to[0]
            self.notify_running(
                f"Splitting into {len(parts)} parts "
                f"({base_fmt.codec}{base_fmt.kbps})"
            )
            converted.append(
                await coding.split(
                    source_path, tmp_dir, [
                        TimeRange(p.from_second, p.to_second)
                        for p in parts
                    ],
                    recode_to_codec=base_fmt.codec,
                    bitrate_kbps=base_fmt.kbps,
                    output_ext=base_fmt.ext
                )
            )

            for fmt in self.config.app.convert_to[1:]:
                self.notify_running(
                    f"Transcoding & copying {len(parts)} parts to "
                    f"{fmt.codec}{fmt.kbps}"
                )
                converted.append(
                    list(
                        await asyncio.gather(
                            *(
                                coding.transcode(
                                    input_path,
                                    input_path.with_suffix(f".{fmt.ext}"),
                                    codec=fmt.codec,
                                    bitrate_kbps=fmt.kbps,
                                )
                                for input_path in converted[0]
                            )
                        )
                    )
                )

            for fmt, files in zip(self.config.app.convert_to, converted):
                self.notify_running(
                    f"Writing metadata to {fmt.codec}{fmt.kbps}"
                )
                for part_config, part_file in zip(parts, files):
                    metadata.write_metadata(
                        part_file,
                        part_config.title,
                        part_config.artist,
                        part_config.album,
                        part_config.year,
                        part_config.genre,
                        part_config.album_cover,
                    )

            tracks_to_add = [
                Track(
                    uid=str(uuid.uuid4()),
                    title=part.title,
                    artist=part.artist or "Unknown Artist",
                    album=part.album or "Unknown Album",
                    year=part.year,
                    genre=part.genre or "Unknown Genre",
                )
                for part in parts
            ]

            with self.storage.for_update() as session:
                for fmt, files in zip(self.config.app.convert_to, converted):
                    self.notify_running(f"Saving {fmt.codec}{fmt.kbps}")
                    for track, file in zip(tracks_to_add, files):
                        session.copy_track_file(file, track.uid, fmt)

                self.notify_running(f"Saving {len(parts)} covers")
                for track, part in zip(tracks_to_add, parts):
                    if part.album_cover:
                        session.write_cover(track.uid, part.album_cover)

                self.notify_running(f"Writing to DB")
                session.save_all_tracks(
                    session.tracks | {
                        track.uid: track for track in tracks_to_add
                    }
                )
        self.notify_running(f"Cleanup complete")
        self.notify_done("Done")


def _make_parts(
    request: ImportYTVideoRequest,
    video: YTVideoDetailed,
    thumb: bytes | None
) -> list[_ConcreteSegment]:
    title = request.override_title or video.title
    artist = request.override_artist or video.channel
    album = request.override_album
    year = request.override_year or video.year
    genre = request.override_album
    album_cover = thumb
    if album_cover:
        album_cover = fit_cover_art(album_cover)
    if not request.segments:
        return [_ConcreteSegment(
            from_second=0,
            to_second=video.duration_seconds,
            title=title,
            artist=artist,
            album=album,
            year=year,
            genre=genre,
            album_cover=album_cover,
        )]
    return [
        _ConcreteSegment(
            from_second=seg.from_second,
            to_second=seg.to_second,
            title=seg.override_title or title,
            artist=seg.override_artist or artist,
            album=seg.override_album or album,
            year=seg.override_year or year,
            genre=seg.override_genre or genre,
            album_cover=(
                fit_cover_art(seg.override_album_cover)
                if seg.override_album_cover
                else album_cover
            ),
        )
        for seg in request.segments
    ]
