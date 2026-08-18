"""FastMCP server and v1 tool registration."""

import base64
import json
import logging
import sqlite3
from collections.abc import Awaitable, Callable
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.tools import ToolResult
from mcp.types import ImageContent, TextContent

from detection_mcp.config import Settings
from detection_mcp.errors import DomainError, ErrorCode
from detection_mcp.models import AnnotationType, BBoxCreate, CategoryCreate, ExportMode, ImageStatus, RotatedBBoxCreate
from detection_mcp.services.application import Application

LOGGER = logging.getLogger(__name__)


def _find_cause(error: BaseException, error_type: type[BaseException]) -> BaseException | None:
    """Find a typed cause in an exception chain without looping forever."""
    current: BaseException | None = error
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        if isinstance(current, error_type):
            return current
        seen.add(id(current))
        current = current.__cause__ or current.__context__
    return None


class DomainErrorMiddleware(Middleware):
    """Convert domain failures to stable structured MCP error results."""

    async def on_call_tool(
        self,
        context: MiddlewareContext,
        call_next: Callable[[MiddlewareContext], Awaitable[ToolResult]],
    ) -> ToolResult:
        try:
            return await call_next(context)
        except Exception as caught:
            domain_error = _find_cause(caught, DomainError)
            storage_error = _find_cause(caught, sqlite3.Error)
            if isinstance(domain_error, DomainError):
                error = domain_error
            elif isinstance(storage_error, sqlite3.Error):
                LOGGER.exception("SQLite operation failed while calling %s", context.message.name)
                error = DomainError(ErrorCode.STORAGE_ERROR, "the storage operation failed")
            else:
                if not isinstance(caught, ToolError):
                    LOGGER.exception("Unexpected failure while calling %s", context.message.name)
                error = DomainError(ErrorCode.INTERNAL_ERROR, "the tool failed unexpectedly")
            payload = {"ok": False, "error": error.as_dict()}
            return ToolResult(
                content=[TextContent(type="text", text=json.dumps(payload, separators=(",", ":")))],
                structured_content=payload,
                is_error=True,
            )


def _success(data: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "data": data}


def _preview_result(image: bytes, metadata: dict[str, Any]) -> ToolResult:
    payload = {"ok": True, "data": metadata}
    return ToolResult(
        content=[
            ImageContent(type="image", data=base64.b64encode(image).decode("ascii"), mimeType="image/png"),
            TextContent(type="text", text=json.dumps(payload, separators=(",", ":"))),
        ],
        structured_content=payload,
    )


def create_server(settings: Settings) -> FastMCP:
    application = Application(settings)
    mcp = FastMCP(name="detection-mcp")
    mcp.add_middleware(DomainErrorMiddleware())

    @mcp.tool
    def create_dataset(root_path: str, name: str | None = None) -> dict[str, Any]:
        """Register a dataset root without changing any source image."""
        return _success(application.create_dataset(root_path, name))

    @mcp.tool
    def delete_dataset(dataset_id: int) -> dict[str, Any]:
        """Soft-delete a dataset and preserve all related state."""
        return _success(application.delete_dataset(dataset_id))

    @mcp.tool
    def restore_dataset(dataset_id: int) -> dict[str, Any]:
        """Restore a soft-deleted dataset record."""
        return _success(application.restore_dataset(dataset_id))

    @mcp.tool
    def list_datasets(include_deleted: bool = False) -> dict[str, Any]:
        """List registered datasets."""
        return _success(application.list_datasets(include_deleted))

    @mcp.tool
    def get_dataset(dataset_id: int) -> dict[str, Any]:
        """Get dataset metadata, including a deleted dataset."""
        return _success(application.get_dataset(dataset_id))

    @mcp.tool
    def add_categories(dataset_id: int, categories: list[CategoryCreate]) -> dict[str, Any]:
        """Add categories atomically to an active dataset."""
        return _success(application.add_categories(dataset_id, categories))

    @mcp.tool
    def edit_category(
        dataset_id: int,
        category_id: int,
        name: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Change a category name or authoritative description."""
        return _success(application.edit_category(dataset_id, category_id, name, description))

    @mcp.tool
    def delete_category(dataset_id: int, category_id: int) -> dict[str, Any]:
        """Soft-delete a category and retain historical annotations."""
        return _success(application.delete_category(dataset_id, category_id))

    @mcp.tool
    def restore_category(
        dataset_id: int,
        category_id: int,
        new_name: str | None = None,
    ) -> dict[str, Any]:
        """Restore a category, optionally with a new non-conflicting name."""
        return _success(application.restore_category(dataset_id, category_id, new_name))

    @mcp.tool
    def list_categories(dataset_id: int, include_deleted: bool = False) -> dict[str, Any]:
        """List categories for a dataset."""
        return _success(application.list_categories(dataset_id, include_deleted))

    @mcp.tool
    def get_category(dataset_id: int, category_id: int) -> dict[str, Any]:
        """Get a category, including a soft-deleted category."""
        return _success(application.get_category(dataset_id, category_id))

    @mcp.tool
    def list_images(
        dataset_id: int,
        status: str = "all",
        order_by: str = "name",
        random_seed: int | None = None,
        offset: int = 0,
        max_results: int = 100,
    ) -> dict[str, Any]:
        """Discover dataset images with status filtering and stable ordering."""
        return _success(application.list_images(dataset_id, status, order_by, random_seed, offset, max_results))

    @mcp.tool
    def set_image_status(dataset_id: int, image_path: str, status: ImageStatus) -> dict[str, Any]:
        """Set annotation workflow status without changing the image."""
        return _success(application.set_image_status(dataset_id, image_path, status))

    @mcp.tool
    def preview_image(
        dataset_id: int,
        image_path: str,
        max_width: int | None = None,
        max_height: int | None = None,
        allow_upscale: bool = False,
    ) -> ToolResult:
        """Return an orientation-corrected image preview and size metadata."""
        image, metadata = application.preview_image(dataset_id, image_path, max_width, max_height, allow_upscale)
        return _preview_result(image, metadata)

    @mcp.tool
    def preview_annotations(
        dataset_id: int,
        image_path: str,
        annotation_type: str = "all",
        annotation_ids: list[int] | None = None,
        include_deleted_categories: bool = False,
        max_width: int | None = None,
        max_height: int | None = None,
    ) -> ToolResult:
        """Return an in-memory annotation overlay and structured metadata."""
        image, metadata = application.preview_annotations(
            dataset_id,
            image_path,
            annotation_type,
            annotation_ids,
            include_deleted_categories,
            max_width,
            max_height,
        )
        return _preview_result(image, metadata)

    @mcp.tool
    def list_annotations(
        dataset_id: int,
        image_path: str | None = None,
        annotation_type: str | None = None,
        category_ids: list[int] | None = None,
        annotation_ids: list[int] | None = None,
        include_deleted_categories: bool = False,
        offset: int = 0,
        max_results: int = 100,
    ) -> dict[str, Any]:
        """List annotations with stable filters and pagination."""
        return _success(
            application.list_annotations(
                dataset_id,
                image_path,
                annotation_type,
                category_ids,
                annotation_ids,
                include_deleted_categories,
                offset,
                max_results,
            )
        )

    @mcp.tool
    def add_bbox_annotations(
        dataset_id: int,
        image_path: str,
        annotations: list[BBoxCreate],
    ) -> dict[str, Any]:
        """Add normalized xyxy annotations in one transaction."""
        return _success(application.add_bbox_annotations(dataset_id, image_path, annotations))

    @mcp.tool
    def edit_bbox_annotation(
        dataset_id: int,
        annotation_id: int,
        category_id: int | None = None,
        bbox: list[float] | None = None,
    ) -> dict[str, Any]:
        """Edit a bbox annotation without changing its annotation type."""
        return _success(application.edit_bbox_annotation(dataset_id, annotation_id, category_id, bbox))

    @mcp.tool
    def delete_bbox_annotation(
        dataset_id: int,
        annotation_ids: list[int],
    ) -> dict[str, Any]:
        """Hard-delete one or more bbox annotations atomically."""
        return _success(application.delete_annotations(dataset_id, annotation_ids, AnnotationType.BBOX))

    @mcp.tool
    def add_rotated_bbox_annotations(
        dataset_id: int,
        image_path: str,
        annotations: list[RotatedBBoxCreate],
    ) -> dict[str, Any]:
        """Validate, correct, and add rotated bbox annotations atomically."""
        return _success(application.add_rotated_bbox_annotations(dataset_id, image_path, annotations))

    @mcp.tool
    def edit_rotated_bbox_annotation(
        dataset_id: int,
        annotation_id: int,
        category_id: int | None = None,
        polygon: list[float] | None = None,
    ) -> dict[str, Any]:
        """Edit a rotated bbox without changing its annotation type."""
        return _success(application.edit_rotated_bbox_annotation(dataset_id, annotation_id, category_id, polygon))

    @mcp.tool
    def delete_rotated_bbox_annotation(
        dataset_id: int,
        annotation_ids: list[int],
    ) -> dict[str, Any]:
        """Hard-delete one or more rotated bbox annotations atomically."""
        return _success(application.delete_annotations(dataset_id, annotation_ids, AnnotationType.ROTATED_BBOX))

    @mcp.tool
    def export_metadata_jsonl(
        dataset_id: int,
        output_path: str,
        export_mode: ExportMode = ExportMode.AUTOTRAIN,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Preflight and atomically export completed-image metadata."""
        return _success(application.export_metadata_jsonl(dataset_id, output_path, export_mode, overwrite))

    return mcp
