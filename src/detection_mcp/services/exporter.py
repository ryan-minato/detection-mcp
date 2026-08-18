"""Validated, atomic metadata.jsonl export."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from detection_mcp.errors import DomainError, ErrorCode
from detection_mcp.models import ExportMode
from detection_mcp.services.images import open_visual_image
from detection_mcp.services.paths import resolve_image


def _bbox_pixels(geometry: list[float], width: int, height: int) -> list[float]:
    x1, y1, x2, y2 = geometry
    return [x1 * width, y1 * height, (x2 - x1) * width, (y2 - y1) * height]


def _polygon_pixels(geometry: list[float], width: int, height: int) -> list[float]:
    return [value * (width if index % 2 == 0 else height) for index, value in enumerate(geometry)]


def export_metadata(
    *,
    root: Path,
    output_path: Path,
    mode: ExportMode,
    overwrite: bool,
    completed_images: list[str],
    categories: list[dict[str, Any]],
    annotations: list[dict[str, Any]],
) -> dict[str, Any]:
    if output_path.exists() and not overwrite:
        raise DomainError(ErrorCode.OUTPUT_ALREADY_EXISTS, "output file already exists", field="output_path")
    if mode is ExportMode.AUTOTRAIN and len(completed_images) < 5:
        raise DomainError(
            ErrorCode.AUTOTRAIN_LAYOUT_INCOMPATIBLE,
            "autotrain export requires at least five completed images",
            details={"completed_images": len(completed_images)},
        )

    category_mapping = {category["id"]: index for index, category in enumerate(categories)}
    by_image: dict[str, list[dict[str, Any]]] = {image_path: [] for image_path in completed_images}
    ignored_rotated = 0
    excluded_deleted = 0
    for annotation in annotations:
        if annotation["category_id"] not in category_mapping:
            excluded_deleted += 1
            continue
        if annotation["image_path"] in by_image:
            by_image[annotation["image_path"]].append(annotation)

    lines: list[str] = []
    for image_path in completed_images:
        if mode is ExportMode.AUTOTRAIN:
            path = Path(image_path)
            if len(path.parts) != 1 or path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                raise DomainError(
                    ErrorCode.AUTOTRAIN_LAYOUT_INCOMPATIBLE,
                    "autotrain images must use a flat JPG, JPEG, or PNG layout",
                    details={"image_path": image_path},
                )
        _, absolute_path = resolve_image(root, image_path)
        image, _ = open_visual_image(absolute_path)
        width, height = image.size
        objects: dict[str, list[Any]] = {"bbox": [], "category": []}
        if mode is ExportMode.EXTENDED:
            objects.update({"polygon": [], "polygon_category": []})
        for annotation in by_image[image_path]:
            category = category_mapping[annotation["category_id"]]
            if annotation["type"] == "bbox":
                objects["bbox"].append(_bbox_pixels(annotation["geometry"], width, height))
                objects["category"].append(category)
            elif mode is ExportMode.EXTENDED:
                objects["polygon"].append(_polygon_pixels(annotation["geometry"], width, height))
                objects["polygon_category"].append(category)
            else:
                ignored_rotated += 1
        lines.append(json.dumps({"file_name": image_path, "objects": objects}, separators=(",", ":")))

    lock_path = output_path.with_name(f".{output_path.name}.lock")
    lock_descriptor: int | None = None
    temporary_path: Path | None = None
    try:
        lock_descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        if output_path.exists() and not overwrite:
            raise DomainError(ErrorCode.OUTPUT_ALREADY_EXISTS, "output file already exists", field="output_path")
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            for line in lines:
                temporary.write(f"{line}\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, output_path)
        temporary_path = None
    except FileExistsError as error:
        raise DomainError(
            ErrorCode.OUTPUT_ALREADY_EXISTS,
            "another export is writing this output path",
            field="output_path",
        ) from error
    finally:
        if lock_descriptor is not None:
            os.close(lock_descriptor)
            lock_path.unlink(missing_ok=True)
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    return {
        "output_path": str(output_path),
        "export_mode": mode.value,
        "exported_images": len(completed_images),
        "category_mapping": {str(key): value for key, value in category_mapping.items()},
        "ignored_rotated_annotations": ignored_rotated,
        "excluded_deleted_category_annotations": excluded_deleted,
    }
