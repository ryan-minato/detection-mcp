---
name: object-detection-annotation
description: >
  Annotates local object-detection datasets through detection-mcp while keeping source images immutable. Use when an agent must inspect images, manage category labels, create axis-aligned or rotated boxes, review overlays, track completion, or export AutoTrain-compatible JSONL. Do not use for image editing, segmentation masks, cloud labeling services, or training models.
license: Apache-2.0
compatibility: Requires a configured detection-mcp server with access to the dataset and export roots.
metadata:
  version: "1.0"
---

# Object Detection Annotation

Use the MCP tools as a reviewable annotation workflow, not as an image editor.

## Workflow

1. Call `list_datasets`; use `create_dataset` only when the intended root is not registered.
2. Call `list_categories`, then call `get_category` for every category selected for the current image. Treat the returned descriptions as authoritative. Add or edit categories only when the task explicitly requires it.
3. Call `list_images` with an explicit status and order. Work on one returned portable path at a time.
4. Call `set_image_status` with `in_progress` before inspecting or changing the selected image.
5. Call `preview_image` before deciding geometry. Use the returned orientation-corrected dimensions as the coordinate space.
6. Call `list_annotations` for the selected image before every write. Preserve valid existing work and avoid creating duplicate objects.
7. Add or edit annotations:
   - Use `add_bbox_annotations` for axis-aligned objects.
   - Use `add_rotated_bbox_annotations` only when object rotation materially matters.
   - Send related annotations as one batch so validation is atomic.
8. Call `preview_annotations` and visually verify category, coverage, tightness, and object count. Before each corrective write, call `list_annotations` again; then preview the result.
9. Call `set_image_status` with `completed` only after the overlay has been reviewed.
10. Call `export_metadata_jsonl` only when the user requests an export and the output path is within an allowed export root.

Done when: every requested image has reviewed annotations, its intended workflow status is recorded, and any requested export reports its output path and counts.

Read [references/geometry.md](references/geometry.md) when creating or correcting bounding-box coordinates.

Read [references/recovery.md](references/recovery.md) when a category, annotation, dataset, or status is wrong or deleted.

## Safety Boundaries

- Never modify, rename, move, or delete a source image.
- Use only portable paths returned by the server; do not invent absolute paths.
- Do not mark an image completed merely because annotations were submitted.
- Treat a structured tool error as a failed operation. Correct its stated cause before retrying.
- Ask the user when category meaning is ambiguous or when an object cannot be classified from the preview.
