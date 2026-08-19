# detection-mcp

Build and maintain a local FastMCP server for object-detection dataset annotation.
The server owns annotation state but treats every source image as immutable.

## Project Map

```text
src/detection_mcp/    Python package and MCP server
tests/                Unit, integration, packaging, and container tests
skills/               Installable Agent Skills published from the repository
.agents/knowledge/    Agent-facing project knowledge
scripts/              Repository validation commands
```

## Core Conventions

- Use Python 3.12 or newer and type all public and domain interfaces.
- Keep MCP adapters thin: tools call services, services enforce domain rules, and
  repositories own SQLite statements.
- Write code, comments, agent-facing files, commits, issues, and pull requests in
  English. Keep `README.md` and `README.zh-CN.md` synchronized.
- Develop product behavior changes in `src/detection_mcp` test-first and follow the
  comment and docstring rules in `.agents/knowledge/quality.md`. Harness scripts,
  hooks, CI, and repository metadata require relevant validation, not TDD.
- Never modify, move, rename, or delete dataset images. Resolve and validate paths
  before opening them, including symlink targets.
- Write protocol output only to stdout. Send logs and diagnostics to stderr.
- Make the smallest change that satisfies the active issue. Do not refactor
  unrelated code.

## When To Read What

| Situation | Read |
|---|---|
| Scoping work or checking v1 boundaries | `.agents/knowledge/goals.md` |
| Changing modules, dependencies, storage, or data flow | `.agents/knowledge/architecture.md` |
| Changing behavior, implementation, tests, validation, hooks, or CI | `.agents/knowledge/quality.md` |
| Using or upgrading FastMCP, MCP, AutoTrain, or Agent Skills | `.agents/knowledge/references.md` |
| Adding, changing, or reviewing an MCP tool | `.agents/knowledge/tool-specs/index.md` and the matching tool specification |
| Changing detailed product behavior | `.agents/knowledge/goals.md`, affected contract tests, and the relevant architecture or quality knowledge |

The project registers the `fastmcp-docs` documentation server in `.mcp.json`.
Use it first for FastMCP API and behavior questions. Its feedback tool changes
external state; do not call that tool without explicit user approval.

`.agents/knowledge/` is the only project knowledge base. Executable tests define
current behavior; update this knowledge when confirmed behavior changes.

## Development Environment

- Run `uv sync --locked --all-groups` after cloning or changing environments.
- Install every configured hook with
  `uv run pre-commit install --install-hooks --hook-type pre-commit --hook-type commit-msg --hook-type pre-push`.
- Treat the workspace as public. Do not place credentials, private data, real user
  datasets, or identifying filesystem paths in tracked files, tests, logs, issues,
  or pull requests.

## Validation

| Check | Command |
|---|---|
| Format | `uv run ruff format --check .` |
| Lint | `uv run ruff check .` |
| Types | `uv run ty check` |
| Tests | `uv run pytest` |
| Tool specifications | `uv run python scripts/validate_tool_specs.py` |
| CI quality controls | `just quality-control` |
| Complete local gate | `uv run python scripts/quality.py` |
| Repository hooks | `uv run pre-commit run --all-files --show-diff-on-failure` |

Prefer the equivalent `just` recipes for routine work (`just test`,
`just quality`, and `just check`). Keep each recipe as a thin wrapper around the
canonical script or tool command so CI and local execution share behavior.

## Keep In Sync

| When this changes | Update in the same change |
|---|---|
| Tool name, schema, or behavior | Tool-spec index and matching specification, product Skills, and contract tests |
| File under `skills/` | Skill validation and README installation instructions |
| CLI or environment setting | Both READMEs, configuration docs, and container examples |
| Architecture or module boundary | Architecture knowledge and affected tests |
| Quality command or hook | Quality knowledge, CI, and contribution guide |
| External dependency behavior | Reference index with source and verification date |
