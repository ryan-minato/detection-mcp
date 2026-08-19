# `edit_bbox_annotation`

## Purpose

Replace the category and/or axis-aligned geometry of an existing bounding-box annotation.

## Interface

| Parameter | Type | Required | Default | Definition |
| --- | --- | --- | --- | --- |
| `dataset_id` | integer | Yes | — | Active owning dataset identifier. |
| `annotation_id` | integer | Yes | — | Existing `bbox` annotation identifier. |
| `category_id` | integer or null | No | `null` | Optional replacement active category. |
| `bbox` | float array or null | No | `null` | Optional replacement normalized `[x1, y1, x2, y2]`. |

## Preconditions

The dataset must be active, the annotation must be a matching `bbox`, and at least
one replacement must be supplied.

## Behavior and invariants

Updates only supplied fields and preserves annotation type and ID. Replacement
geometry is validated before persistence.

## Output

`data` is the updated `AnnotationRecord` with `type: "bbox"`.

## Business errors

- `DATASET_NOT_FOUND`, `DATASET_DELETED`, `ANNOTATION_NOT_FOUND`, `CATEGORY_NOT_FOUND`, or `CATEGORY_DELETED`.
- `INVALID_BBOX`: invalid replacement geometry.
- `INVALID_ARGUMENT`: no change or invalid input.

## Example

```json
{ "dataset_id": 17, "annotation_id": 31, "bbox": [0.15, 0.2, 0.55, 0.85] }
```

## Acceptance criteria

- A valid replacement updates only the specified fields and keeps `type: "bbox"`.
- A wrong-type ID, empty update, or invalid box leaves the annotation unchanged.
