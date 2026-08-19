"""Tests for repository Agent Skill validation."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_validator():
    path = ROOT / "scripts" / "validate_skills.py"
    spec = importlib.util.spec_from_file_location("validate_skills", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_skill_directories_include_public_and_project_skill_roots() -> None:
    validator = _load_validator()
    public_root = ROOT / "skills"
    project_root = ROOT / ".agents" / "skills"
    expected = {path for skills_root in (public_root, project_root) for path in skills_root.iterdir() if path.is_dir()}

    assert validator.SKILL_ROOTS == (public_root, project_root)
    assert set(validator.skill_directories(validator.SKILL_ROOTS)) == expected
