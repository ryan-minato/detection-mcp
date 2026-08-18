# Export Format

`export_metadata_jsonl` exports only images whose status is `completed`. It writes to a temporary file, flushes it, and atomically replaces the destination while holding an exclusive lock file.

## AutoTrain mode

AutoTrain mode requires at least five completed images in a flat dataset root. Files must use `.jpg`, `.jpeg`, or `.png`. Each JSONL object contains `file_name` and `objects`; bbox values are pixel `[x, y, width, height]` coordinates and categories are zero-based export indices.

Rotated boxes are not representable in the AutoTrain bbox schema. They are counted in `ignored_rotated_annotations` and omitted. Images without annotations remain negative samples with empty arrays.

## Extended mode

Extended mode also emits `polygon` and `polygon_category` arrays. Each polygon is eight pixel coordinates in canonical point order. Nested portable image paths and WebP images are allowed.

Deleted-category annotations are excluded and reported. Existing output is rejected unless `overwrite=true`; a concurrent lock is also reported as an existing-output error.
