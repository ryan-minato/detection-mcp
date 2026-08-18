from pathlib import Path

import pytest
from fastmcp import Client
from PIL import Image

from detection_mcp.config import Settings
from detection_mcp.server import create_server

pytestmark = pytest.mark.integration


@pytest.mark.anyio
async def test_server_exposes_exact_v1_tool_set(tmp_path: Path) -> None:
    server = create_server(Settings(db_path=tmp_path / "state.db"))
    async with Client(server) as client:
        tools = await client.list_tools()
    assert {tool.name for tool in tools} == {
        "create_dataset",
        "delete_dataset",
        "restore_dataset",
        "list_datasets",
        "get_dataset",
        "add_categories",
        "edit_category",
        "delete_category",
        "restore_category",
        "list_categories",
        "get_category",
        "list_images",
        "set_image_status",
        "preview_image",
        "preview_annotations",
        "list_annotations",
        "add_bbox_annotations",
        "edit_bbox_annotation",
        "delete_bbox_annotation",
        "add_rotated_bbox_annotations",
        "edit_rotated_bbox_annotation",
        "delete_rotated_bbox_annotation",
        "export_metadata_jsonl",
    }


@pytest.mark.anyio
async def test_preview_returns_image_and_structured_metadata(tmp_path: Path) -> None:
    root = tmp_path / "images"
    root.mkdir()
    Image.new("RGB", (40, 20), "white").save(root / "image.png")
    server = create_server(Settings(db_path=tmp_path / "state.db", allowed_dataset_roots=(root,)))
    async with Client(server) as client:
        created = await client.call_tool("create_dataset", {"root_path": str(root)})
        dataset_id = created.structured_content["data"]["id"]
        preview = await client.call_tool(
            "preview_image",
            {"dataset_id": dataset_id, "image_path": "image.png"},
        )
    assert preview.structured_content["data"]["preview_width"] == 40
    assert [item.type for item in preview.content] == ["image", "text"]


@pytest.mark.anyio
async def test_domain_error_is_structured(tmp_path: Path) -> None:
    server = create_server(Settings(db_path=tmp_path / "state.db"))
    async with Client(server) as client:
        result = await client.call_tool("get_dataset", {"dataset_id": 999}, raise_on_error=False)
    assert result.is_error is True
    assert result.structured_content["error"]["code"] == "DATASET_NOT_FOUND"


@pytest.mark.anyio
async def test_all_mutating_tools_execute_through_mcp(tmp_path: Path) -> None:
    root = tmp_path / "images"
    root.mkdir()
    Image.new("RGB", (40, 20), "white").save(root / "image.png")
    server = create_server(
        Settings(
            db_path=tmp_path / "state.db",
            allowed_dataset_roots=(root,),
            allowed_export_roots=(tmp_path,),
        )
    )
    async with Client(server) as client:
        created = await client.call_tool("create_dataset", {"root_path": str(root), "name": "sample"})
        dataset_id = created.structured_content["data"]["id"]
        assert (await client.call_tool("list_datasets", {})).structured_content["data"]["count"] == 1
        assert (await client.call_tool("get_dataset", {"dataset_id": dataset_id})).structured_content["data"][
            "id"
        ] == dataset_id

        categories = await client.call_tool(
            "add_categories",
            {"dataset_id": dataset_id, "categories": [{"name": "vehicle"}, {"name": "person"}]},
        )
        category_id = categories.structured_content["data"]["categories"][0]["id"]
        second_id = categories.structured_content["data"]["categories"][1]["id"]
        await client.call_tool(
            "edit_category",
            {"dataset_id": dataset_id, "category_id": category_id, "description": "Road vehicle"},
        )
        assert (await client.call_tool("list_categories", {"dataset_id": dataset_id})).structured_content["data"][
            "count"
        ] == 2
        await client.call_tool("get_category", {"dataset_id": dataset_id, "category_id": category_id})
        await client.call_tool("list_images", {"dataset_id": dataset_id})
        await client.call_tool(
            "set_image_status",
            {"dataset_id": dataset_id, "image_path": "image.png", "status": "completed"},
        )

        bbox = await client.call_tool(
            "add_bbox_annotations",
            {
                "dataset_id": dataset_id,
                "image_path": "image.png",
                "annotations": [{"category_id": category_id, "bbox": [0.1, 0.1, 0.4, 0.4]}],
            },
        )
        bbox_id = bbox.structured_content["data"]["annotations"][0]["id"]
        await client.call_tool(
            "edit_bbox_annotation",
            {"dataset_id": dataset_id, "annotation_id": bbox_id, "category_id": second_id},
        )

        rotated = await client.call_tool(
            "add_rotated_bbox_annotations",
            {
                "dataset_id": dataset_id,
                "image_path": "image.png",
                "annotations": [
                    {
                        "category_id": category_id,
                        "polygon": [0.2, 0.2, 0.8, 0.2, 0.8, 0.8, 0.2, 0.8],
                    }
                ],
            },
        )
        rotated_id = rotated.structured_content["data"]["annotations"][0]["id"]
        await client.call_tool(
            "edit_rotated_bbox_annotation",
            {"dataset_id": dataset_id, "annotation_id": rotated_id, "category_id": second_id},
        )
        listed = await client.call_tool("list_annotations", {"dataset_id": dataset_id})
        assert listed.structured_content["data"]["count"] == 2
        preview = await client.call_tool(
            "preview_annotations",
            {"dataset_id": dataset_id, "image_path": "image.png"},
        )
        assert preview.structured_content["data"]["annotation_count"] == 2
        await client.call_tool(
            "export_metadata_jsonl",
            {
                "dataset_id": dataset_id,
                "output_path": str(tmp_path / "metadata.jsonl"),
                "export_mode": "extended",
            },
        )
        await client.call_tool(
            "delete_bbox_annotation",
            {"dataset_id": dataset_id, "annotation_ids": [bbox_id]},
        )
        await client.call_tool(
            "delete_rotated_bbox_annotation",
            {"dataset_id": dataset_id, "annotation_ids": [rotated_id]},
        )
        await client.call_tool("delete_category", {"dataset_id": dataset_id, "category_id": category_id})
        await client.call_tool("restore_category", {"dataset_id": dataset_id, "category_id": category_id})
        await client.call_tool("delete_dataset", {"dataset_id": dataset_id})
        restored = await client.call_tool("restore_dataset", {"dataset_id": dataset_id})
        assert restored.structured_content["data"]["deleted_at"] is None
