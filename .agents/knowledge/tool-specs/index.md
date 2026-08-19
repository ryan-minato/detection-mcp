# MCP Tool Specifications

Read this index before adding, changing, or reviewing an MCP tool. The executable
contract tests and public models define current behavior; these files are the
agent-facing specification for using and maintaining that behavior.

Read [the shared contract](common-contract.md) first, then the specification for
the tool in scope. Use [the template](template.md) for a new tool specification.

## Datasets

- [create_dataset](create_dataset.md)
- [delete_dataset](delete_dataset.md)
- [restore_dataset](restore_dataset.md)
- [list_datasets](list_datasets.md)
- [get_dataset](get_dataset.md)

## Categories

- [add_categories](add_categories.md)
- [edit_category](edit_category.md)
- [delete_category](delete_category.md)
- [restore_category](restore_category.md)
- [list_categories](list_categories.md)
- [get_category](get_category.md)

## Images and review

- [list_images](list_images.md)
- [set_image_status](set_image_status.md)
- [preview_image](preview_image.md)
- [preview_annotations](preview_annotations.md)

## Annotations

- [list_annotations](list_annotations.md)
- [add_bbox_annotations](add_bbox_annotations.md)
- [edit_bbox_annotation](edit_bbox_annotation.md)
- [delete_bbox_annotation](delete_bbox_annotation.md)
- [add_rotated_bbox_annotations](add_rotated_bbox_annotations.md)
- [edit_rotated_bbox_annotation](edit_rotated_bbox_annotation.md)
- [delete_rotated_bbox_annotation](delete_rotated_bbox_annotation.md)

## Export

- [export_metadata_jsonl](export_metadata_jsonl.md)

Keep this index, the shared contract, and the affected specification synchronized
with every tool name, schema, or behavior change.
