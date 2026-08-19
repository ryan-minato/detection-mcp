# `list_categories`

## Purpose

List categories belonging to a dataset before assigning labels or reviewing state.

## Interface

| Parameter | Type | Required | Default | Definition |
| --- | --- | --- | --- | --- |
| `dataset_id` | integer | Yes | — | Owning dataset identifier. |
| `include_deleted` | boolean | No | `false` | Include soft-deleted categories. |

## Preconditions

The dataset must exist. It may be deleted for this read-only lookup.

## Behavior and invariants

Returns records ordered by stable category ID. Deleted categories are excluded unless
requested explicitly.

## Output

`data` contains ordered `categories` (`CategoryRecord` values) and `count`.

## Business errors

- `DATASET_NOT_FOUND`: the owner does not exist.
- `STORAGE_ERROR`: category state cannot be read.

## Example

```json
{ "dataset_id": 17, "include_deleted": false }
```

## Acceptance criteria

- Default results contain only active categories in ID order.
- Including deleted categories changes only result visibility and count.
