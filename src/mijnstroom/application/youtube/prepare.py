from mijnstroom.application.interfaces.chapters import DescriptionChapterParser
from mijnstroom.application.interfaces.idp import UserIdProvider
from mijnstroom.application.interfaces.ytdlp import (
    YoutubeClient,
    YtPlaylistInfo,
    YtSearchResult,
    YtVideoInfo,
)
from mijnstroom.application.youtube.dto import PrepareVideoInput, SearchYoutubeInput
from mijnstroom.common.decorators import interactor


@interactor
class SearchYoutube:
    client: YoutubeClient
    idp: UserIdProvider

    async def __call__(self, input: SearchYoutubeInput) -> list[YtSearchResult]:
        await self.idp.require_user()
        return await self.client.search(input.query, input.limit)


@interactor
class PrepareVideo:
    """Fetch video metadata + pieces.

    Pieces are taken from yt-dlp ``chapters`` when present; otherwise the
    description is parsed for timecodes. When neither yields anything,
    we return a single piece spanning the entire video.
    """

    client: YoutubeClient
    parser: DescriptionChapterParser
    idp: UserIdProvider

    async def __call__(self, input: PrepareVideoInput) -> YtVideoInfo:
        await self.idp.require_user()
        info = await self.client.video_info(input.url)
        if info.chapters:
            return info
        # Augment with parser-derived chapters if available.
        if info.description:
            parsed = self.parser.parse(info.description, info.duration_ms)
            if parsed:
                return YtVideoInfo(
                    id=info.id,
                    url=info.url,
                    title=info.title,
                    uploader=info.uploader,
                    upload_date=info.upload_date,
                    duration_ms=info.duration_ms,
                    description=info.description,
                    thumbnail_url=info.thumbnail_url,
                    chapters=tuple(parsed),
                )
        return info


@interactor
class PreparePlaylist:
    client: YoutubeClient
    idp: UserIdProvider

    async def __call__(self, input: PrepareVideoInput) -> YtPlaylistInfo:
        await self.idp.require_user()
        return await self.client.playlist_info(input.url)
