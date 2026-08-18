"""Forward-only SQLite schema migrations."""

import sqlite3

MIGRATIONS: tuple[str, ...] = (
    """
    CREATE TABLE datasets (
        id INTEGER PRIMARY KEY,
        name TEXT,
        root_path TEXT NOT NULL,
        deleted_at TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE TABLE categories (
        id INTEGER PRIMARY KEY,
        dataset_id INTEGER NOT NULL REFERENCES datasets(id),
        name TEXT NOT NULL,
        description TEXT,
        deleted_at TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE UNIQUE INDEX categories_active_name
        ON categories(dataset_id, name) WHERE deleted_at IS NULL;
    CREATE TABLE image_states (
        dataset_id INTEGER NOT NULL REFERENCES datasets(id),
        image_path TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('unannotated', 'in_progress', 'completed')),
        updated_at TEXT NOT NULL,
        PRIMARY KEY(dataset_id, image_path)
    );
    CREATE TABLE annotations (
        id INTEGER PRIMARY KEY,
        dataset_id INTEGER NOT NULL REFERENCES datasets(id),
        image_path TEXT NOT NULL,
        type TEXT NOT NULL CHECK(type IN ('bbox', 'rotated_bbox')),
        category_id INTEGER NOT NULL REFERENCES categories(id),
        geometry_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE INDEX annotations_dataset_image ON annotations(dataset_id, image_path);
    CREATE INDEX annotations_category ON annotations(category_id);
    """,
)


def migrate(connection: sqlite3.Connection) -> None:
    connection.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    applied = {row[0] for row in connection.execute("SELECT version FROM schema_migrations")}
    for version, script in enumerate(MIGRATIONS, start=1):
        if version in applied:
            continue
        connection.executescript(script)
        connection.execute(
            "INSERT INTO schema_migrations(version, applied_at) VALUES (?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))",
            (version,),
        )
    connection.commit()
