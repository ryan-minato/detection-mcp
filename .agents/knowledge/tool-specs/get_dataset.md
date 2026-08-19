# `get_dataset`

## Purpose

Retrieve one dataset's metadata, including a soft-deleted registration.

## Interface

| Parameter | Type | Required | Default | Definition |
| --- | --- | --- | --- | --- |
| `dataset_id` | integer | Yes | — | Registered dataset identifier. |

## Preconditions

The dataset must exist; it need not be active.

## Behavior and invariants

Performs a read-only direct lookup and does not hide a deleted record.

## Output

`data` is the matching `DatasetRecord`, including its actual `deleted_at` value.

## Business errors

- `DATASET_NOT_FOUND`: no dataset has the supplied ID.
- `STORAGE_ERROR`: dataset state cannot be read.

## Example

```json
{ "dataset_id": 17 }
```

## Acceptance criteria

- Active and deleted datasets are both retrievable by ID.
- An unknown ID returns `DATASET_NOT_FOUND`.
