import re
import subprocess
import sys
import tomllib
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


def test_release_workflow_tests_built_artifacts_before_publishing() -> None:
    workflow = _load_workflow("release.yml")

    assert workflow["on"] == {"release": {"types": ["published"]}}
    assert workflow["permissions"] == {"contents": "read"}

    jobs = workflow["jobs"]
    version_step = next(step for step in jobs["package-build"]["steps"] if step["name"] == "Verify release version")
    assert 'test "v$(uv version --short)" = "$RELEASE_TAG"' in version_step["run"]
    assert jobs["package-test"]["strategy"]["matrix"]["package-format"] == ["wheel", "sdist"]
    assert jobs["package-test"]["needs"] == "package-build"
    assert jobs["container-test"]["needs"] == "package-build"

    required_tests = ["package-test", "container-test"]
    assert jobs["publish-pypi"]["needs"] == required_tests
    assert jobs["publish-container"]["needs"] == required_tests


def test_release_workflow_uses_minimal_publish_permissions() -> None:
    workflow = _load_workflow("release.yml")
    jobs = workflow["jobs"]

    pypi = jobs["publish-pypi"]
    assert pypi["permissions"] == {"id-token": "write"}
    assert pypi["environment"] == {"name": "pypi", "url": "https://pypi.org/p/detection-mcp"}
    assert "password" not in str(pypi)
    assert "token" not in str(pypi["steps"])

    container = jobs["publish-container"]
    assert container["permissions"] == {"contents": "read", "packages": "write"}
    metadata = next(step for step in container["steps"] if step.get("id") == "metadata")
    assert metadata["with"]["images"] == "ghcr.io/${{ github.repository }}"
    assert metadata["with"]["flavor"] == "latest=auto"
    assert metadata["with"]["tags"] == "type=pep440,pattern={{version}}"

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


def test_gitleaks_extends_default_secret_rules() -> None:
    config = tomllib.loads((ROOT / ".gitleaks.toml").read_text())

    assert config["extend"]["useDefault"] is True
