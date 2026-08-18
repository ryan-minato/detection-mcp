import hashlib
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from PIL import Image

pytestmark = [pytest.mark.integration, pytest.mark.docker]

IMAGE = "detection-mcp:local"


def _require_runtime() -> None:
    """Require Docker and the locally built test image, failing only in CI."""
    if shutil.which("docker") is None:
        if os.environ.get("CI"):
            pytest.fail("docker executable is unavailable")
        pytest.skip("docker executable is unavailable")
    checks = (["docker", "info"], ["docker", "image", "inspect", IMAGE])
    for command in checks:
        result = subprocess.run(command, check=False, capture_output=True, text=True)
        if result.returncode == 0:
            continue
        message = result.stderr.strip() or result.stdout.strip() or f"failed to run {' '.join(command)}"
        if os.environ.get("CI"):
            pytest.fail(message)
        pytest.skip(message)


def _transport(dataset: Path, state: Path, output: Path) -> StdioTransport:
    """Create a Docker-backed STDIO transport with the production mounts."""
    mounts = [
        f"type=bind,source={dataset},target=/datasets,readonly",
        f"type=bind,source={state},target=/state",
        f"type=bind,source={output},target=/output",
    ]
    args = ["run", "--rm", "--interactive"]
    for mount in mounts:
        args.extend(["--mount", mount])
    args.append(IMAGE)
    return StdioTransport("docker", args=args)


@pytest.mark.anyio
async def test_container_mounts_and_state_survive_recreation(tmp_path: Path) -> None:
    """Exercise annotation, preview, export, and persisted state through Docker."""
    _require_runtime()
    dataset = tmp_path / "datasets"
    state = tmp_path / "state"
    output = tmp_path / "output"
    for directory in (dataset, state, output):
        directory.mkdir()
    state.chmod(0o777)
    output.chmod(0o777)
    image_path = dataset / "image.png"
    Image.new("RGB", (40, 20), "white").save(image_path)
    source_digest = hashlib.sha256(image_path.read_bytes()).digest()

    async with Client(_transport(dataset, state, output)) as client:
        created = await client.call_tool("create_dataset", {"root_path": "/datasets", "name": "container"})
        dataset_id = created.structured_content["data"]["dataset_id"]
        categories = await client.call_tool(
            "add_categories",
            {"dataset_id": dataset_id, "categories": [{"name": "vehicle"}]},
        )
        category_id = categories.structured_content["data"]["categories"][0]["category_id"]
        await client.call_tool(
            "set_image_status",
            {"dataset_id": dataset_id, "image_path": "image.png", "status": "completed"},
        )
        await client.call_tool(
            "add_bbox_annotations",
            {
                "dataset_id": dataset_id,
                "image_path": "image.png",
                "annotations": [{"category_id": category_id, "bbox": [0.1, 0.1, 0.5, 0.5]}],
            },
        )
        preview = await client.call_tool(
            "preview_annotations",
            {"dataset_id": dataset_id, "image_path": "image.png"},
        )
        assert preview.structured_content["data"]["annotation_count"] == 1
        await client.call_tool(
            "export_metadata_jsonl",
            {
                "dataset_id": dataset_id,
                "output_path": "/output/metadata.jsonl",
                "export_mode": "extended",
            },
        )

    async with Client(_transport(dataset, state, output)) as client:
        datasets = await client.call_tool("list_datasets", {})
        annotations = await client.call_tool("list_annotations", {"dataset_id": dataset_id})
        images = await client.call_tool("list_images", {"dataset_id": dataset_id})

    assert datasets.structured_content["data"]["count"] == 1
    assert annotations.structured_content["data"]["count"] == 1
    assert images.structured_content["data"]["images"][0]["status"] == "completed"
    assert (output / "metadata.jsonl").is_file()
    assert hashlib.sha256(image_path.read_bytes()).digest() == source_digest
