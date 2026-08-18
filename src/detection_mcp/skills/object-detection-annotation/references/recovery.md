# Recovery Guide

- Use `edit_bbox_annotation` or `edit_rotated_bbox_annotation` to correct
  geometry or category assignment in place.
- Use the matching delete tool to hard-delete incorrect annotations. Recreate
  them with the appropriate add tool when needed.
- Use `restore_category` for an accidentally deleted category. Supply a new name
  if its former name now conflicts with an active category.
- Use `restore_dataset` for an accidentally deleted dataset registration.
- Use `set_image_status` to move an image back to `in_progress` or `unannotated`
  when review finds unfinished work.

Batch calls are atomic: if one item fails validation, none of that batch is
stored. Fix the invalid item and submit the complete intended batch again.
