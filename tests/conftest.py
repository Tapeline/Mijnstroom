import os
import tempfile
from collections.abc import Iterator

import pytest

from mijnstroom.bootstrap.config import Config, StorageConfig


@pytest.fixture
def tmp_data_dir() -> Iterator[str]:
    with tempfile.TemporaryDirectory() as path:
        yield path


@pytest.fixture
def config(tmp_data_dir: str) -> Config:
    return Config(storage=StorageConfig(data_dir=tmp_data_dir))


@pytest.fixture
def db_path(tmp_data_dir: str) -> str:
    return os.path.join(tmp_data_dir, "mijnstroom.sqlite")
