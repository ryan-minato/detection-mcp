---
name: detection-mcp-setup
description: >
  Configures and verifies a local detection-mcp STDIO server and its filesystem boundaries. Use when installing the server, adding it to an MCP client, selecting a SQLite state path, allowing dataset or export roots, or troubleshooting startup. Do not use for performing annotations or changing project source code.
license: Apache-2.0
compatibility: Requires Python 3.12 or newer and a local MCP client that supports STDIO servers.
metadata:
  version: "1.0"
---

# detection-mcp Setup

Configure the smallest filesystem scope the annotation task needs, then verify the server before annotation work begins.

## Setup

1. Choose one installation method:
   - For a local Python installation, install the PyPI package with `uv tool install detection-mcp` and use `detection-mcp` as the STDIO command.
   - For Docker, use `ghcr.io/ryan-minato/detection-mcp:latest` and keep `--interactive` (`-i`) enabled so the MCP client can communicate over STDIO.
2. Confirm `detection-mcp --version` succeeds in the same environment the MCP client will use. For Docker, run the image with `--version`.
3. Choose a persistent SQLite path with `--db-path` or `DETECTION_MCP_DB_PATH`.
4. Allow each dataset parent with a repeated `--allowed-dataset-root` option or `DETECTION_MCP_ALLOWED_DATASET_ROOTS`.
5. Allow export destinations separately with `--allowed-export-root` or `DETECTION_MCP_ALLOWED_EXPORT_ROOTS`.
6. Configure the MCP client to launch the command over STDIO. Keep logs on stderr and do not wrap the command with software that writes banners to stdout.
7. Start a client session and call `list_datasets` to verify the protocol connection.

For Docker, mount exactly the required host directories and use their container paths in MCP tool calls:

```sh
docker run --rm -i \
  --mount type=bind,source=/host/datasets,target=/datasets,readonly \
  --mount type=bind,source=/host/detection-mcp-state,target=/state \
  --mount type=bind,source=/host/detection-mcp-output,target=/output \
  ghcr.io/ryan-minato/detection-mcp:latest
```

The host paths are managed by the operator; the server sees `/datasets`, `/state`, and `/output`. Pass `/datasets/<dataset>` to `create_dataset` and `/output/<file>.jsonl` to `export_metadata_jsonl`. Never pass the corresponding host paths to containerized tools.

Done when: the client can call `list_datasets`, the database survives a restart, dataset roots are read-only by policy, and exports are restricted to their intended destination roots.

Read [references/configuration.md](references/configuration.md) when selecting command-line options or environment variables.

Read [references/troubleshooting.md](references/troubleshooting.md) when startup, connection, path validation, or persistence checks fail.

## Boundaries

- Never use `/` or an entire home directory as an allowed root.
- Mount dataset directories read-only when running in a container.
- Keep the database and export directory on writable persistent storage.
- Do not put credentials or personal filesystem paths in shared client configuration examples.
