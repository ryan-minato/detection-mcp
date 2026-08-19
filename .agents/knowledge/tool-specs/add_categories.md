# `add_categories`

## Purpose

Create one or more categories for an active dataset in a single transaction.

## Interface

| Parameter | Type | Required | Default | Definition |
| --- | --- | --- | --- | --- |
| `dataset_id` | integer | Yes | — | Active owning dataset identifier. |
| `categories` | array | Yes | — | Non-empty category requests with `name` (trimmed, 1–255 chars) and optional `description`. |

## Preconditions

The dataset must be active. Every submitted name must be unique among active
categories and unknown request fields are rejected.

## Behavior and invariants

Validates the full batch before insertion. A single invalid or conflicting category
rolls back the entire batch.

## Output

`data` contains `categories` (created `CategoryRecord` values in request order) and
`count`.

## Business errors

- `DATASET_NOT_FOUND` or `DATASET_DELETED`: the owner is unavailable.
- `CATEGORY_NAME_CONFLICT`: an active name conflicts.
- `INVALID_ARGUMENT`: the batch or category input is invalid.
- `TRANSACTION_FAILED`: the batch could not be committed.

## Example

```json
{ "dataset_id": 17, "categories": [{ "name": "car" }, { "name": "person", "description": "Pedestrian" }] }
```

## Acceptance criteria

- A valid batch creates all categories and reports the matching count.
- An invalid or conflicting entry creates none of the batch.
