# `list_datasets`

## Purpose

List registered datasets to select or inspect annotation state.

## Interface

| Parameter | Type | Required | Default | Definition |
| --- | --- | --- | --- | --- |
| `include_deleted` | boolean | No | `false` | Include soft-deleted datasets. |

## Preconditions

No dataset must exist; an empty result is valid.

## Behavior and invariants

Returns records ordered by stable dataset ID. Listing is read-only and excludes
deleted records unless explicitly requested.

## Output

`data` contains `datasets` (ordered `DatasetRecord` values) and `count`.

## Business errors

- `STORAGE_ERROR`: dataset state cannot be read.

## Example

```json
{ "include_deleted": false }
```

## Acceptance criteria

- Default results contain only active datasets in ID order.
- `include_deleted: true` includes soft-deleted records and returns an accurate count.
