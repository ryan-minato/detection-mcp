# Tool Reference

Every ordinary success returns `{ "ok": true, "data": ... }`. Domain failures return `{ "ok": false, "error": { "code": ..., "message": ... } }` as an MCP error result. Preview tools return PNG image content plus the same structured envelope.

| Tool | Purpose |
|---|---|
| `create_dataset` | Register a canonical image root. |
| `delete_dataset` | Soft-delete a dataset registration. |
| `restore_dataset` | Restore a soft-deleted dataset. |
| `list_datasets` | List active or all registrations. |
| `get_dataset` | Get one registration by stable ID. |
| `add_categories` | Atomically add named categories. |
| `edit_category` | Edit a category name or description. |
| `delete_category` | Soft-delete a category. |
| `restore_category` | Restore a category, optionally under a new name. |
| `list_categories` | List active or all categories. |
| `get_category` | Get one category by stable ID. |
| `list_images` | Discover supported images with status, ordering, and pagination. |
| `set_image_status` | Record `unannotated`, `in_progress`, or `completed`. |
| `preview_image` | Return an EXIF-corrected, bounded PNG preview. |
| `preview_annotations` | Return an overlay PNG and annotation count. |
| `list_annotations` | Filter and paginate stored annotations. |
| `add_bbox_annotations` | Atomically add normalized `[x1,y1,x2,y2]` boxes. |
| `edit_bbox_annotation` | Edit bbox geometry or category. |
| `delete_bbox_annotation` | Atomically hard-delete bbox IDs. |
| `add_rotated_bbox_annotations` | Validate, normalize, and add four-point boxes. |
| `edit_rotated_bbox_annotation` | Edit rotated geometry or category. |
| `delete_rotated_bbox_annotation` | Atomically hard-delete rotated-box IDs. |
| `export_metadata_jsonl` | Atomically export completed images. |

The Pydantic schemas returned by `list_tools` are the machine-readable contract. Contract tests fail if this exact tool set changes.
