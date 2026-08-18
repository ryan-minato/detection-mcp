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

The server uses STDIO: protocol messages go to stdout and logs go to stderr. CLI options override `DETECTION_MCP_*` environment variables. See [configuration](docs/configuration.md) for all settings.

## Annotation workflow

1. Register a dataset root and define categories.
2. List images by status or deterministic random order.
3. Preview an orientation-corrected image.
4. Add normalized axis-aligned or rotated boxes in atomic batches.
5. Preview the overlay and correct annotations before marking the image completed.
6. Export completed images to AutoTrain or extended JSONL.

The bundled `object-detection-annotation` and `detection-mcp-setup` Agent Skills can be located after installation with `detection-mcp --skills-path`.

## Tool groups

| Area | Tools |
|---|---|
| Datasets | `create_dataset`, `delete_dataset`, `restore_dataset`, `list_datasets`, `get_dataset` |
| Categories | `add_categories`, `edit_category`, `delete_category`, `restore_category`, `list_categories`, `get_category` |
| Images and review | `list_images`, `set_image_status`, `preview_image`, `preview_annotations` |
| Annotations | `list_annotations`, three bbox tools, and three rotated-bbox tools |
| Export | `export_metadata_jsonl` |

See the complete [tool reference](docs/tool-reference.md) and [export format](docs/export-format.md).

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

The production image runs as a non-root user. Dataset mounts must be read-only, while state and exports require separate writable mounts. See [Docker deployment](docs/docker.md) and `docker-compose.example.yml`.

## License

Apache-2.0. See [LICENSE](LICENSE).
