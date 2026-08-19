# `add_rotated_bbox_annotations`

## Purpose

Add rotated rectangular annotations with validated, canonical normalized polygon geometry.

## Interface

| Parameter | Type | Required | Default | Definition |
| --- | --- | --- | --- | --- |
| `dataset_id` | integer | Yes | — | Active owning dataset identifier. |
| `image_path` | string | Yes | — | Portable dataset-relative target image path. |
| `annotations` | array | Yes | — | Non-empty requests with active `category_id` and eight-float four-point `polygon`. |

## Preconditions

The dataset, image, and categories must be valid. Each polygon must describe a
normalized convex rectangle within permitted correction tolerance.

## Behavior and invariants

Validates and canonicalizes every polygon before one atomic insert. Response records
show submitted and stored geometry plus correction diagnostics.

## Output

`data` contains `annotations` and `count`. Each annotation has `AnnotationRecord`
fields plus `submitted_geometry`, `stored_geometry`, `corrected`, `deviation`, and
optional `warning`.

## Business errors

- `DATASET_NOT_FOUND`, `DATASET_DELETED`, `CATEGORY_NOT_FOUND`, `CATEGORY_DELETED`, or `IMAGE_NOT_FOUND`.
- `INVALID_ROTATED_BBOX`: invalid polygon.
- `ROTATED_BBOX_CORRECTION_EXCEEDED`: correction exceeds the allowed tolerance.
- `TRANSACTION_FAILED`: no complete batch commit is possible.

## Example

```json
{ "dataset_id": 17, "image_path": "camera/0001.jpg", "annotations": [{ "category_id": 4, "polygon": [0.2, 0.2, 0.8, 0.2, 0.8, 0.8, 0.2, 0.8] }] }
```

## Acceptance criteria

- Valid polygons create `rotated_bbox` records and disclose any accepted correction.
- One invalid or over-tolerance polygon creates no records from the batch.
