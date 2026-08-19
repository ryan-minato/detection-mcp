# `delete_rotated_bbox_annotation`

## Purpose

Hard-delete one or more rotated bounding-box annotations atomically.

## Interface

| Parameter | Type | Required | Default | Definition |
| --- | --- | --- | --- | --- |
| `dataset_id` | integer | Yes | — | Active owning dataset identifier. |
| `annotation_ids` | integer array | Yes | — | Non-empty IDs of `rotated_bbox` annotations in the dataset. |

## Preconditions

The dataset must be active and every ID must identify an existing matching rotated annotation.

## Behavior and invariants

Validates all IDs before any removal. Deletion is hard, atomic, and does not reuse IDs.

## Output

`data` contains `deleted_annotation_ids` and `count`.

## Business errors

- `DATASET_NOT_FOUND`, `DATASET_DELETED`, or `ANNOTATION_NOT_FOUND`.
- `INVALID_ARGUMENT`: empty input or an ID with the wrong annotation type.
- `TRANSACTION_FAILED`: the complete delete cannot be committed.

## Example

```json
{ "dataset_id": 17, "annotation_ids": [32, 33] }
```

## Acceptance criteria

- A valid request removes all selected rotated annotations and returns their IDs/count.
- An unknown or `bbox` ID causes the complete request to leave records intact.
