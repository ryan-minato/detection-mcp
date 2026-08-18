"""Scan candidate repository text for common secrets and personal information."""

import argparse
import ipaddress
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GIT = shutil.which("git") or "git"
MAX_FILE_SIZE = 2_000_000
SCAN_EXCLUDES = {Path(".gitleaks.toml")}
PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")),
    (
        "credential assignment",
        re.compile(
            r"(?i)\b(?:api[_-]?key|client[_-]?secret|password|passwd|secret|access[_-]?token)\b"
            r"\s*[:=]\s*['\"](?!example|placeholder|redacted|changeme)[^'\"\s]{8,}['\"]"
        ),
    ),
    ("email address", re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")),
    ("personal home path", re.compile(r"(?<![A-Za-z0-9_])(?:/home|/Users)/[A-Za-z0-9._-]+/")),
)
IPV4_PATTERN = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")


def git_paths(staged: bool) -> list[Path]:
    """List candidate tracked or staged paths for the local scan."""
    command = [GIT, "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"]
    if not staged:
        command = [GIT, "ls-files", "--cached", "--others", "--exclude-standard", "-z"]
    result = subprocess.run(command, cwd=ROOT, check=True, capture_output=True)  # noqa: S603
    return [ROOT / item.decode() for item in result.stdout.split(b"\0") if item]


def staged_bytes(path: Path) -> bytes:
    """Read one file from the staged Git snapshot."""
    relative = path.relative_to(ROOT).as_posix()
    return subprocess.run(  # noqa: S603
        [GIT, "show", f":{relative}"], cwd=ROOT, check=True, capture_output=True
    ).stdout


def public_ip_matches(text: str) -> list[str]:
    """Return syntactically valid public IPv4 values found in text."""
    matches: list[str] = []
    for candidate in IPV4_PATTERN.findall(text):
        try:
            address = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if address.is_global:
            matches.append(candidate)
    return matches


def main() -> int:
    """Run the repository sensitivity scan and return its exit status."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--staged", action="store_true", help="scan the staged snapshot only")
    arguments = parser.parse_args()
    findings: list[str] = []
    for path in git_paths(arguments.staged):
        if path.relative_to(ROOT) in SCAN_EXCLUDES:
            continue
        try:
            data = staged_bytes(path) if arguments.staged else path.read_bytes()
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
        if len(data) > MAX_FILE_SIZE or b"\0" in data[:8192]:
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        relative = path.relative_to(ROOT)
        for line_number, line in enumerate(text.splitlines(), 1):
            for label, pattern in PATTERNS:
                if pattern.search(line):
                    findings.append(f"{relative}:{line_number}: possible {label}")
            if public_ip_matches(line):
                findings.append(f"{relative}:{line_number}: possible public IP address")
    if findings:
        print("Sensitive-data scan: YES", file=sys.stderr)
        for finding in findings:
            print(f"ERROR: {finding}", file=sys.stderr)
        print("Review locally; do not commit or publish the candidate content.", file=sys.stderr)
        return 1
    print("Sensitive-data scan: NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
