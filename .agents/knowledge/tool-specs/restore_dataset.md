# `restore_dataset`

## Purpose

Restore a previously soft-deleted dataset registration.

## Interface

| Parameter | Type | Required | Default | Definition |
| --- | --- | --- | --- | --- |
| `dataset_id` | integer | Yes | — | Registered dataset identifier. |

## Preconditions

The dataset must exist. It may already be active.

## Behavior and invariants

Clears only dataset deletion state and preserves all related records and source files.

## Output

`data` is the active `DatasetRecord` with `deleted_at` set to `null`.

## Business errors

- `DATASET_NOT_FOUND`: no dataset has the supplied ID.
- `STORAGE_ERROR`: restoration cannot be stored.

## Example

```json
{ "dataset_id": 17 }
```

## Acceptance criteria

- A deleted dataset becomes active without changing its ID or associated state.
- Restoring an active dataset is safe; an unknown ID returns `DATASET_NOT_FOUND`.
