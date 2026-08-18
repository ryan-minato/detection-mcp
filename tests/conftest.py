from collections.abc import Iterator
from pathlib import Path

import pytest
from PIL import Image

from detection_mcp.config import Settings
from detection_mcp.services.application import Application


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def image_root(tmp_path: Path) -> Path:
    root = tmp_path / "images"
    root.mkdir()
    for index in range(5):
        Image.new("RGB", (100 + index, 80 + index), "white").save(root / f"{index}.png")
    return root


@pytest.fixture
def application(tmp_path: Path, image_root: Path) -> Iterator[Application]:
    yield Application(
        Settings(
            db_path=tmp_path / "state" / "annotations.db",
            allowed_dataset_roots=(image_root,),
            allowed_export_roots=(tmp_path,),
        )
    )
