import asyncio
import pprint

from mijnstroom.config import load_config
from mijnstroom.media.yt import YT
from mijnstroom.storage import LockedStorage
from mijnstroom.usecases.registry import PipelineRegistry
from mijnstroom.usecases.yt_video_flow import (
    ImportYTVideoFlow,
    ImportYTVideoRequest,
    ImportYTVideoSegment,
    PrepareYTVideo,
    PrepareYTVideoRequest,
)


async def main():
    config = load_config()
    storage = LockedStorage(config)
    storage.init()
    registry = PipelineRegistry()
    yt = YT(config, storage.tmp_path)
    url = "https://www.youtube.com/watch?v=CxhD0mvcED0"
    #result = await PrepareYTVideo(yt)(PrepareYTVideoRequest(url))
    #print(pprint.pformat(result))
    await ImportYTVideoFlow(yt, registry, storage, config)(
        ImportYTVideoRequest(
            url,
            override_artist="S.Vasilyev & M.Landa",
            override_album="Smeshariki OST",
            override_year=2010,
            segments=[
                ImportYTVideoSegment(
                    from_second=1465,
                    to_second=1647
                )
            ]
        )
    )
    await asyncio.sleep(1000000)


if __name__ == '__main__':
    asyncio.run(main())
