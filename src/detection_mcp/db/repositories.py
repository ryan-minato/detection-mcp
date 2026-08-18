"""Repository operations shared by domain services."""

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any

from detection_mcp.errors import DomainError, ErrorCode


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def row_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def inserted_id(cursor: sqlite3.Cursor) -> int:
    if cursor.lastrowid is None:
        raise RuntimeError("an INSERT statement did not return a row id")
    return cursor.lastrowid


class Repository:
    @staticmethod
    def dataset(connection: sqlite3.Connection, dataset_id: int) -> sqlite3.Row:
        row = connection.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
        if row is None:
            raise DomainError(ErrorCode.DATASET_NOT_FOUND, f"dataset {dataset_id} was not found")
        return row

    @classmethod
    def active_dataset(cls, connection: sqlite3.Connection, dataset_id: int) -> sqlite3.Row:
        row = cls.dataset(connection, dataset_id)
        if row["deleted_at"] is not None:
            raise DomainError(ErrorCode.DATASET_DELETED, f"dataset {dataset_id} is deleted")
        return row

    @staticmethod
    def category(connection: sqlite3.Connection, dataset_id: int, category_id: int) -> sqlite3.Row:
        row = connection.execute(
            "SELECT * FROM categories WHERE id = ? AND dataset_id = ?",
            (category_id, dataset_id),
        ).fetchone()
        if row is None:
            raise DomainError(ErrorCode.CATEGORY_NOT_FOUND, f"category {category_id} was not found")
        return row

    @classmethod
    def active_category(cls, connection: sqlite3.Connection, dataset_id: int, category_id: int) -> sqlite3.Row:
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
        result = row_dict(row)
        result["geometry"] = json.loads(result.pop("geometry_json"))
        return result
