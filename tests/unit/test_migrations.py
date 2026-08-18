import sqlite3

import pytest

from detection_mcp.db import migrations

pytestmark = pytest.mark.unit


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def test_migration_failure_rolls_back_schema_and_version(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        migrations,
        "MIGRATIONS",
        (
            "CREATE TABLE first_table (id INTEGER PRIMARY KEY);",
            "CREATE TABLE partial_table (id INTEGER PRIMARY KEY); INVALID SQL;",
        ),
    )
    connection = _connection()

    with pytest.raises(sqlite3.Error):
        migrations.migrate(connection)

    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")}
    versions = [row[0] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version")]
    assert "first_table" in tables
    assert "partial_table" not in tables
    assert versions == [1]


def test_annotation_migration_preserves_rows_and_prevents_id_reuse() -> None:
    connection = _connection()
    connection.execute("CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
    connection.executescript(migrations.MIGRATIONS[0])
    connection.execute("INSERT INTO schema_migrations VALUES (1, '2026-01-01T00:00:00Z')")
    connection.execute("INSERT INTO datasets VALUES (1, 'sample', '/datasets', NULL, 'created', 'updated')")
    connection.execute("INSERT INTO categories VALUES (1, 1, 'vehicle', NULL, NULL, 'created', 'updated')")
    for annotation_id in (1, 2):
        connection.execute(
            "INSERT INTO annotations VALUES (?, 1, 'image.png', 'bbox', 1, '[0,0,1,1]', 'created', 'updated')",
            (annotation_id,),
        )
    connection.commit()

    migrations.migrate(connection)
    connection.execute("DELETE FROM annotations WHERE id = 2")
    cursor = connection.execute(
        "INSERT INTO annotations(dataset_id, image_path, type, category_id, geometry_json, created_at, updated_at) "
        "VALUES (1, 'image.png', 'bbox', 1, '[0,0,1,1]', 'created', 'updated')"
    )

    assert cursor.lastrowid == 3
    assert connection.execute("SELECT COUNT(*) FROM annotations").fetchone()[0] == 2
    assert [row[0] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version")] == [1, 2]
