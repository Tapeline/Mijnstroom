from abc import abstractmethod
from typing import Protocol

from mijnstroom.application.interfaces.ytdlp import YtChapter


class DescriptionChapterParser(Protocol):
    @abstractmethod
    def parse(self, description: str, total_duration_ms: int | None) -> list[YtChapter]: ...
