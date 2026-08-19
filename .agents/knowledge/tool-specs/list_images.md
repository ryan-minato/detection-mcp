# `list_images`

## Purpose

Discover images in a dataset and select an annotation work queue without changing files.

## Interface

| Parameter | Type | Required | Default | Definition |
| --- | --- | --- | --- | --- |
| `dataset_id` | integer | Yes | — | Dataset identifier to scan. |
| `status` | string | No | `all` | `all`, `unannotated`, `in_progress`, or `completed`. |
| `order_by` | string | No | `name` | Stable `name` order or deterministic `random` order. |
| `random_seed` | integer or null | No | `null` | Optional seed for random ordering. |
| `offset` | integer | No | `0` | Zero-based page offset. |
| `max_results` | integer | No | `100` | Positive page size. |

## Preconditions

The dataset and its root must be available. Filters and pagination must be valid.

## Behavior and invariants

Image discovery is read-only. Untracked discoverable images have `unannotated`
status. Random order is deterministic for the selected seed.

## Output

`data` contains `images` with `image_path` and `status`, plus `total`, `offset`,
`count`, and the effective `random_seed`.

## Business errors

- `DATASET_NOT_FOUND` or `IMAGE_ROOT_UNAVAILABLE`.
- `INVALID_ARGUMENT`: invalid filter, order, offset, or page size.

## Example

```json
{ "dataset_id": 17, "status": "unannotated", "order_by": "name", "max_results": 50 }
```

## Acceptance criteria

- Results honor status, ordering, and pagination while leaving source images unchanged.
- Invalid filter or pagination input returns `INVALID_ARGUMENT`.
