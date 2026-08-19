# detection-mcp

[简体中文](README.zh-CN.md)

`detection-mcp` is a local STDIO Model Context Protocol server for object-detection annotation. It stores workflow state and annotations in SQLite, renders review previews in memory, and exports JSONL without modifying source images.

## Status

The v1 implementation is available for review. It exposes 23 tools for datasets, categories, images, axis-aligned boxes, rotated boxes, previews, and export. The package targets Python 3.12 or newer and uses `fastmcp>=3.4.7,<4.0.0`, allowing compatible 3.x security updates.

## Install from this repository

Install [uv](https://docs.astral.sh/uv/), then run:

```bash
uv tool install .
detection-mcp --version
```

For repository development:

```bash
uv sync --locked --all-groups
uv run pre-commit install --install-hooks --hook-type pre-commit --hook-type commit-msg --hook-type pre-push
```

## Configure an MCP client

Use an installed executable and grant only the directories the task needs:

```json
{
  "mcpServers": {
    "detection-mcp": {
      "command": "detection-mcp",
      "args": [
        "--db-path", "/var/lib/detection-mcp/annotations.db",
        "--allowed-dataset-root", "/srv/datasets",
        "--allowed-export-root", "/srv/exports"
      ]
    }
  }
}
```

The server uses STDIO: protocol messages go to stdout and logs go to stderr. CLI options override `DETECTION_MCP_*` environment variables, followed by built-in defaults.

### Configuration reference

| Purpose | CLI | Environment | Default |
|---|---|---|---|
| SQLite file | `--db-path` | `DETECTION_MCP_DB_PATH` | platform user-data directory |
| Dataset roots | repeated `--allowed-dataset-root` | `DETECTION_MCP_ALLOWED_DATASET_ROOTS` | unrestricted |
| Export roots | repeated `--allowed-export-root` | `DETECTION_MCP_ALLOWED_EXPORT_ROOTS` | unrestricted |
| Random order seed | `--random-seed` | `DETECTION_MCP_RANDOM_SEED` | `42` |
| Preview width | `--preview-max-width` | `DETECTION_MCP_PREVIEW_MAX_WIDTH` | `768` |
| Preview height | `--preview-max-height` | `DETECTION_MCP_PREVIEW_MAX_HEIGHT` | `768` |
| Rotated correction | `--rotated-correction-enabled` / `--no-rotated-correction` | `DETECTION_MCP_ROTATED_CORRECTION_ENABLED` | enabled |
| Correction threshold | `--rotated-correction-threshold` | `DETECTION_MCP_ROTATED_CORRECTION_THRESHOLD` | `0.01` |
| Rejection threshold | `--rotated-error-threshold` | `DETECTION_MCP_ROTATED_ERROR_THRESHOLD` | `0.05` |
| Logging | `--log-level` | `DETECTION_MCP_LOG_LEVEL` | `INFO` |

Environment root lists use the operating-system path separator. Empty allowed-root lists retain the portable default, but deployments should configure explicit roots. Dataset permission never grants export permission. Run `detection-mcp --version` without starting an MCP session.

## Annotation workflow

1. Register a dataset root and define categories.
2. List images by status or deterministic random order.
3. Preview an orientation-corrected image.
4. Add normalized axis-aligned or rotated boxes in atomic batches.
5. Preview the overlay and correct annotations before marking the image completed.
6. Export completed images to AutoTrain or extended JSONL.

## Install the Agent Skills

The installable Agent Skills for detection-mcp users live in the repository's root
`skills/` directory. They are not included in the Python wheel, source distribution,
or container image. Install either Skill directly from GitHub with the [skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add ryan-minato/detection-mcp --skill object-detection-annotation
npx skills add ryan-minato/detection-mcp --skill detection-mcp-setup
```

The default installation is project-local. Add `--global` when the Skill should be available across projects.

## Tool groups

| Area | Tools |
|---|---|
| Datasets | `create_dataset`, `delete_dataset`, `restore_dataset`, `list_datasets`, `get_dataset` |
| Categories | `add_categories`, `edit_category`, `delete_category`, `restore_category`, `list_categories`, `get_category` |
| Images and review | `list_images`, `set_image_status`, `preview_image`, `preview_annotations` |
| Annotations | `list_annotations`, three bbox tools, and three rotated-bbox tools |
| Export | `export_metadata_jsonl` |

Every ordinary success returns `{ "ok": true, "data": ... }`. Domain failures return `{ "ok": false, "error": { "code": ..., "message": ... } }` as an MCP error result. Preview tools return PNG image content plus the same structured envelope. The schemas returned by `list_tools` are the machine-readable contract.

## Export format

`export_metadata_jsonl` exports only images marked `completed`. It writes to a temporary file, flushes it, and atomically replaces the destination while holding an exclusive lock file.

### AutoTrain mode

AutoTrain mode requires at least five completed images in a flat dataset root. Files must use `.jpg`, `.jpeg`, or `.png`. Each JSONL object contains `file_name` and `objects`; bbox values are pixel `[x, y, width, height]` coordinates and categories are zero-based export indices.

Rotated boxes are not representable in the AutoTrain bbox schema. They are counted in `ignored_rotated_annotations` and omitted. Images without annotations remain negative samples with empty arrays.

### Extended mode

Extended mode also emits `polygon` and `polygon_category` arrays. Each polygon is eight pixel coordinates in canonical point order. Nested portable image paths and WebP images are allowed.

Deleted-category annotations are excluded and reported. Existing output is rejected unless `overwrite=true`; a concurrent lock is also reported as an existing-output error.

## Development commands

`just` is the repository command executor:

```bash
just sync       # synchronize the locked environment
just test       # run ordinary tests
just quality-control # run CI checks without tests
just quality    # run the complete local commit gate
just hooks      # run repository hooks against tracked files
just check      # run quality and hooks
```

Never bypass Git hooks. Every commit requires the full quality gate and a staged secret/PII scan. See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and [AGENTS.md](AGENTS.md).

## Containers

The production image runs as the non-root `detection-mcp` system user and starts the STDIO server directly. Set two host paths and launch the example:

```bash
export DETECTION_MCP_DATASET_PATH=/srv/datasets
export DETECTION_MCP_OUTPUT_PATH=/srv/detection-mcp-output
docker compose -f docker-compose.example.yml run --rm detection-mcp
```

The example mounts `/datasets` read-only, `/output` writable, and `/state` from a named persistent volume. Pass container paths such as `/datasets/coco-subset` and `/output/metadata.jsonl` to MCP tools; host paths are not visible inside the container.

An MCP desktop client can use `docker run --interactive` with the same mounts as its STDIO command. Do not mount a home directory or filesystem root. The database must not share the read-only dataset mount. Back up the state volume and export output independently; source images remain outside this server's ownership.

## License

Apache-2.0. See [LICENSE](LICENSE).
