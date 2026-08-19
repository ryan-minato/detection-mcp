# Shared MCP Tool Contract

Read this file before using or changing any tool specification. It defines rules
shared by every MCP tool and prevents repeated, divergent statements in individual
specifications.

## Protocol responses

Successful tools return structured content shaped as `{ "ok": true, "data": ... }`.
Domain failures set the MCP result error flag and return an `error` object with a
stable `code`, a safe `message`, optional `field`, and `details`. Do not depend on
message text; branch on `code`.

`preview_image` and `preview_annotations` additionally return PNG image content.
Their structured response still uses the success envelope.

## Shared data shapes

- `DatasetRecord`: `dataset_id`, `name`, `root_path`, `deleted_at`, `created_at`,
  and `updated_at`.
- `CategoryRecord`: `category_id`, `dataset_id`, `name`, `description`,
  `deleted_at`, `created_at`, and `updated_at`.
- `AnnotationRecord`: `annotation_id`, `dataset_id`, `image_path`, `type`,
  `category_id`, `geometry`, `created_at`, and `updated_at`.
- `ImageStatus` values are `unannotated`, `in_progress`, and `completed`.
- `AnnotationType` values are `bbox` and `rotated_bbox`.
- `ExportMode` values are `autotrain` and `extended`.

Timestamps are strings. IDs are stable positive integers. Dataset-relative paths
are portable POSIX paths.

## Safety and state

Source images are immutable. Tools may read images, write SQLite annotation state,
or write an authorized export, but never modify, move, rename, or delete source
files. Every image path is resolved and contained within its dataset root after
symlink resolution.

Datasets and categories are soft-deleted. Annotation deletion is hard. Mutating
tools that accept a batch validate the complete batch and apply it atomically.
Active-dataset operations reject deleted datasets; explicitly addressed `get_*`
tools may return deleted records where their own specification permits it.

## Geometry and previews

Axis-aligned boxes are normalized `[x1, y1, x2, y2]`. Rotated boxes are normalized
four-point polygons flattened to eight coordinates. Geometry is evaluated in the
orientation-corrected visual image coordinate space.

Preview metadata reports orientation-corrected original dimensions, preview
dimensions, scale, dataset and image identity, and whether requested dimensions
were clamped. Annotation previews add `annotation_count`.

## Error codes

Possible business codes include dataset and category availability errors,
image/path/decode errors, invalid argument and geometry errors, annotation lookup
errors, output authorization and collision errors, export validation errors,
transaction failures, and storage/internal failures. Each tool specification lists
the codes relevant to its operation. Preserve existing stable error codes whenever
behavior changes.

## Specification authority

Use `src/detection_mcp/server.py` for registered names and adapter signatures,
`models.py` for public schemas, `errors.py` for error codes, and tests for observed
behavior. Update specifications with confirmed changes; do not invent behavior to
fill a documentation gap.
