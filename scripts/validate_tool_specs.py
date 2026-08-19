"""Validate MCP tool-specification coverage and required document structure."""

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = ROOT / "src" / "detection_mcp" / "server.py"
SPECS_ROOT = ROOT / ".agents" / "knowledge" / "tool-specs"
REQUIRED_SECTIONS = (
    "## Purpose",
    "## Interface",
    "## Preconditions",
    "## Behavior and invariants",
    "## Output",
    "## Business errors",
    "## Example",
    "## Acceptance criteria",
)
SUPPORTING_FILES = {"index.md", "common-contract.md", "template.md"}
LINK_PATTERN = re.compile(r"\[[^]]+\]\(([^)#]+)(?:#[^)]+)?\)")


def registered_tool_names(server_path: Path) -> set[str]:
    """Return names of functions registered with the FastMCP tool decorator."""
    tree = ast.parse(server_path.read_text(encoding="utf-8"), filename=str(server_path))
    tools: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            call = decorator if isinstance(decorator, ast.Call) else None
            target = call.func if call is not None else decorator
            if isinstance(target, ast.Attribute) and target.attr == "tool":
                tools.add(node.name)
    return tools


def linked_files(index_path: Path) -> set[str]:
    """Return local Markdown filenames linked from a tool-specification index."""
    links = LINK_PATTERN.findall(index_path.read_text(encoding="utf-8"))
    return {Path(link).name for link in links if link.endswith(".md")}


def validate_tool_specs(server_path: Path, specs_root: Path) -> list[str]:
    """Return coverage, index, and section errors for the tool specifications."""
    errors: list[str] = []
    if not server_path.is_file():
        return [f"{server_path}: MCP server source is missing"]
    if not specs_root.is_dir():
        return [f"{specs_root}: tool-specification directory is missing"]

    expected = registered_tool_names(server_path)
    documented = {path.stem for path in specs_root.glob("*.md") if path.name not in SUPPORTING_FILES}
    for name in sorted(expected - documented):
        errors.append(f"{specs_root}: missing specification for MCP tool '{name}'")
    for name in sorted(documented - expected):
        errors.append(f"{specs_root / f'{name}.md'}: no registered MCP tool named '{name}'")

    index_path = specs_root / "index.md"
    if not index_path.is_file():
        errors.append(f"{index_path}: missing tool-specification index")
    else:
        indexed = linked_files(index_path)
        for name in sorted(expected):
            filename = f"{name}.md"
            if filename not in indexed:
                errors.append(f"{index_path}: missing link to {filename}")
            elif not (specs_root / filename).is_file():
                errors.append(f"{index_path}: broken link to {filename}")

    for name in sorted(documented):
        path = specs_root / f"{name}.md"
        text = path.read_text(encoding="utf-8")
        for section in REQUIRED_SECTIONS:
            if section not in text:
                errors.append(f"{path}: missing required section '{section}'")
    for filename in ("common-contract.md", "template.md"):
        if not (specs_root / filename).is_file():
            errors.append(f"{specs_root / filename}: missing supporting specification document")
    return errors


def main() -> int:
    """Print validation failures and return a conventional process status."""
    errors = validate_tool_specs(SERVER_PATH, SPECS_ROOT)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Validated {len(registered_tool_names(SERVER_PATH))} MCP tool specifications.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
