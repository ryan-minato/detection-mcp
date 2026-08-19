# `export_metadata_jsonl`

## Purpose

Preflight completed images and atomically export training metadata as JSONL.

## Interface

| Parameter | Type | Required | Default | Definition |
| --- | --- | --- | --- | --- |
| `dataset_id` | integer | Yes | — | Active dataset identifier to export. |
| `output_path` | string | Yes | — | Destination file within an allowed export root. |
| `export_mode` | enum | No | `autotrain` | `autotrain` or `extended` output layout. |
| `overwrite` | boolean | No | `false` | Allow atomic replacement of an existing destination. |

## Preconditions

The dataset must be active; every completed image must pass export preflight; the
destination must be authorized. Existing output requires `overwrite: true`.

## Behavior and invariants

Exports only images with status `completed`. It writes a temporary output and
atomically replaces the destination while holding an exclusive lock. `autotrain`
requires its compatible flat-image subset; `extended` supports rotated boxes and
portable nested paths. Source images remain unchanged.

## Output

`data` contains `output_path`, `export_mode`, `exported_images`, string-keyed
`category_mapping`, `ignored_rotated_annotations`, and
`excluded_deleted_category_annotations`.

## Business errors

- `DATASET_NOT_FOUND` or `DATASET_DELETED`.
- `OUTPUT_PATH_NOT_ALLOWED` or `OUTPUT_ALREADY_EXISTS`.
- `AUTOTRAIN_LAYOUT_INCOMPATIBLE`: completed data cannot use the selected AutoTrain layout.
- `EXPORT_VALIDATION_FAILED`: completed images or annotations fail preflight.
- `IMAGE_ROOT_UNAVAILABLE`, `IMAGE_NOT_FOUND`, `STORAGE_ERROR`, or `TRANSACTION_FAILED`.

## Example

```json
{ "dataset_id": 17, "output_path": "/output/metadata.jsonl", "export_mode": "extended", "overwrite": true }
```

## Acceptance criteria

- Only completed images are represented after a successful preflighted export.
- Existing output is preserved unless explicit overwrite is allowed; a successful replacement is atomic.
- Incompatible layout or invalid completed data fails without publishing a partial destination.
