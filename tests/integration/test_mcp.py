import hashlib
import json
from pathlib import Path

import pytest
from fastmcp import Client
from PIL import Image

from detection_mcp.config import Settings
from detection_mcp.server import create_server

pytestmark = pytest.mark.integration

EXPECTED_TOOL_SCHEMA_DIGESTS = {
    "create_dataset": "a8d385184acd739d7d9db341b03615a4b5515d0cd24fc594cba05c254dfa7bc2",
    "delete_dataset": "2efa84945bb91f6ebf8fbafda9df95a30a7b41078223ca54113818cef68536fd",
    "restore_dataset": "3fa46248c39fadc53b4fc0e6f8dd279d10df4270213475c29a51cfbc93fcb3cc",
    "list_datasets": "7dc1cc4ae8b8d04181e16d74fe811c3d32ce20c67d9ae4592bed843075358904",
    "get_dataset": "8645fa97e7a13e9bcb45445ef486547a54e64ac5953cd3c7e6dac7e3ae744f6b",
    "add_categories": "9b46529baa73bef0e66a1cf7df97e0bd60c7b9b5b2e87387be70778751af4067",
    "edit_category": "ea143add9be06e60e14483ee48cbc8f2f8c763471f720773d550dacdba658e1e",
    "delete_category": "1ea8996f611cdc801dd0cc3f8c7dd41e4a6f12fd9de60b176e7f7f3d158919cf",
    "restore_category": "6486fa55ff439b501a0ac69b40a1cdaea2a37c7e8cc5ac431926abfa9cb7f4d0",
    "list_categories": "fd8dcab7da1ffd98a779000d0f8ce605d6aa463ca53e8671b3d17f5d3e2c9705",
    "get_category": "8a9190c2d25c281d0b57de0205bb94feeb9a3528e2f189ff647fcc1794383836",
    "list_images": "49b3aebf0caf3d69bd6df2f588656a02c7d994776f577661413c2d77d53a528c",
    "set_image_status": "7bbdd7b3192aa2dc19e22d7b405567b788cb9b9dd80174fd2c314863394a29a0",
    "preview_image": "8c160e56cdf00a8609c03bea63d16f79e6655e722a656a9767141479a67db377",
    "preview_annotations": "aced5b4181b410d4aade37443b5b78add252d29ecd93983230cbfbe9ae484ec0",
    "list_annotations": "239362b27eb0315ae09e31832884c6b09fa8e780a05fdd7810d10bb2453bdde0",
    "add_bbox_annotations": "c045ada64bb3d99e0287ffb7b7a129688a3b80c6af804e044cdc2a0e11ffa965",
    "edit_bbox_annotation": "63481da83f770c3f26d03ddf13b55a209dd5d261750fca4c68efff7bf6220733",
    "delete_bbox_annotation": "3451e53f466792e8d688089174efe5266b83dde164aa3e02ee8f3b8399de3de9",
    "add_rotated_bbox_annotations": "6ec644303c349b2bd0e6f844dff3f36405e52c5497bcf71530c18082ceb9ffa2",
    "edit_rotated_bbox_annotation": "adbac3b17d9d8e7c3f9e0c874dc6dcfb52e49d1bde78451be214ad46c97c8310",
    "delete_rotated_bbox_annotation": "d5b2addc1567c6a0f0a17ce37aef8c499031980d1f3764693c79aa871111b600",
    "export_metadata_jsonl": "f12054e6ce73a9c754117647d611ed15dfac9743bfcaab9db5a77526445085f6",
}


@pytest.mark.anyio
async def test_server_exposes_exact_v1_tool_set(tmp_path: Path) -> None:
    server = create_server(Settings(db_path=tmp_path / "state.db"))
    async with Client(server) as client:
        tools = await client.list_tools()
    actual = {}
    for tool in tools:
        schema = json.dumps(
            {"input": tool.inputSchema, "output": tool.outputSchema},
            sort_keys=True,
            separators=(",", ":"),
        )
        actual[tool.name] = hashlib.sha256(schema.encode()).hexdigest()
    assert actual == EXPECTED_TOOL_SCHEMA_DIGESTS


@pytest.mark.anyio
async def test_preview_returns_image_and_structured_metadata(tmp_path: Path) -> None:
    root = tmp_path / "images"
    root.mkdir()
    Image.new("RGB", (40, 20), "white").save(root / "image.png")
    server = create_server(Settings(db_path=tmp_path / "state.db", allowed_dataset_roots=(root,)))
    async with Client(server) as client:
        created = await client.call_tool("create_dataset", {"root_path": str(root)})
        dataset_id = created.structured_content["data"]["dataset_id"]
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
        dataset_id = created.structured_content["data"]["dataset_id"]
        assert (await client.call_tool("list_datasets", {})).structured_content["data"]["count"] == 1
        assert (await client.call_tool("get_dataset", {"dataset_id": dataset_id})).structured_content["data"][
            "dataset_id"
        ] == dataset_id

        categories = await client.call_tool(
            "add_categories",
            {"dataset_id": dataset_id, "categories": [{"name": "vehicle"}, {"name": "person"}]},
        )
        category_id = categories.structured_content["data"]["categories"][0]["category_id"]
        second_id = categories.structured_content["data"]["categories"][1]["category_id"]
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
        bbox_id = bbox.structured_content["data"]["annotations"][0]["annotation_id"]
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
        rotated_id = rotated.structured_content["data"]["annotations"][0]["annotation_id"]
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
