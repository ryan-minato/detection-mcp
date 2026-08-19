# `preview_image`

## Purpose

Return an orientation-corrected PNG preview and its visual-coordinate metadata before annotation.

## Interface

| Parameter | Type | Required | Default | Definition |
| --- | --- | --- | --- | --- |
| `dataset_id` | integer | Yes | — | Owning dataset identifier. |
| `image_path` | string | Yes | — | Portable dataset-relative image path. |
| `max_width` | integer or null | No | `null` | Optional positive width limit. |
| `max_height` | integer or null | No | `null` | Optional positive height limit. |
| `allow_upscale` | boolean | No | `false` | Permit enlargement of a smaller image. |
| `show_grid` | boolean | No | `true` | Overlay a semi-transparent grid: 5 major cells per axis, each with 5 minor intervals and marked intersections. |

## Preconditions

The dataset and image must be available, decodable, and contained within the dataset root.

## Behavior and invariants

Uses orientation-corrected visual dimensions. Requested dimensions are clamped to
server limits; no preview file or source file is written. Unless disabled, a white
semi-transparent grid divides each axis into five major cells and each major cell
into five minor divisions, with grid intersections marked for position counting.

## Output

The MCP content contains a PNG image and a success envelope. `data` contains
`original_width`, `original_height`, `preview_width`, `preview_height`, `scale`,
`orientation_applied`, `dataset_id`, `image_path`, and `clamped`.

## Business errors

- `DATASET_NOT_FOUND`, `IMAGE_NOT_FOUND`, `PATH_OUTSIDE_DATASET_ROOT`.
- `UNSUPPORTED_IMAGE_FORMAT` or `IMAGE_DECODE_FAILED`.
- `INVALID_ARGUMENT`: non-positive requested dimensions.

## Example

```json
{ "dataset_id": 17, "image_path": "camera/0001.jpg", "max_width": 1280, "show_grid": true }
```

## Acceptance criteria

- A valid request returns PNG content and metadata matching orientation-corrected dimensions.
- The positioning grid is enabled by default and can be disabled without changing preview metadata.
- Invalid dimensions or an unavailable image fail without writing a file.
