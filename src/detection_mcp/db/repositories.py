"""Repository operations shared by domain services."""

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any

from detection_mcp.errors import DomainError, ErrorCode


def now() -> str:
    """Return the current UTC timestamp in the storage format."""
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def row_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a SQLite row into a JSON-compatible mapping."""
    return dict(row)


def inserted_id(cursor: sqlite3.Cursor) -> int:
    """Return the row identifier created by an INSERT statement.

    Args:
        cursor: Cursor returned by the completed INSERT statement.

    Returns:
        The generated integer row identifier.

    Raises:
        RuntimeError: If the statement did not produce a row identifier.
    """
    if cursor.lastrowid is None:
        raise RuntimeError("an INSERT statement did not return a row id")
    return cursor.lastrowid


class Repository:
    """Provide reusable SQLite lookups with stable not-found errors.

    Notes:
        Callers own connection and transaction lifetimes. Repository methods do
        not commit, roll back, or close connections.
    """

    @staticmethod
    def dataset(connection: sqlite3.Connection, dataset_id: int) -> sqlite3.Row:
        """Fetch a dataset regardless of deletion state.

        Args:
            connection: Open SQLite connection.
            dataset_id: Dataset identifier to fetch.

        Returns:
            The matching dataset row.

        Raises:
            DomainError: If the dataset does not exist.
        """
        row = connection.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
        if row is None:
            raise DomainError(ErrorCode.DATASET_NOT_FOUND, f"dataset {dataset_id} was not found")
        return row

    @classmethod
    def active_dataset(cls, connection: sqlite3.Connection, dataset_id: int) -> sqlite3.Row:
        """Fetch a dataset that has not been soft-deleted.

        Args:
            connection: Open SQLite connection.
            dataset_id: Dataset identifier to fetch.

        Returns:
            The matching active dataset row.

        Raises:
            DomainError: If the dataset is missing or deleted.
        """
        row = cls.dataset(connection, dataset_id)
        if row["deleted_at"] is not None:
            raise DomainError(ErrorCode.DATASET_DELETED, f"dataset {dataset_id} is deleted")
        return row

    @staticmethod
    def category(connection: sqlite3.Connection, dataset_id: int, category_id: int) -> sqlite3.Row:
        """Fetch a category belonging to a dataset.

        Args:
            connection: Open SQLite connection.
            dataset_id: Owning dataset identifier.
            category_id: Category identifier to fetch.

        Returns:
            The matching category row, including deleted categories.

        Raises:
            DomainError: If the category does not belong to the dataset.
        """
        row = connection.execute(
            "SELECT * FROM categories WHERE id = ? AND dataset_id = ?",
            (category_id, dataset_id),
        ).fetchone()
        if row is None:
            raise DomainError(ErrorCode.CATEGORY_NOT_FOUND, f"category {category_id} was not found")
        return row

    @classmethod
    def active_category(cls, connection: sqlite3.Connection, dataset_id: int, category_id: int) -> sqlite3.Row:
        """Fetch an active category belonging to a dataset.

        Args:
            connection: Open SQLite connection.
            dataset_id: Owning dataset identifier.
            category_id: Category identifier to fetch.

        Returns:
            The matching active category row.

        Raises:
            DomainError: If the category is missing or deleted.
        """
        row = cls.category(connection, dataset_id, category_id)
        if row["deleted_at"] is not None:
            raise DomainError(ErrorCode.CATEGORY_DELETED, f"category {category_id} is deleted")
        return row

    @staticmethod
    def annotation(
        connection: sqlite3.Connection,
        dataset_id: int,
        annotation_id: int,
        annotation_type: str | None = None,
    ) -> sqlite3.Row:
        """Fetch an annotation with an optional type constraint.

        Args:
            connection: Open SQLite connection.
            dataset_id: Owning dataset identifier.
            annotation_id: Annotation identifier to fetch.
            annotation_type: Optional required stored geometry type.

        Returns:
            The matching annotation row.

        Raises:
            DomainError: If no matching annotation exists.
        """
        query = "SELECT * FROM annotations WHERE id = ? AND dataset_id = ?"
        parameters: tuple[Any, ...] = (annotation_id, dataset_id)
        if annotation_type is not None:
            query += " AND type = ?"
            parameters += (annotation_type,)
        row = connection.execute(query, parameters).fetchone()
        if row is None:
            raise DomainError(
                ErrorCode.ANNOTATION_NOT_FOUND,
                f"annotation {annotation_id} was not found",
            )
        return row

    @staticmethod
    def annotation_dict(row: sqlite3.Row) -> dict[str, Any]:
        """Convert an annotation row and decode its geometry.

        Args:
            row: Annotation row containing ``geometry_json``.

        Returns:
            A JSON-compatible annotation mapping with a ``geometry`` list.

        Raises:
            json.JSONDecodeError: If persisted geometry is invalid JSON.
        """
        result = row_dict(row)
        result["geometry"] = json.loads(result.pop("geometry_json"))
        return result
