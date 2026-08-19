# `edit_rotated_bbox_annotation`

## Purpose

Replace the category and/or canonical rotated geometry of one rotated annotation.

## Interface

| Parameter | Type | Required | Default | Definition |
| --- | --- | --- | --- | --- |
| `dataset_id` | integer | Yes | — | Active owning dataset identifier. |
| `annotation_id` | integer | Yes | — | Existing `rotated_bbox` annotation identifier. |
| `category_id` | integer or null | No | `null` | Optional replacement active category. |
| `polygon` | float array or null | No | `null` | Optional replacement normalized four-point polygon. |

## Preconditions

The dataset must be active, the annotation must be a matching `rotated_bbox`, and at
least one replacement must be supplied. A supplied polygon must be correctable within tolerance.

## Behavior and invariants

Updates only supplied fields, preserves ID/type, and returns correction diagnostics.
Omitted geometry retains its stored canonical value.

## Output

`data` has `AnnotationRecord` fields plus `submitted_geometry`, `stored_geometry`,
`corrected`, `deviation`, and optional `warning`.

## Business errors

- `DATASET_NOT_FOUND`, `DATASET_DELETED`, `ANNOTATION_NOT_FOUND`, `CATEGORY_NOT_FOUND`, or `CATEGORY_DELETED`.
- `INVALID_ROTATED_BBOX` or `ROTATED_BBOX_CORRECTION_EXCEEDED`.
- `INVALID_ARGUMENT`: no change or malformed input.

## Example

```json
{ "dataset_id": 17, "annotation_id": 32, "category_id": 5 }
```

## Acceptance criteria

- A valid update keeps the annotation as `rotated_bbox` and returns correction metadata.
- Wrong-type IDs, empty updates, and invalid polygons leave the record unchanged.
