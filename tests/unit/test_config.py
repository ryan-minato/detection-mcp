import os
from pathlib import Path

import pytest

from detection_mcp.config import Settings, _bool, _paths

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("value", ["1", "true", "YES", "on", True])
def test_bool_accepts_true_values(value: str | bool) -> None:
    assert _bool(value, False) is True


@pytest.mark.parametrize("value", ["0", "false", "NO", "off", False])
def test_bool_accepts_false_values(value: str | bool) -> None:
    assert _bool(value, True) is False


def test_bool_uses_default_and_rejects_unknown() -> None:
    assert _bool(None, True) is True
    with pytest.raises(ValueError, match="invalid boolean"):
        _bool("perhaps", True)


def test_paths_accept_lists_and_path_separated_strings(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    assert _paths([str(first), "", str(second)]) == (first.resolve(), second.resolve())
    assert _paths(f"{first}{os.pathsep}{second}") == (first.resolve(), second.resolve())
    assert _paths(None) == ()


def test_settings_respect_cli_over_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    environment_root = tmp_path / "environment"
    command_root = tmp_path / "command"
    export_root = tmp_path / "exports"
    monkeypatch.setenv("DETECTION_MCP_DB_PATH", str(tmp_path / "environment.db"))
    monkeypatch.setenv("DETECTION_MCP_RANDOM_SEED", "9")
    monkeypatch.setenv("DETECTION_MCP_ROTATED_CORRECTION_ENABLED", "false")
    monkeypatch.setenv("DETECTION_MCP_ALLOWED_DATASET_ROOTS", str(environment_root))
    monkeypatch.setenv("DETECTION_MCP_ALLOWED_EXPORT_ROOTS", str(export_root))
    monkeypatch.setenv("DETECTION_MCP_LOG_LEVEL", "debug")

    settings = Settings.from_values(db_path=tmp_path / "command.db", allowed_dataset_roots=[str(command_root)])

    assert settings.db_path == (tmp_path / "command.db").resolve()
    assert settings.random_seed == 9
    assert settings.rotated_correction_enabled is False
    assert settings.allowed_dataset_roots == (command_root.resolve(),)
    assert settings.allowed_export_roots == (export_root.resolve(),)
    assert settings.log_level == "DEBUG"


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ({"preview_max_width": 0}, "preview dimensions"),
        ({"preview_max_height": -1}, "preview dimensions"),
        ({"rotated_correction_threshold": 0.05, "rotated_error_threshold": 0.05}, "rotated thresholds"),
        ({"rotated_correction_threshold": -0.1}, "rotated thresholds"),
    ],
)
def test_settings_reject_invalid_values(values: dict[str, int | float], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        Settings.from_values(**values)
