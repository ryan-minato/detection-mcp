# `create_dataset`

## Purpose

Register an authorized image-root directory as a dataset without changing source files.

## Interface

| Parameter | Type | Required | Default | Definition |
| --- | --- | --- | --- | --- |
| `root_path` | string | Yes | — | Existing dataset root within an allowed dataset root. |
| `name` | string or null | No | `null` | Optional display name. |

## Preconditions

`root_path` must resolve to an existing authorized directory.

## Behavior and invariants

Stores the resolved root in SQLite and creates a stable dataset ID. It does not scan,
write, move, or alter source images.

## Output

`data` is a `DatasetRecord` with its assigned ID, resolved `root_path`, optional
`name`, null `deleted_at`, and creation/update timestamps.

## Business errors

- `PATH_NOT_ALLOWED`: the root is outside configured dataset roots.
- `IMAGE_ROOT_UNAVAILABLE`: the root does not exist or cannot be used.
- `STORAGE_ERROR`: dataset state cannot be persisted.

## Example

```json
{ "root_path": "/datasets/road-images", "name": "Road images" }
```

## Acceptance criteria

- A valid authorized directory returns a persisted active `DatasetRecord`.
- An unauthorized or unavailable directory fails without changing source files.
