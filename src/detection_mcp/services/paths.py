"""Filesystem boundary enforcement."""

from pathlib import Path, PurePosixPath

from detection_mcp.errors import DomainError, ErrorCode

SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def _within(path: Path, roots: tuple[Path, ...]) -> bool:
    return not roots or any(path == root or path.is_relative_to(root) for root in roots)


def resolve_dataset_root(root_path: str, allowed_roots: tuple[Path, ...]) -> Path:
    path = Path(root_path).expanduser().resolve()
    if not path.exists() or not path.is_dir():
        raise DomainError(
            ErrorCode.IMAGE_ROOT_UNAVAILABLE,
            "dataset root does not exist or is not a directory",
            field="root_path",
            details={"root_path": str(path)},
        )
    if not _within(path, allowed_roots):
        raise DomainError(
            ErrorCode.PATH_NOT_ALLOWED,
            "dataset root is outside the configured allowed roots",
            field="root_path",
        )
    return path


def portable_image_path(image_path: str) -> str:
    normalized = PurePosixPath(image_path.replace("\\", "/"))
    if normalized.is_absolute() or ".." in normalized.parts or str(normalized) in {"", "."}:
        raise DomainError(
            ErrorCode.PATH_OUTSIDE_DATASET_ROOT,
            "image_path must be a dataset-relative path without '..'",
            field="image_path",
        )
    return normalized.as_posix()


def resolve_image(root: Path, image_path: str) -> tuple[str, Path]:
    relative = portable_image_path(image_path)
    resolved = (root / Path(*PurePosixPath(relative).parts)).resolve()
    if resolved == root or not resolved.is_relative_to(root):
        raise DomainError(
            ErrorCode.PATH_OUTSIDE_DATASET_ROOT,
            "resolved image path is outside the dataset root",
            field="image_path",
        )
    if resolved.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
        raise DomainError(
            ErrorCode.UNSUPPORTED_IMAGE_FORMAT,
            "image format is not supported",
            field="image_path",
            details={"suffix": resolved.suffix.lower()},
        )
    if not resolved.is_file():
        raise DomainError(
            ErrorCode.IMAGE_NOT_FOUND,
            "image was not found",
            field="image_path",
            details={"image_path": relative},
        )
    return relative, resolved


def resolve_output(output_path: str, allowed_roots: tuple[Path, ...]) -> Path:
    path = Path(output_path).expanduser().resolve()
    if not _within(path, allowed_roots):
        raise DomainError(
            ErrorCode.OUTPUT_PATH_NOT_ALLOWED,
            "output path is outside the configured allowed roots",
            field="output_path",
        )
    if not path.parent.exists() or not path.parent.is_dir():
        raise DomainError(
            ErrorCode.OUTPUT_PATH_NOT_ALLOWED,
            "output parent does not exist or is not a directory",
            field="output_path",
        )
    return path
