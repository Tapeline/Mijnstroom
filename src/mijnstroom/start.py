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



if __name__ == '__main__':
    asyncio.run(main())
