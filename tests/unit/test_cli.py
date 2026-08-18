import sys
from pathlib import Path
from typing import Any

import pytest

from detection_mcp import cli
from detection_mcp.config import Settings

pytestmark = pytest.mark.unit


class FakeServer:
    def __init__(self) -> None:
        self.ran = False

    def run(self) -> None:
        self.ran = True


def test_cli_prints_version(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["detection-mcp", "--version"])
    monkeypatch.setattr(cli.importlib.metadata, "version", lambda _name: "1.2.3")
    cli.main()
    assert capsys.readouterr().out == "1.2.3\n"


def test_cli_prints_skills_path(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["detection-mcp", "--skills-path"])
    cli.main()
    assert capsys.readouterr().out.rstrip().endswith("detection_mcp/skills")


def test_cli_builds_settings_and_runs_server(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    server = FakeServer()
    captured: dict[str, Any] = {}

    def create_server(settings: Settings) -> FakeServer:
        captured["settings"] = settings
        return server

    monkeypatch.setattr(cli, "create_server", create_server)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "detection-mcp",
            "--db-path",
            str(tmp_path / "state.db"),
            "--random-seed",
            "7",
            "--no-rotated-correction",
            "--log-level",
            "warning",
        ],
    )
    cli.main()
    assert server.ran is True
    assert captured["settings"].random_seed == 7
    assert captured["settings"].rotated_correction_enabled is False


def test_cli_reports_invalid_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["detection-mcp", "--preview-max-width", "0"])
    with pytest.raises(SystemExit) as captured:
        cli.main()
    assert captured.value.code == 2
