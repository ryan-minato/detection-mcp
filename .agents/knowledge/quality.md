# Quality Gates

Read this file when changing tests, validation scripts, hooks, CI, dependencies,
or release checks.

## Local Commit Gate

Run `just quality` before every commit. It invokes `scripts/quality.py`, which must perform, in
order:

1. Ruff formatting check and linting.
2. ty type checking over `src` and `tests`.
3. Unit and non-container integration tests with branch coverage.
4. Agent Skill structure and link validation.
5. Wheel and source distribution build verification.

Run `just hooks` after staging so
repository hygiene and sensitive-data hooks see the exact candidate content.
Failures block the commit; fix the cause and rerun the complete gate.

## Pull Request Gate

Required CI repeats the local gate, tests supported Python versions, installs the
built wheel in a clean environment, exercises a real STDIO client, and runs Docker
mount and persistence scenarios. Security jobs scan repository history in addition
to the staged-content checks used locally.

## Test Shape

- Unit tests isolate geometry, path, state, and export rules.
- Transaction tests prove all-or-nothing batch behavior.
- MCP contract tests fix tool names and input/output schemas.
- Packaging tests use built artifacts, not an editable checkout.
- Docker tests prove the dataset mount remains read-only and state survives a new
  container.

The project-wide branch coverage floor is 90 percent. Explicit high-risk scenarios
remain required even when coverage already exceeds the floor.
