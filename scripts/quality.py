"""Run the complete local quality gate in a stable order."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMANDS: tuple[tuple[str, ...], ...] = (
    ("uv", "run", "ruff", "format", "--check", "."),
    ("uv", "run", "ruff", "check", "."),
    ("uv", "run", "ty", "check"),
    (
        "uv",
        "run",
        "pytest",
        "--cov=detection_mcp",
        "--cov-branch",
        "--cov-report=term-missing",
        "--cov-fail-under=90",
    ),
    ("uv", "run", "python", "scripts/validate_skills.py"),
    ("uv", "run", "python", "scripts/verify_build.py"),
    ("uv", "run", "python", "scripts/check_sensitive.py"),
)


def main() -> int:
    """Run quality commands in order and return the first failure status."""
    for command in COMMANDS:
        print(f"+ {' '.join(command)}", flush=True)
        completed = subprocess.run(command, cwd=ROOT, check=False)  # noqa: S603
        if completed.returncode:
            return completed.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
