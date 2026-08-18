# Architecture

Read this file before changing module boundaries, dependency direction, storage,
filesystem access, geometry, preview rendering, or export behavior.

## Dependency Direction

```text
CLI / FastMCP server
        ↓
MCP tool adapters and public models
        ↓
domain services
        ↓
SQLite repositories and read-only image filesystem
```

Dependencies point downward. Tool adapters translate protocol models and domain
errors; they do not contain SQL or duplicate validation. Repositories do not know
about FastMCP.

## Package Areas

- `config.py`, `cli.py`, and `server.py`: process configuration and STDIO startup.
- `models.py` and `errors.py`: stable public schemas and business error codes.
- `server.py`: the 23 thin protocol adapters, grouped by product area.
- `services/`: dataset, category, image, annotation, geometry, preview, and export
  rules.
- `db/`: connection policy, numbered forward migrations, and repositories.

## Invariants

- SQLite foreign keys are enabled on every connection. Multi-item writes use one
  transaction and roll back on any invalid item.
- Stored image paths are portable dataset-relative POSIX paths. Canonical absolute
  dataset paths stay in the dataset registry only.
- Image decoding, dimensions, annotations, previews, and exports all use the
  orientation-corrected visual image.
- Dataset and category deletion is soft. Annotation deletion is hard. Stable IDs
  are never reused.
- Source images are opened read-only. Temporary output is written only under the
  state directory, system temporary storage, or an allowed export directory.
