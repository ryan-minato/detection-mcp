# Configuration

CLI options take precedence over environment variables, followed by built-in defaults.

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

Environment root lists use the operating system path separator. Empty allowed-root lists retain the portable default, but deployments should always configure explicit roots. Dataset permission never grants export permission.

Run `detection-mcp --skills-path` to locate installed Agent Skills. Run `detection-mcp --version` without starting an MCP session.
