# Product Goals

Read this file when scoping a task, deciding whether behavior belongs in v1, or
checking product acceptance criteria.

## Goal

`detection-mcp` is a local STDIO Model Context Protocol server that lets an AI
agent register image datasets, define categories, track image status, create and
review axis-aligned or rotated bounding boxes, and export training metadata. It
stores its own state in SQLite and never changes source images.

## Product Contract

- The v1 public surface is exactly 23 MCP tools: 5 dataset, 6 category, 4 image
  and review, 7 annotation, and 1 export tool. MCP contract tests define their
  names and input/output schemas.
- Axis-aligned boxes use normalized `xyxy`; rotated boxes use normalized
  four-point polygons. Writes validate immediately; batch writes are atomic.
- Images move between `unannotated`, `in_progress`, and `completed`. Export
  preflights the dataset and exports only completed images.
- `autotrain` exports its compatible flat-image JSONL subset. `extended` also
  represents rotated boxes and portable nested paths.

## v1 Boundaries

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

## Authority

Executable tests define current behavior. This knowledge base records the intended
product contract and must be updated when confirmed behavior changes. If a test and
this document disagree, investigate the discrepancy before changing either one.
