"""Read-only image discovery and decoding."""

import unicodedata
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from detection_mcp.errors import DomainError, ErrorCode
from detection_mcp.services.paths import SUPPORTED_IMAGE_SUFFIXES


def discover_images(root: Path) -> list[str]:
    """Discover supported images below a dataset root.

    Args:
        root: Canonical dataset directory to scan recursively.

    Returns:
        Stable, case-insensitively sorted POSIX relative paths.

    Raises:
        DomainError: If the directory tree cannot be scanned.

    Notes:
        Discovery reads directory metadata only and never changes image files.
    """
    try:
        paths = []
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
                continue
            if not path.resolve().is_relative_to(root):
                continue
            paths.append(path.relative_to(root).as_posix())
    except OSError as error:
        raise DomainError(ErrorCode.IMAGE_ROOT_UNAVAILABLE, "dataset root cannot be scanned") from error
    return sorted(paths, key=lambda value: (unicodedata.normalize("NFC", value).casefold(), value))


def open_visual_image(path: Path) -> tuple[Image.Image, bool]:
    """Decode an image in visual orientation without changing its source.

    Args:
        path: Canonical path to a supported image file.

    Returns:
        An in-memory RGB image and whether EXIF orientation was applied.

    Raises:
        DomainError: If Pillow cannot identify or decode the image.

    Notes:
        Pixel data is fully loaded before the source file handle is closed.
    """
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
