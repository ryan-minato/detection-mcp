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
from pydantic import BaseModel

from detection_mcp.config import Settings
from detection_mcp.errors import DomainError, ErrorCode
from detection_mcp.models import (
    AnnotationBatch,
    AnnotationList,
    AnnotationPreviewMetadata,
    AnnotationRecord,
    AnnotationType,
    BBoxCreate,
    CategoryCreate,
    CategoryList,
    CategoryRecord,
    DatasetList,
    DatasetRecord,
    DeletedAnnotations,
    ExportMode,
    ExportRecord,
    ImageList,
    ImageStatus,
    ImageStatusRecord,
    PreviewMetadata,
    RotatedAnnotationBatch,
    RotatedAnnotationRecord,
    RotatedBBoxCreate,
    SuccessEnvelope,
)
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
    """Convert application failures to stable structured MCP error results.

    Notes:
        Domain failures retain their public error code. SQLite and unexpected
        failures are logged to stderr and replaced with safe generic errors.
    """

    async def on_call_tool(
        self,
        context: MiddlewareContext,
        call_next: Callable[[MiddlewareContext], Awaitable[ToolResult]],
    ) -> ToolResult:
        """Invoke a tool and normalize failures at the MCP boundary.

        Args:
            context: FastMCP invocation context containing the requested tool.
            call_next: Remaining middleware and tool invocation callable.

        Returns:
            The original successful result or a structured error result.

        Notes:
            This boundary prevents internal exception details from reaching clients.
        """
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


def _success[ResponseT: BaseModel](model: type[ResponseT], data: dict[str, Any]) -> SuccessEnvelope[ResponseT]:
    """Validate application data and wrap it in a typed success envelope."""
    return SuccessEnvelope[ResponseT](data=model.model_validate(data))


def _preview_result[ResponseT: BaseModel](
    image: bytes,
    model: type[ResponseT],
    metadata: dict[str, Any],
) -> ToolResult:
    """Combine PNG content and metadata into a FastMCP tool result."""
    payload = _success(model, metadata).model_dump(mode="json")
    return ToolResult(
        content=[
            ImageContent(type="image", data=base64.b64encode(image).decode("ascii"), mimeType="image/png"),
            TextContent(type="text", text=json.dumps(payload, separators=(",", ":"))),
        ],
        structured_content=payload,
    )


def create_server(settings: Settings) -> FastMCP:
    """Create the configured FastMCP server and register all v1 tools.

    Args:
        settings: Validated application settings.

    Returns:
        A ready-to-run FastMCP server using STDIO when started by the CLI.

    Raises:
        OSError: If the database directory cannot be initialized.
        sqlite3.Error: If database initialization or migration fails.

    Notes:
        Tool failures are normalized by ``DomainErrorMiddleware``; source images
        remain outside application state and are always treated as immutable.
    """
    application = Application(settings)
    mcp = FastMCP(name="detection-mcp")
    mcp.add_middleware(DomainErrorMiddleware())

    @mcp.tool
    def create_dataset(root_path: str, name: str | None = None) -> SuccessEnvelope[DatasetRecord]:
        """Register a dataset root without changing any source image.

        Args:
            root_path: Existing, authorized directory containing source images.
            name: Optional display name for the dataset.

        Returns:
            A success envelope containing the created dataset record.

        Raises:
            DomainError: If the root is unavailable or outside allowed roots.

        Notes:
            The resolved root path is stored; no source file is written or moved.
        """
        return _success(DatasetRecord, application.create_dataset(root_path, name))

    @mcp.tool
    def delete_dataset(dataset_id: int) -> SuccessEnvelope[DatasetRecord]:
        """Soft-delete a dataset and preserve all related state.

        Args:
            dataset_id: Dataset identifier to soft-delete.

        Returns:
            A success envelope containing the deleted dataset record.

        Raises:
            DomainError: If the dataset does not exist.

        Notes:
            Deletion is idempotent and never affects source images.
        """
        return _success(DatasetRecord, application.delete_dataset(dataset_id))

    @mcp.tool
    def restore_dataset(dataset_id: int) -> SuccessEnvelope[DatasetRecord]:
        """Restore a soft-deleted dataset record.

        Args:
            dataset_id: Dataset identifier to restore.

        Returns:
            A success envelope containing the active dataset record.

        Raises:
            DomainError: If the dataset does not exist.

        Notes:
            Restoration changes only stored annotation state.
        """
        return _success(DatasetRecord, application.restore_dataset(dataset_id))

    @mcp.tool
    def list_datasets(include_deleted: bool = False) -> SuccessEnvelope[DatasetList]:
        """List registered datasets.

        Args:
            include_deleted: Whether soft-deleted datasets are included.

        Returns:
            A success envelope containing ordered records and their count.

        Raises:
            DomainError: If the storage operation fails.

        Notes:
            Results are ordered by stable dataset identifier.
        """
        return _success(DatasetList, application.list_datasets(include_deleted))

    @mcp.tool
    def get_dataset(dataset_id: int) -> SuccessEnvelope[DatasetRecord]:
        """Get dataset metadata, including a deleted dataset.

        Args:
            dataset_id: Dataset identifier to fetch.

        Returns:
            A success envelope containing the dataset record.

        Raises:
            DomainError: If the dataset does not exist.

        Notes:
            Deletion state does not hide a directly requested record.
        """
        return _success(DatasetRecord, application.get_dataset(dataset_id))

    @mcp.tool
    def add_categories(dataset_id: int, categories: list[CategoryCreate]) -> SuccessEnvelope[CategoryList]:
        """Add categories atomically to an active dataset.

        Args:
            dataset_id: Active dataset that will own the categories.
            categories: Non-empty category creation requests.

        Returns:
            A success envelope containing created records and their count.

        Raises:
            DomainError: If the dataset is unavailable, input is empty, a name
                conflicts, or the batch transaction fails.

        Notes:
            One invalid category rolls back the complete batch.
        """
        return _success(CategoryList, application.add_categories(dataset_id, categories))

    @mcp.tool
    def edit_category(
        dataset_id: int,
        category_id: int,
        name: str | None = None,
        description: str | None = None,
    ) -> SuccessEnvelope[CategoryRecord]:
        """Change a category name or authoritative description.

        Args:
            dataset_id: Active owning dataset identifier.
            category_id: Category identifier to edit.
            name: Optional replacement name.
            description: Optional replacement description.

        Returns:
            A success envelope containing the updated category record.

        Raises:
            DomainError: If no change is supplied, a name is invalid or conflicts,
                or the dataset or category is unavailable.

        Notes:
            Omitted fields retain their existing values.
        """
        return _success(CategoryRecord, application.edit_category(dataset_id, category_id, name, description))

    @mcp.tool
    def delete_category(dataset_id: int, category_id: int) -> SuccessEnvelope[CategoryRecord]:
        """Soft-delete a category and retain historical annotations.

        Args:
            dataset_id: Active owning dataset identifier.
            category_id: Category identifier to soft-delete.

        Returns:
            A success envelope containing the deleted category record.

        Raises:
            DomainError: If the dataset or category is unavailable.

        Notes:
            Existing annotations remain stored for history and restoration.
        """
        return _success(CategoryRecord, application.delete_category(dataset_id, category_id))

    @mcp.tool
    def restore_category(
        dataset_id: int,
        category_id: int,
        new_name: str | None = None,
    ) -> SuccessEnvelope[CategoryRecord]:
        """Restore a category, optionally under a new name.

        Args:
            dataset_id: Active owning dataset identifier.
            category_id: Category identifier to restore.
            new_name: Optional replacement name used during restoration.

        Returns:
            A success envelope containing the restored category record.

        Raises:
            DomainError: If the dataset or category is unavailable or the final
                name is empty or conflicts with an active category.

        Notes:
            Omit ``new_name`` to reuse the category's stored name.
        """
        return _success(CategoryRecord, application.restore_category(dataset_id, category_id, new_name))

    @mcp.tool
    def list_categories(dataset_id: int, include_deleted: bool = False) -> SuccessEnvelope[CategoryList]:
        """List categories for a dataset.

        Args:
            dataset_id: Owning dataset identifier.
            include_deleted: Whether soft-deleted categories are included.

        Returns:
            A success envelope containing ordered categories and their count.

        Raises:
            DomainError: If the dataset does not exist.

        Notes:
            Results are ordered by stable category identifier.
        """
        return _success(CategoryList, application.list_categories(dataset_id, include_deleted))

    @mcp.tool
    def get_category(dataset_id: int, category_id: int) -> SuccessEnvelope[CategoryRecord]:
        """Get a category, including a soft-deleted category.

        Args:
            dataset_id: Owning dataset identifier.
            category_id: Category identifier to fetch.

        Returns:
            A success envelope containing the category record.

        Raises:
            DomainError: If the dataset or category does not exist.

        Notes:
            Deletion state does not hide a directly requested record.
        """
        return _success(CategoryRecord, application.get_category(dataset_id, category_id))

    @mcp.tool
    def list_images(
        dataset_id: int,
        status: str = "all",
        order_by: str = "name",
        random_seed: int | None = None,
        offset: int = 0,
        max_results: int = 100,
    ) -> SuccessEnvelope[ImageList]:
        """Discover dataset images with status filtering and stable ordering.

        Args:
            dataset_id: Dataset identifier to scan.
            status: Workflow status filter or ``all``.
            order_by: ``name`` or deterministic ``random`` ordering.
            random_seed: Optional seed overriding server configuration.
            offset: Zero-based result offset.
            max_results: Positive page size.

        Returns:
            A success envelope containing image records and page metadata.

        Raises:
            DomainError: If filters, pagination, dataset, or its root are invalid.

        Notes:
            Discovery is read-only; untracked images default to ``unannotated``.
        """
        return _success(
            ImageList, application.list_images(dataset_id, status, order_by, random_seed, offset, max_results)
        )

    @mcp.tool
    def set_image_status(
        dataset_id: int,
        image_path: str,
        status: ImageStatus,
    ) -> SuccessEnvelope[ImageStatusRecord]:
        """Set annotation workflow status without changing the image.

        Args:
            dataset_id: Active owning dataset identifier.
            image_path: Dataset-relative image path.
            status: New workflow status.

        Returns:
            A success envelope containing normalized status state.

        Raises:
            DomainError: If the dataset or image is unavailable or disallowed.

        Notes:
            Only SQLite workflow state changes; source pixels and metadata do not.
        """
        return _success(ImageStatusRecord, application.set_image_status(dataset_id, image_path, status))

    @mcp.tool(output_schema=SuccessEnvelope[PreviewMetadata].model_json_schema())
    def preview_image(
        dataset_id: int,
        image_path: str,
        max_width: int | None = None,
        max_height: int | None = None,
        allow_upscale: bool = False,
    ) -> ToolResult:
        """Return an orientation-corrected preview and size metadata.

        Args:
            dataset_id: Owning dataset identifier.
            image_path: Dataset-relative source image path.
            max_width: Optional requested width limit.
            max_height: Optional requested height limit.
            allow_upscale: Whether a small image may be enlarged.

        Returns:
            A tool result containing PNG image content and structured metadata.

        Raises:
            DomainError: If dimensions, dataset, path, or decoding are invalid.

        Notes:
            Dimensions are clamped to server limits and no file is written.
        """
        image, metadata = application.preview_image(dataset_id, image_path, max_width, max_height, allow_upscale)
        return _preview_result(image, PreviewMetadata, metadata)

    @mcp.tool(output_schema=SuccessEnvelope[AnnotationPreviewMetadata].model_json_schema())
    def preview_annotations(
        dataset_id: int,
        image_path: str,
        annotation_type: str = "all",
        annotation_ids: list[int] | None = None,
        include_deleted_categories: bool = False,
        max_width: int | None = None,
        max_height: int | None = None,
    ) -> ToolResult:
        """Return an in-memory annotation overlay and metadata.

        Args:
            dataset_id: Owning dataset identifier.
            image_path: Dataset-relative source image path.
            annotation_type: Geometry type filter or ``all``.
            annotation_ids: Optional identifiers to render.
            include_deleted_categories: Whether deleted-category annotations render.
            max_width: Optional requested width limit.
            max_height: Optional requested height limit.

        Returns:
            A tool result containing overlay PNG content and structured metadata.

        Raises:
            DomainError: If filters, dimensions, records, path, or decoding are
                invalid.

        Notes:
            The preview never upscales and never modifies the source image.
        """
        image, metadata = application.preview_annotations(
            dataset_id,
            image_path,
            annotation_type,
            annotation_ids,
            include_deleted_categories,
            max_width,
            max_height,
        )
        return _preview_result(image, AnnotationPreviewMetadata, metadata)

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
    ) -> SuccessEnvelope[AnnotationList]:
        """List annotations with stable filters and pagination.

        Args:
            dataset_id: Owning dataset identifier.
            image_path: Optional dataset-relative image filter.
            annotation_type: Optional geometry type filter or ``all``.
            category_ids: Optional category identifiers to include.
            annotation_ids: Optional annotation identifiers to include.
            include_deleted_categories: Whether deleted-category records are shown.
            offset: Zero-based result offset.
            max_results: Positive page size.

        Returns:
            A success envelope containing decoded records and page metadata.

        Raises:
            DomainError: If filters, pagination, dataset, or image are invalid.

        Notes:
            Results are ordered by stable annotation identifier.
        """
        return _success(
            AnnotationList,
            application.list_annotations(
                dataset_id,
                image_path,
                annotation_type,
                category_ids,
                annotation_ids,
                include_deleted_categories,
                offset,
                max_results,
            ),
        )

    @mcp.tool
    def add_bbox_annotations(
        dataset_id: int,
        image_path: str,
        annotations: list[BBoxCreate],
    ) -> SuccessEnvelope[AnnotationBatch]:
        """Add normalized xyxy annotations in one transaction.

        Args:
            dataset_id: Active owning dataset identifier.
            image_path: Dataset-relative target image path.
            annotations: Non-empty axis-aligned annotation requests.

        Returns:
            A success envelope containing created records and their count.

        Raises:
            DomainError: If the batch, target, category, or geometry is invalid.

        Notes:
            All annotations are validated before any record is inserted.
        """
        return _success(AnnotationBatch, application.add_bbox_annotations(dataset_id, image_path, annotations))

    @mcp.tool
    def edit_bbox_annotation(
        dataset_id: int,
        annotation_id: int,
        category_id: int | None = None,
        bbox: list[float] | None = None,
    ) -> SuccessEnvelope[AnnotationRecord]:
        """Edit a bbox annotation without changing its type.

        Args:
            dataset_id: Active owning dataset identifier.
            annotation_id: Axis-aligned annotation identifier.
            category_id: Optional replacement active category.
            bbox: Optional replacement normalized xyxy geometry.

        Returns:
            A success envelope containing the updated record.

        Raises:
            DomainError: If no change is supplied or a record or geometry is invalid.

        Notes:
            Omitted fields retain their existing values.
        """
        return _success(
            AnnotationRecord,
            application.edit_bbox_annotation(dataset_id, annotation_id, category_id, bbox),
        )

    @mcp.tool
    def delete_bbox_annotation(
        dataset_id: int,
        annotation_ids: list[int],
    ) -> SuccessEnvelope[DeletedAnnotations]:
        """Hard-delete one or more bbox annotations atomically.

        Args:
            dataset_id: Active owning dataset identifier.
            annotation_ids: Non-empty axis-aligned annotation identifiers.

        Returns:
            A success envelope containing deleted identifiers and their count.

        Raises:
            DomainError: If input is empty or any dataset, annotation, or type does
                not match.

        Notes:
            Every identifier is validated before deletion begins.
        """
        return _success(
            DeletedAnnotations,
            application.delete_annotations(dataset_id, annotation_ids, AnnotationType.BBOX),
        )

    @mcp.tool
    def add_rotated_bbox_annotations(
        dataset_id: int,
        image_path: str,
        annotations: list[RotatedBBoxCreate],
    ) -> SuccessEnvelope[RotatedAnnotationBatch]:
        """Validate, correct, and add rotated annotations atomically.

        Args:
            dataset_id: Active owning dataset identifier.
            image_path: Dataset-relative target image path.
            annotations: Non-empty rotated annotation requests.

        Returns:
            A success envelope containing records and correction metadata.

        Raises:
            DomainError: If the batch, target, category, polygon, or correction is
                invalid.

        Notes:
            All annotations are validated before canonical geometry is inserted.
        """
        return _success(
            RotatedAnnotationBatch,
            application.add_rotated_bbox_annotations(dataset_id, image_path, annotations),
        )

    @mcp.tool
    def edit_rotated_bbox_annotation(
        dataset_id: int,
        annotation_id: int,
        category_id: int | None = None,
        polygon: list[float] | None = None,
    ) -> SuccessEnvelope[RotatedAnnotationRecord]:
        """Edit a rotated annotation without changing its type.

        Args:
            dataset_id: Active owning dataset identifier.
            annotation_id: Rotated annotation identifier.
            category_id: Optional replacement active category.
            polygon: Optional replacement normalized polygon.

        Returns:
            A success envelope containing the updated record and correction data.

        Raises:
            DomainError: If no change is supplied or a record, polygon, or
                correction is invalid.

        Notes:
            Omitted fields retain their existing values.
        """
        return _success(
            RotatedAnnotationRecord,
            application.edit_rotated_bbox_annotation(dataset_id, annotation_id, category_id, polygon),
        )

    @mcp.tool
    def delete_rotated_bbox_annotation(
        dataset_id: int,
        annotation_ids: list[int],
    ) -> SuccessEnvelope[DeletedAnnotations]:
        """Hard-delete one or more rotated annotations atomically.

        Args:
            dataset_id: Active owning dataset identifier.
            annotation_ids: Non-empty rotated annotation identifiers.

        Returns:
            A success envelope containing deleted identifiers and their count.

        Raises:
            DomainError: If input is empty or any dataset, annotation, or type does
                not match.

        Notes:
            Every identifier is validated before deletion begins.
        """
        return _success(
            DeletedAnnotations,
            application.delete_annotations(dataset_id, annotation_ids, AnnotationType.ROTATED_BBOX),
        )

    @mcp.tool
    def export_metadata_jsonl(
        dataset_id: int,
        output_path: str,
        export_mode: ExportMode = ExportMode.AUTOTRAIN,
        overwrite: bool = False,
    ) -> SuccessEnvelope[ExportRecord]:
        """Preflight and atomically export completed-image metadata.

        Args:
            dataset_id: Active dataset identifier to export.
            output_path: Authorized destination file path.
            export_mode: AutoTrain-compatible or extended layout.
            overwrite: Whether an existing destination may be replaced.

        Returns:
            A success envelope containing counts, mapping, and destination data.

        Raises:
            DomainError: If dataset, destination, image, layout, or write lock
                validation fails.

        Notes:
            Only completed images are exported. Output replacement is atomic and
            source images remain immutable.
        """
        return _success(
            ExportRecord,
            application.export_metadata_jsonl(dataset_id, output_path, export_mode, overwrite),
        )

    return mcp
