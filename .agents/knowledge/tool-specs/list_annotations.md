# `list_annotations`

## Purpose

List stored annotations for review or before making a corrective write.

## Interface

| Parameter | Type | Required | Default | Definition |
| --- | --- | --- | --- | --- |
| `dataset_id` | integer | Yes | — | Owning dataset identifier. |
| `image_path` | string or null | No | `null` | Optional dataset-relative image filter. |
| `annotation_type` | string or null | No | `null` | Optional `bbox`, `rotated_bbox`, or `all` filter. |
| `category_ids` | integer array or null | No | `null` | Optional category IDs to include. |
| `annotation_ids` | integer array or null | No | `null` | Optional annotation IDs to include. |
| `include_deleted_categories` | boolean | No | `false` | Include annotations with deleted categories. |
| `offset` | integer | No | `0` | Zero-based page offset. |
| `max_results` | integer | No | `100` | Positive page size. |

## Preconditions

The dataset must exist. If supplied, the image path, filters, and pagination must be valid.

## Behavior and invariants

Returns visible annotations ordered by stable annotation ID. Listing includes category
name and deletion metadata; no annotation state changes.

## Output

`data` contains `annotations`, `total`, `offset`, and `count`. Each annotation adds
`category_name` and `category_deleted_at` to the shared `AnnotationRecord` shape.

## Business errors

- `DATASET_NOT_FOUND` or `IMAGE_NOT_FOUND`.
- `PATH_OUTSIDE_DATASET_ROOT`: an image filter escapes the dataset.
- `INVALID_ARGUMENT`: invalid type filter, IDs, offset, or page size.

## Example

```json
{ "dataset_id": 17, "image_path": "camera/0001.jpg", "max_results": 100 }
```

## Acceptance criteria

- Filters, deleted-category visibility, pagination, and ID ordering are observable in results.
- Invalid filters or an invalid image path fail without changing annotation state.
