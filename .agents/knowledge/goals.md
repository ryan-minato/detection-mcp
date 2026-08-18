# Product Goals

Read this file when scoping a task, deciding whether behavior belongs in v1, or
checking product acceptance criteria.

## Goal

`detection-mcp` is a local STDIO Model Context Protocol server that lets an AI
agent register image datasets, define categories, track image status, create and
review axis-aligned or rotated bounding boxes, and export training metadata. It
stores its own state in SQLite and never changes source images.

## v1 Boundaries

- Implement exactly the 23 tools defined in `docs/requirements.zh-CN.md`.
- Support PyPI and Docker installation. Docker runs as a non-root user with
  read-only datasets and separate writable state and output mounts.
- Use normalized `xyxy` for axis-aligned boxes and normalized four-point polygons
  for rotated boxes.
- Validate writes immediately and run a dataset-wide preflight before export.
- Return stable structured data and stable business error codes.
- Ship one Skill for annotation work and one Skill for installation and setup.

Do not add HTTP deployment, authentication, multi-tenancy, image fingerprinting,
annotation history, undo, arbitrary polygons, segmentation, dataset splits, or a
GUI in v1.

## Acceptance Source

`docs/requirements.zh-CN.md` is the product behavior source of truth. If code and
that document disagree, stop and resolve the discrepancy in the active change.
