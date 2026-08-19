# `set_image_status`

## Purpose

Set the annotation workflow state of one dataset image.

## Interface

| Parameter | Type | Required | Default | Definition |
| --- | --- | --- | --- | --- |
| `dataset_id` | integer | Yes | — | Active owning dataset identifier. |
| `image_path` | string | Yes | — | Portable dataset-relative image path. |
| `status` | enum | Yes | — | `unannotated`, `in_progress`, or `completed`. |

## Preconditions

The dataset must be active and `image_path` must resolve to a supported image within
its root.

## Behavior and invariants

Updates only SQLite workflow state. It does not modify image pixels, metadata, or
filesystem paths.

## Output

`data` contains `dataset_id`, normalized `image_path`, `status`, and `updated_at`.

## Business errors

- `DATASET_NOT_FOUND` or `DATASET_DELETED`.
- `IMAGE_NOT_FOUND`, `PATH_OUTSIDE_DATASET_ROOT`, `UNSUPPORTED_IMAGE_FORMAT`, or `IMAGE_DECODE_FAILED`.
- `INVALID_ARGUMENT`: invalid status value.

## Example

```json
{ "dataset_id": 17, "image_path": "camera/0001.png", "status": "in_progress" }
```

## Acceptance criteria

- A valid image receives the requested persisted status.
- Invalid, escaping, or unavailable images fail without altering source files.
