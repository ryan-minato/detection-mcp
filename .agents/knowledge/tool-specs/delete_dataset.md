# `delete_dataset`

## Purpose

Soft-delete a registered dataset when its annotation state should no longer be active.

## Interface

| Parameter | Type | Required | Default | Definition |
| --- | --- | --- | --- | --- |
| `dataset_id` | integer | Yes | — | Registered dataset identifier. |

## Preconditions

The dataset must exist. It may already be deleted.

## Behavior and invariants

Sets deletion state while retaining the dataset, categories, annotations, and stable
IDs. The operation is idempotent and never changes source images.

## Output

`data` is the deleted `DatasetRecord`; `deleted_at` is populated.

## Business errors

- `DATASET_NOT_FOUND`: no dataset has the supplied ID.
- `STORAGE_ERROR`: deletion state cannot be stored.

## Example

```json
{ "dataset_id": 17 }
```

## Acceptance criteria

- Deleting an active dataset hides it from default listing and preserves its state.
- Repeating deletion succeeds with a deleted record; an unknown ID returns `DATASET_NOT_FOUND`.
