import os
import shutil
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from PIL import Image

pytestmark = pytest.mark.integration


@pytest.mark.anyio
async def test_console_entry_point_serves_stdio(tmp_path: Path) -> None:
    """Connect to the console entry point and exercise configured storage."""
    command = os.environ.get("DETECTION_MCP_STDIO_COMMAND") or shutil.which("detection-mcp")
    assert command is not None, "detection-mcp console entry point is unavailable"
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    Image.new("RGB", (20, 10), "white").save(dataset / "image.png")
    environment = {
        "DETECTION_MCP_DB_PATH": str(tmp_path / "state" / "annotations.db"),
        "DETECTION_MCP_ALLOWED_DATASET_ROOTS": str(dataset),
        "DETECTION_MCP_ALLOWED_EXPORT_ROOTS": str(tmp_path / "output"),
    }
    transport = StdioTransport(command, args=[], env=environment, keep_alive=False)

    async with Client(transport) as client:
        created = await client.call_tool("create_dataset", {"root_path": str(dataset)})
        listed = await client.call_tool("list_datasets", {})

    assert created.structured_content["data"]["dataset_id"] == 1
    assert listed.structured_content["data"]["count"] == 1
