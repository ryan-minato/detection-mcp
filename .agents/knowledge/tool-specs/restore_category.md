# `restore_category`

## Purpose

Restore a soft-deleted category, optionally under a replacement name.

## Interface

| Parameter | Type | Required | Default | Definition |
| --- | --- | --- | --- | --- |
| `dataset_id` | integer | Yes | — | Active owning dataset identifier. |
| `category_id` | integer | Yes | — | Category identifier to restore. |
| `new_name` | string or null | No | `null` | Optional trimmed replacement name used on restore. |

## Preconditions

The dataset must be active and the category must exist. The final name must be
non-empty and unique among active categories.

## Behavior and invariants

Clears deletion state and retains the category ID, description, and historical
annotations. Omitting `new_name` reuses the stored name.

## Output

`data` is the active restored `CategoryRecord`.

## Business errors

- `DATASET_NOT_FOUND`, `DATASET_DELETED`, or `CATEGORY_NOT_FOUND`.
- `CATEGORY_NAME_CONFLICT`: the final name is already active.
- `INVALID_ARGUMENT`: the supplied replacement name is invalid.

## Example

```json
{ "dataset_id": 17, "category_id": 4, "new_name": "vehicle" }
```

## Acceptance criteria

- A deleted category is restored with the original or supplied valid name.
- A conflicting or empty final name leaves the category deleted.
