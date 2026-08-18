"""Validate a Conventional Commit message without modifying it."""

import re
import sys
from pathlib import Path

HEADER = re.compile(r"^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)(\([a-z0-9-]+\))?(!)?: [^\s].+$")


def main() -> int:
    """Validate the commit message file supplied by Git and return a status."""
    if len(sys.argv) != 2:
        print("usage: validate_commit_message.py COMMIT_MSG_FILE", file=sys.stderr)
        return 2
    lines = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
    header = next((line for line in lines if line and not line.startswith("#")), "")
    if len(header) > 100 or HEADER.fullmatch(header) is None:
        print("Commit header must be an English Conventional Commit of at most 100 characters.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
