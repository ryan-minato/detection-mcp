import re
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

pytestmark = pytest.mark.integration

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"
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
