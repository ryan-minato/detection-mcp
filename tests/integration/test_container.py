import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from PIL import Image

pytestmark = [pytest.mark.integration, pytest.mark.docker]

ROOT = Path(__file__).resolve().parents[2]
IMAGE = os.environ.get("DETECTION_MCP_CONTAINER_IMAGE", "detection-mcp:local")


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


def _require_compose() -> None:
    """Require Docker Compose, failing only in CI."""
    if shutil.which("docker") is None:
        if os.environ.get("CI"):
            pytest.fail("docker executable is unavailable")
        pytest.skip("docker executable is unavailable")
    result = subprocess.run(["docker", "compose", "version"], check=False, capture_output=True, text=True)
    if result.returncode == 0:
        return
    message = result.stderr.strip() or result.stdout.strip() or "docker compose is unavailable"
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


def test_compose_mount_contract(tmp_path: Path) -> None:
    """Verify the example Compose file resolves to the documented mounts."""
    _require_compose()
    dataset = tmp_path / "datasets"
    output = tmp_path / "output"
    environment = {
        **os.environ,
        "DETECTION_MCP_DATASET_PATH": str(dataset),
        "DETECTION_MCP_OUTPUT_PATH": str(output),
    }
    result = subprocess.run(
        ["docker", "compose", "-f", "docker-compose.example.yml", "config", "--format", "json"],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    service = json.loads(result.stdout)["services"]["detection-mcp"]
    mounts = {mount["target"]: mount for mount in service["volumes"]}

    assert mounts["/datasets"] == {
        "type": "bind",
        "source": str(dataset),
        "target": "/datasets",
        "read_only": True,
    }
    assert mounts["/output"] == {"type": "bind", "source": str(output), "target": "/output"}
    assert mounts["/state"]["type"] == "volume"


def test_container_runs_non_root_and_dataset_mount_is_read_only(tmp_path: Path) -> None:
    """Prove the production user and dataset mount prevent source writes."""
    _require_runtime()
    dataset = tmp_path / "datasets"
    dataset.mkdir()
    dataset.chmod(0o777)

    user = subprocess.run(
        ["docker", "run", "--rm", "--entrypoint", "id", IMAGE, "-u"],
        check=True,
        capture_output=True,
        text=True,
    )
    write = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--mount",
            f"type=bind,source={dataset},target=/datasets,readonly",
            "--entrypoint",
            "python",
            IMAGE,
            "-c",
            "from pathlib import Path; Path('/datasets/forbidden').write_text('x')",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert user.stdout.strip() != "0"
    assert write.returncode != 0
    assert not (dataset / "forbidden").exists()


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
    image_path.chmod(0o444)
    dataset.chmod(0o555)
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
