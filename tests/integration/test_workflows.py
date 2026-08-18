import re
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

pytestmark = pytest.mark.integration

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"
ROOT = WORKFLOWS.parents[1]
PINNED_ACTION = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")


def _load_workflow(name: str) -> dict[str, Any]:
    return cast(dict[str, Any], yaml.load((WORKFLOWS / name).read_text(), Loader=yaml.BaseLoader))


def _assert_actions_are_pinned(workflow: dict[str, Any]) -> None:
    for job in workflow["jobs"].values():
        for step in job["steps"]:
            if action := step.get("uses"):
                assert PINNED_ACTION.fullmatch(action)


def test_quality_control_runs_for_all_pushes_and_pull_requests() -> None:
    workflow = _load_workflow("quality.yml")

    assert workflow["on"] == {"pull_request": "", "push": ""}
    assert "if" not in workflow["jobs"]["quality-control"]


def test_container_publish_workflow_has_safe_release_contract() -> None:
    workflow = _load_workflow("publish-container.yml")

    assert workflow["on"] == {"push": {"branches": ["main"], "tags": ["v*.*.*"]}}
    assert workflow["permissions"] == {"contents": "read", "packages": "write"}

    steps = workflow["jobs"]["publish"]["steps"]
    metadata = next(step for step in steps if step.get("id") == "metadata")
    assert metadata["with"]["images"] == "ghcr.io/${{ github.repository }}"
    assert "type=semver,pattern={{version}}" in metadata["with"]["tags"]
    assert "type=raw,value=latest,enable=${{ github.ref == 'refs/heads/main' }}" in metadata["with"]["tags"]
    assert next(step for step in steps if step["name"] == "Build and publish image")["with"]["push"] == "true"
    _assert_actions_are_pinned(workflow)


def test_pypi_publish_workflow_cannot_publish() -> None:
    workflow = _load_workflow("publish-pypi.yml")

    assert workflow["on"] == {"workflow_dispatch": ""}
    assert workflow["jobs"]["build"]["if"] == "${{ false }}"
    assert workflow["jobs"]["publish"]["if"] == "${{ false }}"
    assert workflow["jobs"]["publish"]["permissions"] == {"id-token": "write"}
    assert "password" not in str(workflow["jobs"]["publish"])
    _assert_actions_are_pinned(workflow)


def test_commit_header_limit_is_50_characters(tmp_path: Path) -> None:
    message_file = tmp_path / "COMMIT_EDITMSG"
    command = [sys.executable, str(ROOT / "scripts" / "validate_commit_message.py"), str(message_file)]
    message_file.write_text(f"feat: {'a' * 44}\n")
    accepted = subprocess.run(command, check=False, capture_output=True, text=True)
    message_file.write_text(f"feat: {'a' * 45}\n")
    rejected = subprocess.run(command, check=False, capture_output=True, text=True)

    assert accepted.returncode == 0
    assert rejected.returncode == 1
    assert "at most 50 characters" in rejected.stderr


def test_devcontainer_installs_all_hooks_from_locked_environment() -> None:
    text = (ROOT / ".devcontainer" / "devcontainer.json").read_text()
    expected = (
        '"postCreateCommand": "uv sync --locked --all-groups && uv run pre-commit install --install-hooks '
        '--hook-type pre-commit --hook-type commit-msg --hook-type pre-push"'
    )
    assert expected in text
    assert "pre-commit autoupdate" not in text

    pre_commit = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text())
    standard_hooks = pre_commit["repos"][0]["hooks"]
    check_json = next(hook for hook in standard_hooks if hook["id"] == "check-json")
    assert check_json["exclude"] == r"^\.devcontainer/devcontainer\.json$"
