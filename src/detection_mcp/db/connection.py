"""SQLite connection and transaction policy."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from detection_mcp.db.migrations import migrate


class Database:
    """Own SQLite connection setup and transaction boundaries.

    Args:
        path: Filesystem path of the SQLite database.

    Notes:
        Every connection enables foreign keys and a five-second busy timeout.
    """

    def __init__(self, path: Path) -> None:
        self.path = path

    def initialize(self) -> None:
        """Create the database directory and apply pending migrations.

        Returns:
            None.

        Raises:
            OSError: If the database directory cannot be created.
            sqlite3.Error: If SQLite initialization or migration fails.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            migrate(connection)

    def connect(self) -> sqlite3.Connection:
        """Open a configured SQLite connection.

        Returns:
            A connection whose rows support mapping-style access.

        Raises:
            sqlite3.Error: If SQLite cannot open or configure the database.
        """
        connection = sqlite3.connect(self.path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Provide a commit-or-rollback transaction context.

        Yields:
            An open connection with an explicit transaction in progress.

        Raises:
            Exception: Re-raises any operation failure after rolling back.

        Notes:
            The connection is always closed when the context exits.
        """
        connection = self.connect()
        try:
            connection.execute("BEGIN")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
