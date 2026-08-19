"""Tests for repository Agent Skill validation."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_validator_includes_public_and_project_skill_roots() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_skills.py")],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert ".agents/skills/" in result.stdout
