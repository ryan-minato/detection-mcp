"""Server configuration with CLI-over-environment precedence."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from platformdirs import user_data_path

ENV_PREFIX = "DETECTION_MCP_"


def _env(name: str) -> str | None:
    return os.environ.get(f"{ENV_PREFIX}{name}")


def _bool(value: str | bool | None, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"invalid boolean value: {value}")


def _paths(value: list[str] | tuple[str, ...] | str | None) -> tuple[Path, ...]:
    if value is None:
        return ()
    raw = value if isinstance(value, (list, tuple)) else value.split(os.pathsep)
    return tuple(Path(item).expanduser().resolve() for item in raw if item)


@dataclass(frozen=True, slots=True)
class Settings:
    db_path: Path
    random_seed: int = 42
    preview_max_width: int = 768
    preview_max_height: int = 768
    rotated_correction_enabled: bool = True
    rotated_correction_threshold: float = 0.01
    rotated_error_threshold: float = 0.05
    allowed_dataset_roots: tuple[Path, ...] = ()
    allowed_export_roots: tuple[Path, ...] = ()
    log_level: str = "INFO"

    @classmethod
    def from_values(cls, **values: Any) -> "Settings":
        default_db = user_data_path("detection-mcp") / "annotations.db"

        def choose(name: str, default: Any) -> Any:
            value = values.get(name)
            if value is not None:
                return value
            env_value = _env(name.upper())
            return default if env_value is None else env_value

        settings = cls(
            db_path=Path(choose("db_path", default_db)).expanduser().resolve(),
            random_seed=int(choose("random_seed", 42)),
            preview_max_width=int(choose("preview_max_width", 768)),
            preview_max_height=int(choose("preview_max_height", 768)),
            rotated_correction_enabled=_bool(choose("rotated_correction_enabled", None), True),
            rotated_correction_threshold=float(choose("rotated_correction_threshold", 0.01)),
            rotated_error_threshold=float(choose("rotated_error_threshold", 0.05)),
            allowed_dataset_roots=_paths(
                values.get("allowed_dataset_roots")
                if values.get("allowed_dataset_roots") is not None
                else _env("ALLOWED_DATASET_ROOTS")
            ),
            allowed_export_roots=_paths(
                values.get("allowed_export_roots")
                if values.get("allowed_export_roots") is not None
                else _env("ALLOWED_EXPORT_ROOTS")
            ),
            log_level=str(choose("log_level", "INFO")).upper(),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.preview_max_width <= 0 or self.preview_max_height <= 0:
            raise ValueError("preview dimensions must be positive")
        if not 0 <= self.rotated_correction_threshold < self.rotated_error_threshold:
            raise ValueError("rotated thresholds must satisfy 0 <= correction < error")
