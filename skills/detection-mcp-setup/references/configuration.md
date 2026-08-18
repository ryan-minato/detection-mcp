# Configuration Reference

Command-line options override environment variables, which override built-in
defaults.

| Purpose | CLI option | Environment variable |
|---|---|---|
| SQLite state | `--db-path` | `DETECTION_MCP_DB_PATH` |
| Dataset boundary | `--allowed-dataset-root` | `DETECTION_MCP_ALLOWED_DATASET_ROOTS` |
| Export boundary | `--allowed-export-root` | `DETECTION_MCP_ALLOWED_EXPORT_ROOTS` |
| Stable random order | `--random-seed` | `DETECTION_MCP_RANDOM_SEED` |
| Preview width | `--preview-max-width` | `DETECTION_MCP_PREVIEW_MAX_WIDTH` |
| Preview height | `--preview-max-height` | `DETECTION_MCP_PREVIEW_MAX_HEIGHT` |
| Correction threshold | `--rotated-correction-threshold` | `DETECTION_MCP_ROTATED_CORRECTION_THRESHOLD` |
| Rejection threshold | `--rotated-error-threshold` | `DETECTION_MCP_ROTATED_ERROR_THRESHOLD` |
| Log level | `--log-level` | `DETECTION_MCP_LOG_LEVEL` |

Environment root lists use the operating system path separator. Repeat the CLI
root options instead when client configuration supports argument arrays.
