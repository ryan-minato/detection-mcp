# Docker Deployment

The runtime image is built by `Dockerfile`, runs as the `detection-mcp` system user, and starts the STDIO server directly.

Set two host paths and launch the example:

```bash
export DETECTION_MCP_DATASET_PATH=/srv/datasets
export DETECTION_MCP_EXPORT_PATH=/srv/exports
docker compose -f docker-compose.example.yml run --rm detection-mcp
```

The example mounts `/datasets` read-only, `/exports` writable, and `/state` from a named persistent volume. An MCP desktop client can use `docker run --interactive` with equivalent mounts as its STDIO command.

Do not mount a home directory or filesystem root. The database must not share the read-only dataset mount. Back up the state volume and export output independently; the source dataset remains outside this server's ownership.
