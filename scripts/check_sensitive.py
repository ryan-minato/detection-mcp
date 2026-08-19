"""Scan candidate repository text for common secrets and personal information."""

import argparse
import ipaddress
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GIT = shutil.which("git") or "git"
MAX_FILE_SIZE = 2_000_000
SCAN_EXCLUDES = {Path(".gitleaks.toml"), Path("uv.lock")}
SAFE_EMAIL_SUFFIXES = ("@example.com", ".example", ".test", ".invalid", "@users.noreply.github.com")
PLACEHOLDER_VALUES = ("example", "placeholder", "redacted", "changeme", "your_", "${")
PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("OpenAI API key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("GitLab token", re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("Stripe live key", re.compile(r"\b(?:sk|rk)_live_[0-9A-Za-z]{16,}\b")),
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
UNQUOTED_CREDENTIAL_PATTERN = re.compile(
    r"(?i)\b(?:api[_-]?key|client[_-]?secret|password|passwd|secret|access[_-]?token|"
    r"auth(?:orization)?|bearer|private[_-]?key)\b\s*[:=]\s*"
    r"(?P<value>[A-Za-z0-9_./+=-]{16,})"
)
IPV4_PATTERN = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
PAYMENT_CARD_PATTERN = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
CN_ID_PATTERN = re.compile(r"(?<!\d)\d{17}[\dXx](?![\dA-Za-z])")
PHONE_PATTERNS = (
    re.compile(r"(?<!\d)(?:\+86[- ]?)?1[3-9](?:[- ]?\d){9}(?!\d)"),
    re.compile(r"(?<!\d)\+\d{1,3}(?:[- ]?\d){7,14}(?!\d)"),
)
CN_ID_WEIGHTS = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
CN_ID_CHECK_DIGITS = "10X98765432"


@dataclass(frozen=True)
class Finding:
    """One potential secret or personal-data match in repository text."""

    label: str
    line_number: int


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


def is_safe_email(value: str) -> bool:
    """Return whether an email address is an intentional documentation example."""
    lowered = value.lower()
    return lowered.endswith(SAFE_EMAIL_SUFFIXES)


def is_placeholder(value: str) -> bool:
    """Return whether a credential-like value is an obvious non-secret placeholder."""
    lowered = value.lower()
    return any(marker in lowered for marker in PLACEHOLDER_VALUES)


def luhn_valid(value: str) -> bool:
    """Return whether a candidate payment-card value passes the Luhn checksum."""
    digits = "".join(character for character in value if character.isdigit())
    if len(digits) < 13 or len(digits) > 19 or len(set(digits)) == 1:
        return False
    total = 0
    for index, digit in enumerate(reversed(digits)):
        number = int(digit)
        if index % 2:
            number *= 2
            if number > 9:
                number -= 9
        total += number
    return total % 10 == 0


def chinese_identity_valid(value: str) -> bool:
    """Return whether an 18-character Chinese resident identity number is valid."""
    normalized = value.upper()
    checksum = sum(int(digit) * weight for digit, weight in zip(normalized[:17], CN_ID_WEIGHTS, strict=True))
    return normalized[-1] == CN_ID_CHECK_DIGITS[checksum % 11]


def scan_text(text: str) -> list[Finding]:
    """Find potential secrets and personal information in UTF-8 text."""
    findings: list[Finding] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        for label, pattern in PATTERNS:
            for match in pattern.finditer(line):
                if label == "email address" and is_safe_email(match.group()):
                    continue
                findings.append(Finding(label, line_number))
        for match in UNQUOTED_CREDENTIAL_PATTERN.finditer(line):
            if not is_placeholder(match.group("value")):
                findings.append(Finding("credential assignment", line_number))
        if any(luhn_valid(match.group()) for match in PAYMENT_CARD_PATTERN.finditer(line)):
            findings.append(Finding("payment card number", line_number))
        if any(chinese_identity_valid(match.group()) for match in CN_ID_PATTERN.finditer(line)):
            findings.append(Finding("Chinese resident identity number", line_number))
        if any(pattern.search(line) for pattern in PHONE_PATTERNS):
            findings.append(Finding("phone number", line_number))
        if public_ip_matches(line):
            findings.append(Finding("public IP address", line_number))
    return findings


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
        findings.extend(f"{relative}:{finding.line_number}: possible {finding.label}" for finding in scan_text(text))
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
