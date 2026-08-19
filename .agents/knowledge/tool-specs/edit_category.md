# `edit_category`

## Purpose

Change the name and/or authoritative description of an active category.

## Interface

| Parameter | Type | Required | Default | Definition |
| --- | --- | --- | --- | --- |
| `dataset_id` | integer | Yes | — | Active owning dataset identifier. |
| `category_id` | integer | Yes | — | Category identifier in that dataset. |
| `name` | string or null | No | `null` | Replacement trimmed name, 1–255 chars. |
| `description` | string or null | No | `null` | Replacement description; omitted retains the current value. |

## Preconditions

The dataset and category must be active, and at least one replacement field must be
provided.

## Behavior and invariants

Only supplied fields change. A replacement name must not conflict with another active
category.

## Output

`data` is the updated `CategoryRecord`.

## Business errors

- `DATASET_NOT_FOUND`, `DATASET_DELETED`, `CATEGORY_NOT_FOUND`, or `CATEGORY_DELETED`.
- `CATEGORY_NAME_CONFLICT`: the replacement name is already active.
- `INVALID_ARGUMENT`: no change, empty name, or invalid input.

## Example

```json
{ "dataset_id": 17, "category_id": 4, "description": "Road vehicle" }
```

## Acceptance criteria

- A supplied field changes while an omitted field retains its value.
- Empty updates and conflicting names fail without modifying the category.
