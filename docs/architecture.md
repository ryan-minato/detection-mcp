# Architecture

`detection-mcp` is a local STDIO server with a deliberately narrow ownership boundary: it owns SQLite annotation state and export files, but never source images.

```text
MCP client
    ↓ STDIO
FastMCP adapters (`server.py`)
    ↓ typed calls and stable errors
Application service (`services/application.py`)
    ├── geometry, preview, path, and export services
    └── SQLite repositories and migrations
            ↓
      state database       read-only source images
```

## Boundaries

- `cli.py` resolves CLI and environment configuration, sends logs to stderr, and starts STDIO.
- `server.py` registers exactly 23 thin tool adapters and converts domain failures to structured MCP errors.
- `services/application.py` owns transactions and operation orchestration.
- Focused services enforce canonical paths, image orientation, geometry, previews, and atomic export.
- `db/` owns connection settings, forward migrations, and SQL lookups.

SQLite foreign keys are enabled for every connection. Batch writes use one transaction. Dataset and category deletion is soft; annotation deletion is hard. IDs are never recycled.

Every stored image path is a portable, dataset-relative POSIX path. Filesystem boundaries are checked after path resolution, including symlink resolution. Preview and export use EXIF-corrected visual dimensions.
