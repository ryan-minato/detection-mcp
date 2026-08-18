"""Stable domain errors exposed by MCP tools."""

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    DATASET_NOT_FOUND = "DATASET_NOT_FOUND"
    DATASET_DELETED = "DATASET_DELETED"
    CATEGORY_NOT_FOUND = "CATEGORY_NOT_FOUND"
    CATEGORY_DELETED = "CATEGORY_DELETED"
    CATEGORY_NAME_CONFLICT = "CATEGORY_NAME_CONFLICT"
    IMAGE_NOT_FOUND = "IMAGE_NOT_FOUND"
    IMAGE_ROOT_UNAVAILABLE = "IMAGE_ROOT_UNAVAILABLE"
    UNSUPPORTED_IMAGE_FORMAT = "UNSUPPORTED_IMAGE_FORMAT"
    IMAGE_DECODE_FAILED = "IMAGE_DECODE_FAILED"
    PATH_OUTSIDE_DATASET_ROOT = "PATH_OUTSIDE_DATASET_ROOT"
    PATH_NOT_ALLOWED = "PATH_NOT_ALLOWED"
    ANNOTATION_NOT_FOUND = "ANNOTATION_NOT_FOUND"
    INVALID_BBOX = "INVALID_BBOX"
    INVALID_ROTATED_BBOX = "INVALID_ROTATED_BBOX"
    ROTATED_BBOX_CORRECTION_EXCEEDED = "ROTATED_BBOX_CORRECTION_EXCEEDED"
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    OUTPUT_ALREADY_EXISTS = "OUTPUT_ALREADY_EXISTS"
    OUTPUT_PATH_NOT_ALLOWED = "OUTPUT_PATH_NOT_ALLOWED"
    AUTOTRAIN_LAYOUT_INCOMPATIBLE = "AUTOTRAIN_LAYOUT_INCOMPATIBLE"
    EXPORT_VALIDATION_FAILED = "EXPORT_VALIDATION_FAILED"
    STORAGE_ERROR = "STORAGE_ERROR"
    TRANSACTION_FAILED = "TRANSACTION_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class DomainError(Exception):
    """A recoverable error with a stable machine-readable representation."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        field: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field
        self.details = details or {}

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "code": self.code.value,
            "message": self.message,
            "details": self.details,
        }
        if self.field is not None:
            result["field"] = self.field
        return result
