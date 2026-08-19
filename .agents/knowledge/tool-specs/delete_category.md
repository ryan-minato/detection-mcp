# `delete_category`

## Purpose

Soft-delete an active category while retaining annotations that reference it.

## Interface

| Parameter | Type | Required | Default | Definition |
| --- | --- | --- | --- | --- |
| `dataset_id` | integer | Yes | — | Active owning dataset identifier. |
| `category_id` | integer | Yes | — | Category identifier to delete. |

## Preconditions

The dataset and category must exist; the category may already be deleted.

## Behavior and invariants

Sets category deletion state without deleting historical annotations or changing
source images. Repeated deletion is idempotent.

## Output

`data` is the deleted `CategoryRecord` with populated `deleted_at`.

## Business errors

- `DATASET_NOT_FOUND` or `DATASET_DELETED`: the owner is unavailable.
- `CATEGORY_NOT_FOUND`: the category is absent or belongs to another dataset.

## Example

```json
{ "dataset_id": 17, "category_id": 4 }
```

## Acceptance criteria

- Deletion hides the category from default listing but preserves related annotations.
- Repeated deletion succeeds; an absent category returns `CATEGORY_NOT_FOUND`.
