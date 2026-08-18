"""Read-only image discovery and decoding."""

import unicodedata
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from detection_mcp.errors import DomainError, ErrorCode
from detection_mcp.services.paths import SUPPORTED_IMAGE_SUFFIXES


def discover_images(root: Path) -> list[str]:
    try:
        paths = [
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
        ]
    except OSError as error:
        raise DomainError(ErrorCode.IMAGE_ROOT_UNAVAILABLE, "dataset root cannot be scanned") from error
    return sorted(paths, key=lambda value: (unicodedata.normalize("NFC", value).casefold(), value))


def open_visual_image(path: Path) -> tuple[Image.Image, bool]:
    try:
        with Image.open(path, mode="r") as source:
            orientation = source.getexif().get(274, 1)
            visual = ImageOps.exif_transpose(source)
            visual.load()
            return visual.convert("RGB"), orientation != 1
    except (OSError, UnidentifiedImageError) as error:
        raise DomainError(
            ErrorCode.IMAGE_DECODE_FAILED,
            "image could not be decoded",
            details={"image_path": path.name},
        ) from error
