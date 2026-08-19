# `get_category`

## Purpose

Retrieve one category and its authoritative description, including deleted state.

## Interface

| Parameter | Type | Required | Default | Definition |
| --- | --- | --- | --- | --- |
| `dataset_id` | integer | Yes | — | Owning dataset identifier. |
| `category_id` | integer | Yes | — | Category identifier in that dataset. |

## Preconditions

The dataset and category must exist; neither must be active for this direct lookup.

## Behavior and invariants

Performs a read-only lookup and returns actual deletion state.

## Output

`data` is the matching `CategoryRecord`.

## Business errors

- `DATASET_NOT_FOUND`: the owner does not exist.
- `CATEGORY_NOT_FOUND`: the category is absent or belongs to another dataset.

## Example

```json
{ "dataset_id": 17, "category_id": 4 }
```

## Acceptance criteria

- Both active and deleted categories are retrievable with their stored description.
- Cross-dataset or unknown IDs return `CATEGORY_NOT_FOUND`.
