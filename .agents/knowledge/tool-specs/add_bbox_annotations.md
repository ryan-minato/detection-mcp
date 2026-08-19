# `add_bbox_annotations`

## Purpose

Add one or more axis-aligned normalized bounding-box annotations to one image atomically.

## Interface

| Parameter | Type | Required | Default | Definition |
| --- | --- | --- | --- | --- |
| `dataset_id` | integer | Yes | — | Active owning dataset identifier. |
| `image_path` | string | Yes | — | Portable dataset-relative target image path. |
| `annotations` | array | Yes | — | Non-empty requests with positive active `category_id` and four-float `bbox` `[x1, y1, x2, y2]`. |

## Preconditions

The dataset must be active, the image must be valid, categories must be active and
owned by the dataset, and every box must be normalized with ordered non-zero area.

## Behavior and invariants

Validates the entire batch before insertion. All valid boxes are stored as `bbox`; a
failure inserts none. Source images remain immutable.

## Output

`data` contains created `annotations` (`AnnotationRecord` values) and `count`.

## Business errors

- `DATASET_NOT_FOUND`, `DATASET_DELETED`, `CATEGORY_NOT_FOUND`, or `CATEGORY_DELETED`.
- `IMAGE_NOT_FOUND` or `PATH_OUTSIDE_DATASET_ROOT`.
- `INVALID_BBOX` or `INVALID_ARGUMENT`: malformed or invalid geometry/batch.
- `TRANSACTION_FAILED`: the batch is not committed.

## Example

```json
{ "dataset_id": 17, "image_path": "camera/0001.jpg", "annotations": [{ "category_id": 4, "bbox": [0.1, 0.2, 0.5, 0.8] }] }
```

## Acceptance criteria

- A valid batch creates all records with `type: "bbox"` and normalized geometry.
- One invalid box or category causes no records from that batch to be created.
