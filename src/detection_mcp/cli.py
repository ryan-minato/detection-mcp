"""Console entry point for the local STDIO server."""

import argparse
import importlib.metadata
import logging
import sys
from pathlib import Path

from detection_mcp.config import Settings
from detection_mcp.server import create_server


def _parser() -> argparse.ArgumentParser:
    """Build the command-line parser used by the console entry point."""
    parser = argparse.ArgumentParser(prog="detection-mcp")
    parser.add_argument("--version", action="store_true", help="print the installed version and exit")
    parser.add_argument("--db-path", type=Path)
    parser.add_argument("--random-seed", type=int)
    parser.add_argument("--preview-max-width", type=int)
    parser.add_argument("--preview-max-height", type=int)
    correction = parser.add_mutually_exclusive_group()
    correction.add_argument("--rotated-correction-enabled", action="store_true", default=None)
    correction.add_argument(
        "--no-rotated-correction",
        action="store_false",
        dest="rotated_correction_enabled",
    )
    parser.add_argument("--rotated-correction-threshold", type=float)
    parser.add_argument("--rotated-error-threshold", type=float)
    parser.add_argument("--allowed-dataset-root", action="append", dest="allowed_dataset_roots")
    parser.add_argument("--allowed-export-root", action="append", dest="allowed_export_roots")
    parser.add_argument("--log-level")
    return parser


def main() -> None:
    """Run informational CLI commands or start the STDIO MCP server.

    Returns:
        None.

    Raises:
        SystemExit: If argument parsing fails or an informational command exits.
        OSError: If application storage cannot be initialized.

    Notes:
        Protocol output is written to stdout by FastMCP; logs and argument errors
        use stderr so they cannot corrupt the STDIO transport.
    """
    arguments = _parser().parse_args()
    if arguments.version:
        sys.stdout.write(f"{importlib.metadata.version('detection-mcp')}\n")
        return
    try:
        settings = Settings.from_values(**{key: value for key, value in vars(arguments).items() if key != "version"})
    except ValueError as error:
        _parser().error(str(error))
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    create_server(settings).run()
