from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from detection_mcp.errors import DomainError, ErrorCode
from detection_mcp.services.images import discover_images, open_visual_image
from detection_mcp.services.paths import portable_image_path, resolve_dataset_root, resolve_image, resolve_output
from detection_mcp.services.preview import render_preview

pytestmark = pytest.mark.unit


def test_path_boundaries_and_formats(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    Image.new("RGB", (10, 10)).save(root / "image.png")
    (root / "notes.txt").write_text("not an image")

    assert resolve_dataset_root(str(root), (tmp_path,)) == root.resolve()
    assert portable_image_path(r"nested\image.png") == "nested/image.png"
    assert resolve_image(root, "image.png")[0] == "image.png"
    assert resolve_output(str(tmp_path / "output.jsonl"), (tmp_path,)) == (tmp_path / "output.jsonl").resolve()
    output_directory = root / "output.jsonl"
    output_directory.mkdir()

    cases = [
        (lambda: resolve_dataset_root(str(root / "missing"), (tmp_path,)), ErrorCode.IMAGE_ROOT_UNAVAILABLE),
        (lambda: resolve_dataset_root(str(root), (tmp_path / "other",)), ErrorCode.PATH_NOT_ALLOWED),
        (lambda: portable_image_path("/absolute.png"), ErrorCode.PATH_OUTSIDE_DATASET_ROOT),
        (lambda: portable_image_path("."), ErrorCode.PATH_OUTSIDE_DATASET_ROOT),
        (lambda: resolve_image(root, "notes.txt"), ErrorCode.UNSUPPORTED_IMAGE_FORMAT),
        (lambda: resolve_image(root, "missing.png"), ErrorCode.IMAGE_NOT_FOUND),
        (
            lambda: resolve_output(str(root / "missing" / "output.jsonl"), (root,)),
            ErrorCode.OUTPUT_PATH_NOT_ALLOWED,
        ),
        (lambda: resolve_output(str(root / "output.jsonl"), (tmp_path / "other",)), ErrorCode.OUTPUT_PATH_NOT_ALLOWED),
        (lambda: resolve_output(str(output_directory), (root,)), ErrorCode.OUTPUT_PATH_NOT_ALLOWED),
    ]
    for operation, code in cases:
        with pytest.raises(DomainError) as captured:
            operation()
        assert captured.value.code is code


def test_discovery_excludes_symlinks_outside_the_dataset(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    Image.new("RGB", (10, 10)).save(root / "inside.png")
    Image.new("RGB", (10, 10)).save(tmp_path / "outside.png")
    (root / "linked.png").symlink_to(tmp_path / "outside.png")

    assert discover_images(root.resolve()) == ["inside.png"]


def test_discovery_sorting_decode_failure_and_preview_overlay(tmp_path: Path) -> None:
    Image.new("RGB", (20, 10), "white").save(tmp_path / "b.PNG")
    Image.new("RGB", (10, 20), "white").save(tmp_path / "A.jpg")
    (tmp_path / "broken.webp").write_text("broken")
    assert discover_images(tmp_path) == ["A.jpg", "b.PNG", "broken.webp"]

    with pytest.raises(DomainError) as captured:
        open_visual_image(tmp_path / "broken.webp")
    assert captured.value.code is ErrorCode.IMAGE_DECODE_FAILED

    image_path = tmp_path / "b.PNG"
    data, metadata = render_preview(
        image_path,
        maximum_width=80,
        maximum_height=80,
        allow_upscale=True,
        annotations=[
            {
                "annotation_id": 1,
                "category_id": 2,
                "category_name": "box",
                "type": "bbox",
                "geometry": [0.1, 0.1, 0.5, 0.5],
            },
            {
                "annotation_id": 2,
                "category_id": 2,
                "category_name": "rotated",
                "type": "rotated_bbox",
                "geometry": [0.2, 0.2, 0.8, 0.2, 0.8, 0.8, 0.2, 0.8],
            },
        ],
    )
    assert data.startswith(b"\x89PNG")
    assert metadata["preview_width"] == 80
    assert metadata["preview_height"] == 40


def test_rotated_preview_marks_vertices(tmp_path: Path) -> None:
    image_path = tmp_path / "image.png"
    Image.new("RGB", (100, 100), "white").save(image_path)
    common = {"annotation_id": 1, "category_id": 2, "category_name": "shape"}

    bbox_data, _ = render_preview(
        image_path,
        maximum_width=100,
        maximum_height=100,
        allow_upscale=False,
        annotations=[{**common, "type": "bbox", "geometry": [0.2, 0.2, 0.8, 0.8]}],
    )
    rotated_data, _ = render_preview(
        image_path,
        maximum_width=100,
        maximum_height=100,
        allow_upscale=False,
        annotations=[
            {
                **common,
                "type": "rotated_bbox",
                "geometry": [0.2, 0.2, 0.8, 0.2, 0.8, 0.8, 0.2, 0.8],
            }
        ],
    )

    bbox = Image.open(BytesIO(bbox_data))
    rotated = Image.open(BytesIO(rotated_data))
    assert bbox.getpixel((78, 78)) == (255, 255, 255)
    assert rotated.getpixel((78, 78)) != (255, 255, 255)
