"""Tests for the MCP tool-specification validator."""

import importlib.util
from pathlib import Path


def _load_validator():
    path = Path(__file__).resolve().parents[2] / "scripts" / "validate_tool_specs.py"
    spec = importlib.util.spec_from_file_location("validate_tool_specs", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_server(path: Path, names: list[str]) -> None:
    decorated = "\n".join(f"    @mcp.tool\n    def {name}(): pass" for name in names)
    path.write_text(f"def create_server(mcp):\n{decorated}\n", encoding="utf-8")


def _write_spec(path: Path, validator, *, sections: tuple[str, ...] | None = None) -> None:
    headings = sections or validator.REQUIRED_SECTIONS
    path.write_text("# Tool\n\n" + "\n\n".join(headings) + "\n", encoding="utf-8")


def _valid_layout(tmp_path: Path, validator) -> tuple[Path, Path]:
    server = tmp_path / "server.py"
    specs = tmp_path / "tool-specs"
    specs.mkdir()
    _write_server(server, ["first_tool", "second_tool"])
    for name in ("first_tool", "second_tool"):
        _write_spec(specs / f"{name}.md", validator)
    for name in validator.SUPPORTING_FILES - {"index.md"}:
        (specs / name).write_text("# Supporting\n", encoding="utf-8")
    (specs / "index.md").write_text("[First](first_tool.md)\n[Second](second_tool.md)\n", encoding="utf-8")
    return server, specs


def test_validate_tool_specs_accepts_complete_layout(tmp_path: Path) -> None:
    validator = _load_validator()
    server, specs = _valid_layout(tmp_path, validator)

    assert validator.validate_tool_specs(server, specs) == []


def test_validate_tool_specs_reports_missing_specification_and_index_link(tmp_path: Path) -> None:
    validator = _load_validator()
    server, specs = _valid_layout(tmp_path, validator)
    (specs / "second_tool.md").unlink()
    (specs / "index.md").write_text("[First](first_tool.md)\n", encoding="utf-8")

    errors = validator.validate_tool_specs(server, specs)

    assert any("missing specification for MCP tool 'second_tool'" in error for error in errors)
    assert any("missing link to second_tool.md" in error for error in errors)


def test_validate_tool_specs_reports_a_broken_index_link_path(tmp_path: Path) -> None:
    validator = _load_validator()
    server, specs = _valid_layout(tmp_path, validator)
    (specs / "index.md").write_text(
        "[First](missing/first_tool.md)\n[Second](second_tool.md)\n",
        encoding="utf-8",
    )

    errors = validator.validate_tool_specs(server, specs)

    assert any("broken link: missing/first_tool.md" in error for error in errors)
    assert any("missing link to first_tool.md" in error for error in errors)


def test_validate_tool_specs_reports_unparseable_server_source(tmp_path: Path) -> None:
    validator = _load_validator()
    server, specs = _valid_layout(tmp_path, validator)
    server.write_text("def create_server(:\n", encoding="utf-8")

    errors = validator.validate_tool_specs(server, specs)

    assert any("unable to inspect MCP tool registrations" in error for error in errors)


def test_validate_tool_specs_reports_undecodable_server_source(tmp_path: Path) -> None:
    validator = _load_validator()
    server, specs = _valid_layout(tmp_path, validator)
    server.write_bytes(b"\xff")

    errors = validator.validate_tool_specs(server, specs)

    assert any("unable to inspect MCP tool registrations" in error for error in errors)


def test_validate_tool_specs_reports_unknown_specification_and_missing_section(tmp_path: Path) -> None:
    validator = _load_validator()
    server, specs = _valid_layout(tmp_path, validator)
    _write_spec(specs / "unknown_tool.md", validator)
    _write_spec(specs / "first_tool.md", validator, sections=validator.REQUIRED_SECTIONS[:-1])

    errors = validator.validate_tool_specs(server, specs)

    assert any("no registered MCP tool named 'unknown_tool'" in error for error in errors)
    assert any("first_tool.md: missing required section '## Acceptance criteria'" in error for error in errors)
