from dataclasses import dataclass

from mijnstroom.config import Config
from mijnstroom.media.yt import YT
from mijnstroom.storage import LockedStorage
from mijnstroom.usecases.registry import PipelineRegistry


@dataclass(frozen=True, slots=True)
class AppContainer:
    config: Config
    storage: LockedStorage
    registry: PipelineRegistry
    yt: YT
