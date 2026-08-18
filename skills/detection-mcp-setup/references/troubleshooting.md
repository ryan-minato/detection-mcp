# Troubleshooting

- If the client cannot connect, run `detection-mcp --version` in the configured
  environment and confirm the executable path.
- If the protocol stream is invalid, remove wrappers that print activation or
  status messages to stdout. Send diagnostics to stderr.
- If a dataset or export path is rejected, resolve its real path and confirm it
  is inside the matching allowed root. Dataset permission does not imply export
  permission.
- If state disappears after restart, confirm `--db-path` points to persistent,
  writable storage rather than a temporary container layer.
- If previews appear rotated relative to raw metadata, use the dimensions and
  pixels returned by the preview tool; the server applies EXIF orientation.
- If a bundled skill path is missing, reinstall from a built wheel and rerun
  `detection-mcp --skills-path`.
