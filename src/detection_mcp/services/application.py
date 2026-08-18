"""Application service coordinating domain and persistence operations."""

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from detection_mcp.config import Settings
from detection_mcp.db.connection import Database
from detection_mcp.db.repositories import Repository, inserted_id, now, row_dict
from detection_mcp.errors import DomainError, ErrorCode
from detection_mcp.models import AnnotationType, BBoxCreate, CategoryCreate, ExportMode, ImageStatus, RotatedBBoxCreate
from detection_mcp.services.exporter import export_metadata
from detection_mcp.services.geometry import validate_bbox, validate_rotated_bbox
from detection_mcp.services.images import discover_images
from detection_mcp.services.paths import resolve_dataset_root, resolve_image, resolve_output
from detection_mcp.services.preview import render_preview


class Application:
    """Coordinate validation, persistence, image access, and exports.

    Args:
        settings: Validated runtime configuration.

    Raises:
        OSError: If the database directory cannot be created.
        sqlite3.Error: If database initialization fails.

    Notes:
        This service owns annotation state but treats dataset images as immutable.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.database = Database(settings.db_path)
        self.repository = Repository()
        self.database.initialize()

    def create_dataset(self, root_path: str, name: str | None = None) -> dict[str, Any]:
        """Register an authorized dataset root.

        Args:
            root_path: Existing directory containing source images.
            name: Optional display name for the dataset.

        Returns:
            The newly persisted dataset record.

        Raises:
            DomainError: If the root is unavailable or not allowed.
            sqlite3.Error: If the dataset cannot be persisted.

        Notes:
            Registration stores the resolved path and never changes source files.
        """
        root = resolve_dataset_root(root_path, self.settings.allowed_dataset_roots)
        timestamp = now()
        with self.database.transaction() as connection:
            cursor = connection.execute(
                "INSERT INTO datasets(name, root_path, deleted_at, created_at, updated_at) VALUES (?, ?, NULL, ?, ?)",
                (name.strip() if name else None, str(root), timestamp, timestamp),
            )
            row = self.repository.dataset(connection, inserted_id(cursor))
            return row_dict(row)

    def delete_dataset(self, dataset_id: int) -> dict[str, Any]:
        """Soft-delete a dataset and preserve its related state.

        Args:
            dataset_id: Dataset identifier to delete.

        Returns:
            The dataset record with its deletion timestamp.

        Raises:
            DomainError: If the dataset does not exist.
            sqlite3.Error: If the update fails.

        Notes:
            Repeated deletion is idempotent and source images remain untouched.
        """
        with self.database.transaction() as connection:
            self.repository.dataset(connection, dataset_id)
            connection.execute(
                "UPDATE datasets SET deleted_at = COALESCE(deleted_at, ?), updated_at = ? WHERE id = ?",
                (now(), now(), dataset_id),
            )
            return row_dict(self.repository.dataset(connection, dataset_id))

    def restore_dataset(self, dataset_id: int) -> dict[str, Any]:
        """Restore a soft-deleted dataset record.

        Args:
            dataset_id: Dataset identifier to restore.

        Returns:
            The active dataset record.

        Raises:
            DomainError: If the dataset does not exist.
            sqlite3.Error: If the update fails.
        """
        with self.database.transaction() as connection:
            self.repository.dataset(connection, dataset_id)
            connection.execute(
                "UPDATE datasets SET deleted_at = NULL, updated_at = ? WHERE id = ?",
                (now(), dataset_id),
            )
            return row_dict(self.repository.dataset(connection, dataset_id))

    def list_datasets(self, include_deleted: bool = False) -> dict[str, Any]:
        """List registered datasets in identifier order.

        Args:
            include_deleted: Whether soft-deleted records are included.

        Returns:
            Dataset records and their count.

        Raises:
            sqlite3.Error: If the query fails.
        """
        query = "SELECT * FROM datasets"
        if not include_deleted:
            query += " WHERE deleted_at IS NULL"
        query += " ORDER BY id"
        with self.database.connect() as connection:
            datasets = [row_dict(row) for row in connection.execute(query)]
        return {"datasets": datasets, "count": len(datasets)}

    def get_dataset(self, dataset_id: int) -> dict[str, Any]:
        """Get one dataset regardless of deletion state.

        Args:
            dataset_id: Dataset identifier to fetch.

        Returns:
            The matching dataset record.

        Raises:
            DomainError: If the dataset does not exist.
            sqlite3.Error: If the query fails.
        """
        with self.database.connect() as connection:
            return row_dict(self.repository.dataset(connection, dataset_id))

    def add_categories(self, dataset_id: int, categories: list[CategoryCreate]) -> dict[str, Any]:
        """Add a non-empty category batch atomically.

        Args:
            dataset_id: Active dataset that will own the categories.
            categories: Validated category creation requests.

        Returns:
            Created category records and their count.

        Raises:
            DomainError: If input is empty, the dataset is unavailable, names
                conflict, or the transaction fails.

        Notes:
            Any invalid category rolls back the complete batch.
        """
        if not categories:
            raise DomainError(ErrorCode.INVALID_ARGUMENT, "categories must not be empty", field="categories")
        timestamp = now()
        try:
            # Validate ownership and persist the complete category batch together.
            with self.database.transaction() as connection:
                self.repository.active_dataset(connection, dataset_id)
                created: list[dict[str, Any]] = []
                for index, category in enumerate(categories):
                    try:
                        cursor = connection.execute(
                            "INSERT INTO categories(dataset_id, name, description, deleted_at, created_at, updated_at) "
                            "VALUES (?, ?, ?, NULL, ?, ?)",
                            (dataset_id, category.name, category.description, timestamp, timestamp),
                        )
                    except sqlite3.IntegrityError as error:
                        raise DomainError(
                            ErrorCode.CATEGORY_NAME_CONFLICT,
                            "active category names must be unique within a dataset",
                            field=f"categories[{index}].name",
                            details={"name": category.name},
                        ) from error
                    created.append(row_dict(self.repository.category(connection, dataset_id, inserted_id(cursor))))
                return {"categories": created, "count": len(created)}
        except DomainError:
            raise
        except sqlite3.Error as error:
            raise DomainError(ErrorCode.TRANSACTION_FAILED, "category batch transaction failed") from error

    def edit_category(
        self,
        dataset_id: int,
        category_id: int,
        name: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Update a category name, description, or both.

        Args:
            dataset_id: Active owning dataset identifier.
            category_id: Category identifier to update.
            name: Optional replacement name.
            description: Optional replacement authoritative description.

        Returns:
            The updated category record.

        Raises:
            DomainError: If no field is supplied, a name is invalid or conflicts,
                or the dataset or category is unavailable.
            sqlite3.Error: If the update fails.
        """
        if name is None and description is None:
            raise DomainError(ErrorCode.INVALID_ARGUMENT, "name or description is required")
        if name is not None and not name.strip():
            raise DomainError(ErrorCode.INVALID_ARGUMENT, "category name must not be empty", field="name")
        with self.database.transaction() as connection:
            self.repository.active_dataset(connection, dataset_id)
            category = self.repository.category(connection, dataset_id, category_id)
            final_name = name.strip() if name is not None else category["name"]
            final_description = description if description is not None else category["description"]
            try:
                connection.execute(
                    "UPDATE categories SET name = ?, description = ?, updated_at = ? WHERE id = ?",
                    (final_name, final_description, now(), category_id),
                )
            except sqlite3.IntegrityError as error:
                raise DomainError(
                    ErrorCode.CATEGORY_NAME_CONFLICT,
                    "active category names must be unique within a dataset",
                    field="name",
                ) from error
            return row_dict(self.repository.category(connection, dataset_id, category_id))

    def delete_category(self, dataset_id: int, category_id: int) -> dict[str, Any]:
        """Soft-delete a category while preserving its annotations.

        Args:
            dataset_id: Active owning dataset identifier.
            category_id: Category identifier to delete.

        Returns:
            The category record with its deletion timestamp.

        Raises:
            DomainError: If the dataset or category is unavailable.
            sqlite3.Error: If the update fails.
        """
        with self.database.transaction() as connection:
            self.repository.active_dataset(connection, dataset_id)
            self.repository.category(connection, dataset_id, category_id)
            timestamp = now()
            connection.execute(
                "UPDATE categories SET deleted_at = COALESCE(deleted_at, ?), updated_at = ? WHERE id = ?",
                (timestamp, timestamp, category_id),
            )
            return row_dict(self.repository.category(connection, dataset_id, category_id))

    def restore_category(self, dataset_id: int, category_id: int, new_name: str | None = None) -> dict[str, Any]:
        """Restore a category with an optional replacement name.

        Args:
            dataset_id: Active owning dataset identifier.
            category_id: Category identifier to restore.
            new_name: Optional non-conflicting name used during restoration.

        Returns:
            The restored category record.

        Raises:
            DomainError: If the dataset or category is unavailable or the final
                name is empty or conflicts with an active category.
            sqlite3.Error: If the update fails.
        """
        with self.database.transaction() as connection:
            self.repository.active_dataset(connection, dataset_id)
            category = self.repository.category(connection, dataset_id, category_id)
            final_name = new_name.strip() if new_name is not None else category["name"]
            if not final_name:
                raise DomainError(ErrorCode.INVALID_ARGUMENT, "category name must not be empty", field="new_name")
            try:
                connection.execute(
                    "UPDATE categories SET name = ?, deleted_at = NULL, updated_at = ? WHERE id = ?",
                    (final_name, now(), category_id),
                )
            except sqlite3.IntegrityError as error:
                raise DomainError(
                    ErrorCode.CATEGORY_NAME_CONFLICT,
                    "restored category name conflicts with an active category",
                    field="new_name" if new_name is not None else "name",
                ) from error
            return row_dict(self.repository.category(connection, dataset_id, category_id))

    def list_categories(self, dataset_id: int, include_deleted: bool = False) -> dict[str, Any]:
        """List a dataset's categories in identifier order.

        Args:
            dataset_id: Owning dataset identifier.
            include_deleted: Whether soft-deleted categories are included.

        Returns:
            Category records and their count.

        Raises:
            DomainError: If the dataset does not exist.
            sqlite3.Error: If the query fails.
        """
        with self.database.connect() as connection:
            self.repository.dataset(connection, dataset_id)
            query = "SELECT * FROM categories WHERE dataset_id = ?"
            if not include_deleted:
                query += " AND deleted_at IS NULL"
            query += " ORDER BY id"
            categories = [row_dict(row) for row in connection.execute(query, (dataset_id,))]
        return {"categories": categories, "count": len(categories)}

    def get_category(self, dataset_id: int, category_id: int) -> dict[str, Any]:
        """Get one category regardless of deletion state.

        Args:
            dataset_id: Owning dataset identifier.
            category_id: Category identifier to fetch.

        Returns:
            The matching category record.

        Raises:
            DomainError: If the dataset or category does not exist.
            sqlite3.Error: If the query fails.
        """
        with self.database.connect() as connection:
            self.repository.dataset(connection, dataset_id)
            return row_dict(self.repository.category(connection, dataset_id, category_id))

    def _dataset_root(self, connection: sqlite3.Connection, dataset_id: int, *, active: bool = False) -> Path:
        """Resolve a stored dataset root and optionally require active state."""
        dataset = (
            self.repository.active_dataset(connection, dataset_id)
            if active
            else self.repository.dataset(connection, dataset_id)
        )
        return resolve_dataset_root(dataset["root_path"], self.settings.allowed_dataset_roots)

    def list_images(
        self,
        dataset_id: int,
        status: str = "all",
        order_by: str = "name",
        random_seed: int | None = None,
        offset: int = 0,
        max_results: int = 100,
    ) -> dict[str, Any]:
        """Discover and page images with stable status-aware ordering.

        Args:
            dataset_id: Dataset identifier to scan.
            status: Workflow status filter or ``all``.
            order_by: ``name`` for lexical order or ``random`` for stable shuffle.
            random_seed: Optional shuffle seed overriding configuration.
            offset: Zero-based result offset.
            max_results: Positive page size.

        Returns:
            Image records, total count, page metadata, and effective seed.

        Raises:
            DomainError: If filters or pagination are invalid, the dataset root is
                unavailable, or the dataset does not exist.

        Notes:
            Random order is deterministic for dataset, seed, and image path.
        """
        if status not in {"all", *(item.value for item in ImageStatus)}:
            raise DomainError(ErrorCode.INVALID_ARGUMENT, "invalid image status", field="status")
        if order_by not in {"name", "random"}:
            raise DomainError(ErrorCode.INVALID_ARGUMENT, "order_by must be 'name' or 'random'", field="order_by")
        if offset < 0 or max_results <= 0:
            raise DomainError(ErrorCode.INVALID_ARGUMENT, "offset must be non-negative and max_results positive")
        with self.database.connect() as connection:
            root = self._dataset_root(connection, dataset_id)
            states = {
                row["image_path"]: row["status"]
                for row in connection.execute(
                    "SELECT image_path, status FROM image_states WHERE dataset_id = ?", (dataset_id,)
                )
            }
        # Merge discovered immutable files with workflow state from SQLite.
        images = [
            {"image_path": path, "status": states.get(path, ImageStatus.UNANNOTATED.value)}
            for path in discover_images(root)
        ]
        if status != "all":
            images = [image for image in images if image["status"] == status]
        seed = self.settings.random_seed if random_seed is None else random_seed
        if order_by == "random":
            images.sort(
                key=lambda image: hashlib.sha256(f"{dataset_id}\0{seed}\0{image['image_path']}".encode()).digest()
            )
        total = len(images)
        selected = images[offset : offset + max_results]
        return {"images": selected, "total": total, "offset": offset, "count": len(selected), "random_seed": seed}

    def set_image_status(self, dataset_id: int, image_path: str, status: ImageStatus) -> dict[str, Any]:
        """Set workflow status for an existing source image.

        Args:
            dataset_id: Active owning dataset identifier.
            image_path: Dataset-relative source image path.
            status: New annotation workflow state.

        Returns:
            The normalized image path, status, and update timestamp.

        Raises:
            DomainError: If the dataset or image is unavailable or disallowed.
            sqlite3.Error: If the state cannot be persisted.

        Notes:
            Only SQLite state changes; the source image remains immutable.
        """
        with self.database.transaction() as connection:
            root = self._dataset_root(connection, dataset_id, active=True)
            relative, _ = resolve_image(root, image_path)
            timestamp = now()
            connection.execute(
                "INSERT INTO image_states(dataset_id, image_path, status, updated_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(dataset_id, image_path) DO UPDATE SET "
                "status = excluded.status, updated_at = excluded.updated_at",
                (dataset_id, relative, status.value, timestamp),
            )
            return {"dataset_id": dataset_id, "image_path": relative, "status": status.value, "updated_at": timestamp}

    def _validate_annotation_target(
        self,
        connection: sqlite3.Connection,
        dataset_id: int,
        image_path: str,
        category_id: int,
    ) -> tuple[str, Path]:
        """Validate active dataset, image, and category ownership together."""
        root = self._dataset_root(connection, dataset_id, active=True)
        relative, absolute = resolve_image(root, image_path)
        self.repository.active_category(connection, dataset_id, category_id)
        return relative, absolute

    def add_bbox_annotations(
        self,
        dataset_id: int,
        image_path: str,
        annotations: list[BBoxCreate],
    ) -> dict[str, Any]:
        """Validate and add axis-aligned annotations atomically.

        Args:
            dataset_id: Active owning dataset identifier.
            image_path: Dataset-relative target image path.
            annotations: Non-empty validated annotation requests.

        Returns:
            Created annotation records and their count.

        Raises:
            DomainError: If the batch, target, category, or geometry is invalid.
            sqlite3.Error: If persistence fails.

        Notes:
            The complete batch is validated before any annotation is inserted.
        """
        if not annotations:
            raise DomainError(ErrorCode.INVALID_ARGUMENT, "annotations must not be empty", field="annotations")
        with self.database.transaction() as connection:
            # Validate every target and geometry before persisting the batch.
            prepared: list[tuple[int, list[float]]] = []
            relative: str | None = None
            for index, annotation in enumerate(annotations):
                relative, _ = self._validate_annotation_target(
                    connection, dataset_id, image_path, annotation.category_id
                )
                prepared.append(
                    (annotation.category_id, validate_bbox(annotation.bbox, field=f"annotations[{index}].bbox"))
                )
            # Insert the prepared batch within the same transaction.
            timestamp = now()
            created = []
            for category_id, geometry in prepared:
                cursor = connection.execute(
                    "INSERT INTO annotations("
                    "dataset_id, image_path, type, category_id, geometry_json, created_at, updated_at"
                    ") "
                    "VALUES (?, ?, 'bbox', ?, ?, ?, ?)",
                    (dataset_id, relative, category_id, json.dumps(geometry), timestamp, timestamp),
                )
                created.append(
                    self.repository.annotation_dict(
                        self.repository.annotation(
                            connection, dataset_id, inserted_id(cursor), AnnotationType.BBOX.value
                        )
                    )
                )
            return {"annotations": created, "count": len(created)}

    def edit_bbox_annotation(
        self,
        dataset_id: int,
        annotation_id: int,
        category_id: int | None = None,
        bbox: list[float] | None = None,
    ) -> dict[str, Any]:
        """Update category, geometry, or both for an axis-aligned annotation.

        Args:
            dataset_id: Active owning dataset identifier.
            annotation_id: Axis-aligned annotation identifier.
            category_id: Optional replacement active category.
            bbox: Optional replacement normalized xyxy geometry.

        Returns:
            The updated annotation record.

        Raises:
            DomainError: If no change is supplied or any referenced record or
                geometry is invalid.
            sqlite3.Error: If the update fails.

        Notes:
            The annotation type cannot be changed by this operation.
        """
        if category_id is None and bbox is None:
            raise DomainError(ErrorCode.INVALID_ARGUMENT, "category_id or bbox is required")
        with self.database.transaction() as connection:
            self.repository.active_dataset(connection, dataset_id)
            existing = self.repository.annotation(connection, dataset_id, annotation_id, AnnotationType.BBOX.value)
            final_category = existing["category_id"] if category_id is None else category_id
            self.repository.active_category(connection, dataset_id, final_category)
            final_geometry = json.loads(existing["geometry_json"]) if bbox is None else validate_bbox(bbox)
            connection.execute(
                "UPDATE annotations SET category_id = ?, geometry_json = ?, updated_at = ? WHERE id = ?",
                (final_category, json.dumps(final_geometry), now(), annotation_id),
            )
            return self.repository.annotation_dict(
                self.repository.annotation(connection, dataset_id, annotation_id, AnnotationType.BBOX.value)
            )

    def add_rotated_bbox_annotations(
        self,
        dataset_id: int,
        image_path: str,
        annotations: list[RotatedBBoxCreate],
    ) -> dict[str, Any]:
        """Validate, correct, and add rotated annotations atomically.

        Args:
            dataset_id: Active owning dataset identifier.
            image_path: Dataset-relative target image path.
            annotations: Non-empty validated rotated annotation requests.

        Returns:
            Created records with submitted, stored, and correction metadata.

        Raises:
            DomainError: If the batch, target, category, or polygon is invalid.
            sqlite3.Error: If persistence fails.

        Notes:
            The complete batch is validated before any annotation is inserted.
        """
        if not annotations:
            raise DomainError(ErrorCode.INVALID_ARGUMENT, "annotations must not be empty", field="annotations")
        with self.database.transaction() as connection:
            # Validate and correct every polygon before persisting the batch.
            prepared: list[tuple[int, Any]] = []
            relative: str | None = None
            for index, annotation in enumerate(annotations):
                relative, _ = self._validate_annotation_target(
                    connection, dataset_id, image_path, annotation.category_id
                )
                geometry = validate_rotated_bbox(
                    annotation.polygon,
                    correction_enabled=self.settings.rotated_correction_enabled,
                    correction_threshold=self.settings.rotated_correction_threshold,
                    error_threshold=self.settings.rotated_error_threshold,
                    field=f"annotations[{index}].polygon",
                )
                prepared.append((annotation.category_id, geometry))
            # Persist canonical geometry while returning correction diagnostics.
            timestamp = now()
            created = []
            for category_id, geometry in prepared:
                cursor = connection.execute(
                    "INSERT INTO annotations("
                    "dataset_id, image_path, type, category_id, geometry_json, created_at, updated_at"
                    ") "
                    "VALUES (?, ?, 'rotated_bbox', ?, ?, ?, ?)",
                    (dataset_id, relative, category_id, json.dumps(geometry.stored_geometry), timestamp, timestamp),
                )
                record = self.repository.annotation_dict(
                    self.repository.annotation(
                        connection, dataset_id, inserted_id(cursor), AnnotationType.ROTATED_BBOX.value
                    )
                )
                record.update(
                    {
                        "submitted_geometry": geometry.submitted_geometry,
                        "stored_geometry": geometry.stored_geometry,
                        "corrected": geometry.corrected,
                        "deviation": geometry.deviation,
                        "warning": geometry.warning,
                    }
                )
                created.append(record)
            return {"annotations": created, "count": len(created)}

    def edit_rotated_bbox_annotation(
        self,
        dataset_id: int,
        annotation_id: int,
        category_id: int | None = None,
        polygon: list[float] | None = None,
    ) -> dict[str, Any]:
        """Update category, geometry, or both for a rotated annotation.

        Args:
            dataset_id: Active owning dataset identifier.
            annotation_id: Rotated annotation identifier.
            category_id: Optional replacement active category.
            polygon: Optional replacement normalized polygon.

        Returns:
            The updated record with submitted, stored, and correction metadata.

        Raises:
            DomainError: If no change is supplied or any referenced record or
                geometry is invalid.
            sqlite3.Error: If the update fails.

        Notes:
            The annotation type cannot be changed by this operation.
        """
        if category_id is None and polygon is None:
            raise DomainError(ErrorCode.INVALID_ARGUMENT, "category_id or polygon is required")
        with self.database.transaction() as connection:
            self.repository.active_dataset(connection, dataset_id)
            existing = self.repository.annotation(
                connection, dataset_id, annotation_id, AnnotationType.ROTATED_BBOX.value
            )
            final_category = existing["category_id"] if category_id is None else category_id
            self.repository.active_category(connection, dataset_id, final_category)
            # Preserve stored geometry unless replacement geometry was supplied.
            if polygon is None:
                stored = json.loads(existing["geometry_json"])
                submitted = stored
                corrected = False
                deviation = 0.0
                warning = None
            else:
                geometry = validate_rotated_bbox(
                    polygon,
                    correction_enabled=self.settings.rotated_correction_enabled,
                    correction_threshold=self.settings.rotated_correction_threshold,
                    error_threshold=self.settings.rotated_error_threshold,
                )
                stored = geometry.stored_geometry
                submitted = geometry.submitted_geometry
                corrected = geometry.corrected
                deviation = geometry.deviation
                warning = geometry.warning
            connection.execute(
                "UPDATE annotations SET category_id = ?, geometry_json = ?, updated_at = ? WHERE id = ?",
                (final_category, json.dumps(stored), now(), annotation_id),
            )
            record = self.repository.annotation_dict(
                self.repository.annotation(connection, dataset_id, annotation_id, AnnotationType.ROTATED_BBOX.value)
            )
            record.update(
                {
                    "submitted_geometry": submitted,
                    "stored_geometry": stored,
                    "corrected": corrected,
                    "deviation": deviation,
                    "warning": warning,
                }
            )
            return record

    def delete_annotations(
        self,
        dataset_id: int,
        annotation_ids: list[int],
        annotation_type: AnnotationType,
    ) -> dict[str, Any]:
        """Hard-delete a same-type annotation batch atomically.

        Args:
            dataset_id: Active owning dataset identifier.
            annotation_ids: Non-empty identifiers to delete.
            annotation_type: Required type of every target annotation.

        Returns:
            Deleted identifiers and their count.

        Raises:
            DomainError: If input is empty or any dataset, annotation, or type
                constraint does not match.
            sqlite3.Error: If deletion fails.

        Notes:
            Every identifier is validated before the single DELETE statement.
        """
        if not annotation_ids:
            raise DomainError(ErrorCode.INVALID_ARGUMENT, "annotation_ids must not be empty", field="annotation_ids")
        with self.database.transaction() as connection:
            self.repository.active_dataset(connection, dataset_id)
            # Validate the complete batch before constructing the parameter list.
            for annotation_id in annotation_ids:
                self.repository.annotation(connection, dataset_id, annotation_id, annotation_type.value)
            placeholders = ",".join("?" for _ in annotation_ids)
            connection.execute(
                f"DELETE FROM annotations WHERE dataset_id = ? AND type = ? AND id IN ({placeholders})",  # noqa: S608
                (dataset_id, annotation_type.value, *annotation_ids),
            )
            return {"deleted_annotation_ids": annotation_ids, "count": len(annotation_ids)}

    def list_annotations(
        self,
        dataset_id: int,
        image_path: str | None = None,
        annotation_type: str | None = None,
        category_ids: list[int] | None = None,
        annotation_ids: list[int] | None = None,
        include_deleted_categories: bool = False,
        offset: int = 0,
        max_results: int = 100,
    ) -> dict[str, Any]:
        """Filter and page annotations with category metadata.

        Args:
            dataset_id: Owning dataset identifier.
            image_path: Optional dataset-relative image filter.
            annotation_type: Optional geometry type filter or ``all``.
            category_ids: Optional category identifier filter.
            annotation_ids: Optional annotation identifier filter.
            include_deleted_categories: Whether annotations whose category is
                deleted are included.
            offset: Zero-based result offset.
            max_results: Positive page size.

        Returns:
            Decoded annotation records, total count, and page metadata.

        Raises:
            DomainError: If filters, pagination, dataset, or image are invalid.
            sqlite3.Error: If the query fails.

        Notes:
            Dynamic SQL contains only generated placeholders and fixed column
            names; caller values are always bound parameters.
        """
        if annotation_type not in {None, "all", AnnotationType.BBOX.value, AnnotationType.ROTATED_BBOX.value}:
            raise DomainError(ErrorCode.INVALID_ARGUMENT, "invalid annotation_type", field="annotation_type")
        if offset < 0 or max_results <= 0:
            raise DomainError(ErrorCode.INVALID_ARGUMENT, "offset must be non-negative and max_results positive")
        # Build a parameterized filter shared by the count and page queries.
        clauses = ["a.dataset_id = ?"]
        parameters: list[Any] = [dataset_id]
        with self.database.connect() as connection:
            root = self._dataset_root(connection, dataset_id)
            if image_path is not None:
                relative, _ = resolve_image(root, image_path)
                clauses.append("a.image_path = ?")
                parameters.append(relative)
            if annotation_type not in {None, "all"}:
                clauses.append("a.type = ?")
                parameters.append(annotation_type)
            for values, column in ((category_ids, "a.category_id"), (annotation_ids, "a.id")):
                if values:
                    clauses.append(f"{column} IN ({','.join('?' for _ in values)})")
                    parameters.extend(values)
            if not include_deleted_categories:
                clauses.append("c.deleted_at IS NULL")
            where = " AND ".join(clauses)
            # Count before pagination, then decode geometry for the selected page.
            total = connection.execute(
                f"SELECT COUNT(*) FROM annotations a JOIN categories c ON c.id = a.category_id WHERE {where}",  # noqa: S608
                parameters,
            ).fetchone()[0]
            select_query = (
                "SELECT a.*, c.name AS category_name, c.deleted_at AS category_deleted_at "  # noqa: S608
                f"FROM annotations a JOIN categories c ON c.id = a.category_id WHERE {where} "
                "ORDER BY a.id LIMIT ? OFFSET ?"
            )
            rows = connection.execute(
                select_query,
                (*parameters, max_results, offset),
            )
            annotations = []
            for row in rows:
                record = row_dict(row)
                record["geometry"] = json.loads(record.pop("geometry_json"))
                annotations.append(record)
        return {"annotations": annotations, "total": total, "offset": offset, "count": len(annotations)}

    def preview_image(
        self,
        dataset_id: int,
        image_path: str,
        max_width: int | None = None,
        max_height: int | None = None,
        allow_upscale: bool = False,
    ) -> tuple[bytes, dict[str, Any]]:
        """Create an orientation-corrected preview of one image.

        Args:
            dataset_id: Owning dataset identifier.
            image_path: Dataset-relative source image path.
            max_width: Optional requested width limit.
            max_height: Optional requested height limit.
            allow_upscale: Whether a small image may be enlarged.

        Returns:
            In-memory PNG bytes and structured preview metadata.

        Raises:
            DomainError: If dimensions, dataset, image path, or decoding are invalid.

        Notes:
            Requested dimensions are clamped to server limits. No file is written.
        """
        requested_width = self.settings.preview_max_width if max_width is None else max_width
        requested_height = self.settings.preview_max_height if max_height is None else max_height
        if requested_width <= 0 or requested_height <= 0:
            raise DomainError(ErrorCode.INVALID_ARGUMENT, "preview dimensions must be positive")
        actual_width = min(requested_width, self.settings.preview_max_width)
        actual_height = min(requested_height, self.settings.preview_max_height)
        with self.database.connect() as connection:
            root = self._dataset_root(connection, dataset_id)
            relative, absolute = resolve_image(root, image_path)
        data, metadata = render_preview(
            absolute,
            maximum_width=actual_width,
            maximum_height=actual_height,
            allow_upscale=allow_upscale,
        )
        metadata.update(
            {
                "dataset_id": dataset_id,
                "image_path": relative,
                "clamped": requested_width != actual_width or requested_height != actual_height,
            }
        )
        return data, metadata

    def preview_annotations(
        self,
        dataset_id: int,
        image_path: str,
        annotation_type: str = "all",
        annotation_ids: list[int] | None = None,
        include_deleted_categories: bool = False,
        max_width: int | None = None,
        max_height: int | None = None,
    ) -> tuple[bytes, dict[str, Any]]:
        """Create an image preview with selected annotations overlaid.

        Args:
            dataset_id: Owning dataset identifier.
            image_path: Dataset-relative source image path.
            annotation_type: Geometry type filter or ``all``.
            annotation_ids: Optional annotation identifiers to render.
            include_deleted_categories: Whether deleted-category annotations render.
            max_width: Optional requested width limit.
            max_height: Optional requested height limit.

        Returns:
            In-memory PNG bytes and preview and annotation metadata.

        Raises:
            DomainError: If filters, dimensions, records, path, or decoding are
                invalid.

        Notes:
            Annotation previews never upscale and never modify the source image.
        """
        # Resolve the exact annotation set before opening the source image.
        listed = self.list_annotations(
            dataset_id,
            image_path=image_path,
            annotation_type=annotation_type,
            annotation_ids=annotation_ids,
            include_deleted_categories=include_deleted_categories,
            max_results=10_000,
        )
        requested_width = self.settings.preview_max_width if max_width is None else max_width
        requested_height = self.settings.preview_max_height if max_height is None else max_height
        if requested_width <= 0 or requested_height <= 0:
            raise DomainError(ErrorCode.INVALID_ARGUMENT, "preview dimensions must be positive")
        actual_width = min(requested_width, self.settings.preview_max_width)
        actual_height = min(requested_height, self.settings.preview_max_height)
        with self.database.connect() as connection:
            root = self._dataset_root(connection, dataset_id)
            relative, absolute = resolve_image(root, image_path)
        data, metadata = render_preview(
            absolute,
            maximum_width=actual_width,
            maximum_height=actual_height,
            allow_upscale=False,
            annotations=listed["annotations"],
        )
        metadata.update(
            {
                "dataset_id": dataset_id,
                "image_path": relative,
                "annotation_count": listed["count"],
                "clamped": requested_width != actual_width or requested_height != actual_height,
            }
        )
        return data, metadata

    def export_metadata_jsonl(
        self,
        dataset_id: int,
        output_path: str,
        export_mode: ExportMode = ExportMode.AUTOTRAIN,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Export completed-image annotations to authorized metadata JSONL.

        Args:
            dataset_id: Active dataset identifier to export.
            output_path: Destination file path.
            export_mode: AutoTrain-compatible or extended layout.
            overwrite: Whether an existing destination may be replaced.

        Returns:
            Export counts, mapping, exclusions, and destination metadata.

        Raises:
            DomainError: If the dataset, destination, image, or export preflight is
                invalid or another writer holds the destination lock.
            OSError: If output cannot be written atomically.
            sqlite3.Error: If export state cannot be read.

        Notes:
            Only images marked completed are exported; source images stay immutable.
        """
        output = resolve_output(output_path, self.settings.allowed_export_roots)
        # Snapshot the completed images, active categories, and annotations.
        with self.database.connect() as connection:
            root = self._dataset_root(connection, dataset_id, active=True)
            completed = [
                row["image_path"]
                for row in connection.execute(
                    "SELECT image_path FROM image_states WHERE dataset_id = ? AND status = 'completed' "
                    "ORDER BY image_path",
                    (dataset_id,),
                )
            ]
            categories = [
                row_dict(row)
                for row in connection.execute(
                    "SELECT * FROM categories WHERE dataset_id = ? AND deleted_at IS NULL ORDER BY id",
                    (dataset_id,),
                )
            ]
            annotations = [
                self.repository.annotation_dict(row)
                for row in connection.execute(
                    "SELECT * FROM annotations WHERE dataset_id = ? ORDER BY id",
                    (dataset_id,),
                )
            ]
        return export_metadata(
            root=root,
            output_path=output,
            mode=export_mode,
            overwrite=overwrite,
            completed_images=completed,
            categories=categories,
            annotations=annotations,
        )
