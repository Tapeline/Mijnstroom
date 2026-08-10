import asyncio
import uuid
from dataclasses import dataclass

from mijnstroom.config import Config
from mijnstroom.data import Track
from mijnstroom.errors import AppError
from mijnstroom.media import coding, metadata
from mijnstroom.media.covers import fit_cover_art
from mijnstroom.media.yt import YT, YTPlaylist, YTVideo
from mijnstroom.storage import LockedStorage
from mijnstroom.usecases.registry import Pipeline, PipelineRegistry


@dataclass(frozen=True, slots=True)
class PrepareYTPlaylistRequest:
    url: str


@dataclass(frozen=True, slots=True)
class ImportYTPlaylistVideoConfig:
    """Configuration for a single video in the playlist."""
    video_id: str
    enabled: bool = True
    override_title: str | None = None
    override_artist: str | None = None
    override_album: str | None = None
    override_year: int | None = None
    override_genre: str | None = None


@dataclass(frozen=True, slots=True)
class ImportYTPlaylistRequest:
    url: str
    override_artist: str | None = None
    override_album: str | None = None
    override_year: int | None = None
    override_genre: str | None = None
    videos: list[ImportYTPlaylistVideoConfig] | None = None


@dataclass
class PrepareYTPlaylist:
    yt: YT

    async def __call__(
        self,
        request: PrepareYTPlaylistRequest
    ) -> YTPlaylist:
        playlist = await asyncio.to_thread(self.yt.get_playlist_info, request.url)
        if not playlist:
            raise AppError(f"Playlist {request.url} not found")
        return playlist


@dataclass
class ImportYTPlaylistFlow(Pipeline):
    yt: YT
    registry: PipelineRegistry
    storage: LockedStorage
    config: Config

    async def __call__(self, request: ImportYTPlaylistRequest):
        self.notify_started(f"Import playlist {request.url}")
        self.registry.start_task(self.uid, self.run(request))

    async def run(self, request: ImportYTPlaylistRequest) -> None:
        playlist = await asyncio.to_thread(self.yt.get_playlist_info, request.url)
        if not playlist:
            raise AppError(f"Playlist {request.url} not found")

        # Filter enabled videos
        video_configs = {
            vc.video_id: vc
            for vc in (request.videos or [])
        }

        videos_to_download = [
            (video, video_configs.get(video.id))
            for video in playlist.entries
            if not video_configs or video_configs.get(video.id, ImportYTPlaylistVideoConfig(video.id)).enabled
        ]

        if not videos_to_download:
            self.notify_done("No videos selected")
            return

        self.notify_running(f"Downloading {len(videos_to_download)} videos from playlist")

        with self.storage.with_tmp_dir(self.uid) as tmp_dir:
            tracks_to_add = []
            base_fmt = self.config.app.convert_to[0]

            for idx, (video, config) in enumerate(videos_to_download, 1):
                self.notify_running(
                    f"[{idx}/{len(videos_to_download)}] Downloading {video.title}"
                )

                video_tmp_dir = tmp_dir / f"video_{video.id}"
                video_tmp_dir.mkdir(parents=True, exist_ok=True)

                # Download video
                source_path = await asyncio.to_thread(
                    self.yt.download_best_video,
                    video.url,
                    video_tmp_dir / "source"
                )

                if not source_path:
                    self.notify_running(f"[{idx}/{len(videos_to_download)}] Failed to download {video.title}, skipping")
                    continue

                # Download thumbnail
                thumb_bytes = None
                if video.thumbnail_url:
                    thumb_bytes = await asyncio.to_thread(
                        self.yt.download_thumbnail,
                        video.thumbnail_url
                    )
                    if thumb_bytes:
                        thumb_bytes = fit_cover_art(thumb_bytes)

                # Determine metadata
                title = (config and config.override_title) or video.title
                artist = (config and config.override_artist) or request.override_artist or video.channel
                album = (config and config.override_album) or request.override_album or playlist.title
                year = (config and config.override_year) or request.override_year
                genre = (config and config.override_genre) or request.override_genre

                # Transcode to all formats
                self.notify_running(
                    f"[{idx}/{len(videos_to_download)}] Transcoding {video.title} to {base_fmt.codec}{base_fmt.kbps}"
                )

                converted_files = []
                # Base format
                base_output = video_tmp_dir / f"output.{base_fmt.ext}"
                await coding.transcode(
                    source_path,
                    base_output,
                    codec=base_fmt.codec,
                    bitrate_kbps=base_fmt.kbps,
                )
                converted_files.append((base_fmt, base_output))

                # Additional formats
                for fmt in self.config.app.convert_to[1:]:
                    self.notify_running(
                        f"[{idx}/{len(videos_to_download)}] Transcoding {video.title} to {fmt.codec}{fmt.kbps}"
                    )
                    output_path = video_tmp_dir / f"output.{fmt.ext}"
                    await coding.transcode(
                        base_output,
                        output_path,
                        codec=fmt.codec,
                        bitrate_kbps=fmt.kbps,
                    )
                    converted_files.append((fmt, output_path))

                # Write metadata to all formats
                self.notify_running(
                    f"[{idx}/{len(videos_to_download)}] Writing metadata for {video.title}"
                )
                for fmt, file_path in converted_files:
                    metadata.write_metadata(
                        file_path,
                        title,
                        artist,
                        album,
                        year,
                        genre,
                        thumb_bytes,
                    )

                # Create track record
                track = Track(
                    uid=str(uuid.uuid4()),
                    title=title,
                    artist=artist or "Unknown Artist",
                    album=album or "Unknown Album",
                    year=year,
                    genre=genre or "Unknown Genre",
                )
                tracks_to_add.append((track, converted_files, thumb_bytes))

            # Save all tracks
            with self.storage.for_update() as session:
                self.notify_running(f"Saving {len(tracks_to_add)} tracks")
                for track, converted_files, thumb_bytes in tracks_to_add:
                    for fmt, file_path in converted_files:
                        session.copy_track_file(file_path, track.uid, fmt)
                    if thumb_bytes:
                        session.write_cover(track.uid, thumb_bytes)

                session.save_all_tracks(
                    session.tracks | {
                        track.uid: track
                        for track, _, _ in tracks_to_add
                    }
                )

        self.notify_running(f"Cleanup complete")
        self.notify_done(f"Imported {len(tracks_to_add)} tracks from playlist")
