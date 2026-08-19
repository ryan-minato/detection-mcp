# `delete_bbox_annotation`

## Purpose

Hard-delete one or more axis-aligned annotations in a single transaction.

## Interface

| Parameter | Type | Required | Default | Definition |
| --- | --- | --- | --- | --- |
| `dataset_id` | integer | Yes | — | Active owning dataset identifier. |
| `annotation_ids` | integer array | Yes | — | Non-empty IDs of `bbox` annotations owned by the dataset. |

## Preconditions

The dataset must be active and every ID must identify an existing `bbox` annotation
in that dataset.

## Behavior and invariants

Validates all IDs before deletion. Deletion is hard and atomic; deleted annotation
IDs are never reused.

## Output

`data` contains `deleted_annotation_ids` and `count`.

## Business errors

- `DATASET_NOT_FOUND`, `DATASET_DELETED`, or `ANNOTATION_NOT_FOUND`.
- `INVALID_ARGUMENT`: empty input or an ID with the wrong annotation type.
- `TRANSACTION_FAILED`: the complete delete cannot be committed.

## Example

```json
{ "dataset_id": 17, "annotation_ids": [31, 32] }
```

## Acceptance criteria

- A valid request removes every listed `bbox` and reports the same IDs/count.
- An unknown or wrong-type ID deletes none of the supplied annotations.
