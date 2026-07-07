from pathlib import Path

from mijnstroom.config import Config


class YT:
    def __init__(self, config: Config, tmp_dir: Path) -> None:
        self._tmp_dir = tmp_dir
        self._config = config.youtube
