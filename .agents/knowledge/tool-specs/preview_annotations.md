# `preview_annotations`

## Purpose

Render an in-memory PNG overlay for selected annotations so annotation work can be reviewed.

## Interface

| Parameter | Type | Required | Default | Definition |
| --- | --- | --- | --- | --- |
| `dataset_id` | integer | Yes | — | Owning dataset identifier. |
| `image_path` | string | Yes | — | Portable dataset-relative image path. |
| `annotation_type` | string | No | `all` | `all`, `bbox`, or `rotated_bbox`. |
| `annotation_ids` | integer array or null | No | `null` | Optional annotation IDs to render. |
| `include_deleted_categories` | boolean | No | `false` | Include annotations whose category is deleted. |
| `max_width` | integer or null | No | `null` | Optional positive width limit. |
| `max_height` | integer or null | No | `null` | Optional positive height limit. |
| `show_grid` | boolean | No | `true` | Overlay a semi-transparent grid: 5 major cells per axis, each with 5 minor intervals and marked intersections. |

## Preconditions

The dataset and image must be available. Filters, IDs, and dimensions must be valid.

## Behavior and invariants

Renders only selected annotations in orientation-corrected image space. The preview
never upscales and never changes source files or annotations. Unless disabled, a
white semi-transparent grid divides each axis into five major cells and each major
cell into five minor divisions, with grid intersections marked for position
counting. Annotations are drawn above the grid.

## Output

The MCP content contains an overlay PNG and a success envelope. `data` contains all
preview metadata plus `annotation_count`.

## Business errors

- `DATASET_NOT_FOUND`, `IMAGE_NOT_FOUND`, `PATH_OUTSIDE_DATASET_ROOT`, or `ANNOTATION_NOT_FOUND`.
- `UNSUPPORTED_IMAGE_FORMAT` or `IMAGE_DECODE_FAILED`.
- `INVALID_ARGUMENT`: invalid type filter, IDs, or dimensions.

## Example

```json
{ "dataset_id": 17, "image_path": "camera/0001.jpg", "annotation_type": "bbox", "show_grid": true }
```

## Acceptance criteria

- The overlay and count reflect the selected visible annotations.
- The positioning grid is enabled by default and can be disabled without changing preview metadata.
- Deleted-category annotations remain hidden by default and source images remain unchanged.
