"""In-memory image and annotation preview rendering."""

import hashlib
import io
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from detection_mcp.services.images import open_visual_image


def _preview_size(
    image: Image.Image,
    maximum_width: int,
    maximum_height: int,
    allow_upscale: bool,
) -> tuple[int, int, float]:
    """Calculate bounded preview dimensions and their scale factor."""
    scale = min(maximum_width / image.width, maximum_height / image.height)
    if not allow_upscale:
        scale = min(scale, 1.0)
    width = max(1, round(image.width * scale))
    height = max(1, round(image.height * scale))
    return width, height, scale


def _color(category_id: int) -> tuple[int, int, int]:
    """Derive a stable visible RGB color from a category identifier."""
    digest = hashlib.sha256(str(category_id).encode()).digest()
    return (64 + digest[0] % 160, 64 + digest[1] % 160, 64 + digest[2] % 160)


def _draw_positioning_grid(image: Image.Image) -> None:
    """Overlay a five-by-five grid with five minor divisions per major cell."""
    draw = ImageDraw.Draw(image, "RGBA")
    x_positions = [min(image.width - 1, round(image.width * index / 25)) for index in range(26)]
    y_positions = [min(image.height - 1, round(image.height * index / 25)) for index in range(26)]

    for position in x_positions:
        draw.line((position, 0, position, image.height - 1), fill=(255, 255, 255, 64))
    for position in y_positions:
        draw.line((0, position, image.width - 1, position), fill=(255, 255, 255, 64))
    for x in x_positions:
        for y in y_positions:
            draw.point((x, y), fill=(255, 255, 255, 160))
    for index in range(6):
        x = min(image.width - 1, round(image.width * index / 5))
        y = min(image.height - 1, round(image.height * index / 5))
        draw.line((x, 0, x, image.height - 1), fill=(255, 255, 255, 128))
        draw.line((0, y, image.width - 1, y), fill=(255, 255, 255, 128))


def render_preview(
    image_path: Path,
    *,
    maximum_width: int,
    maximum_height: int,
    allow_upscale: bool,
    annotations: list[dict[str, Any]] | None = None,
    show_grid: bool = True,
) -> tuple[bytes, dict[str, Any]]:
    """Render an optional annotation overlay into an in-memory PNG.

    Args:
        image_path: Canonical source image path.
        maximum_width: Maximum preview width in pixels.
        maximum_height: Maximum preview height in pixels.
        allow_upscale: Whether previews may exceed source dimensions.
        annotations: Optional annotation records to draw over the image.
        show_grid: Whether to overlay the positioning grid.

    Returns:
        PNG bytes and structured source, preview, scale, and orientation metadata.

    Raises:
        DomainError: If the source image cannot be decoded.
        ValueError: If Pillow receives invalid dimensions or annotation geometry.

    Notes:
        Rendering is entirely in memory and never writes to the source image.
    """
    # Decode and resize the visual image while preserving aspect ratio.
    image, orientation_applied = open_visual_image(image_path)
    original_width, original_height = image.size
    width, height, scale = _preview_size(image, maximum_width, maximum_height, allow_upscale)
    if (width, height) != image.size:
        image = image.resize((width, height), Image.Resampling.LANCZOS)

    if show_grid:
        _draw_positioning_grid(image)

    # Draw stable category colors, geometry, and compact annotation labels.
    if annotations:
        draw = ImageDraw.Draw(image)
        line_width = max(2, round(min(width, height) / 300))
        for annotation in annotations:
            color = _color(int(annotation["category_id"]))
            geometry = annotation["geometry"]
            if annotation["type"] == "bbox":
                x1, y1, x2, y2 = geometry
                points = (x1 * width, y1 * height, x2 * width, y2 * height)
                draw.rectangle(points, outline=color, width=line_width)
                label_at = (points[0], points[1])
            else:
                polygon = [(geometry[index] * width, geometry[index + 1] * height) for index in range(0, 8, 2)]
                draw.line([*polygon, polygon[0]], fill=color, width=line_width)
                marker_radius = max(2, line_width * 2)
                for x, y in polygon:
                    draw.ellipse(
                        (x - marker_radius, y - marker_radius, x + marker_radius, y + marker_radius),
                        fill=color,
                    )
                label_at = polygon[0]
            label = f"[{annotation['annotation_id']}] {annotation['category_name']}"
            label_box = draw.textbbox(label_at, label)
            draw.rectangle(label_box, fill=color)
            draw.text(label_at, label, fill=(0, 0, 0))

    # Encode the final preview and report how it relates to the source image.
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    metadata = {
        "original_width": original_width,
        "original_height": original_height,
        "preview_width": width,
        "preview_height": height,
        "scale": scale,
        "orientation_applied": orientation_applied,
    }
    return buffer.getvalue(), metadata
