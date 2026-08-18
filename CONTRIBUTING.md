# Contributing

Use Python 3.12 or newer. Install `uv` and `just`, then synchronize the locked
development environment with `just sync`.

Create one branch for one GitHub issue. Keep commits atomic and use English
Conventional Commit messages. Push a runnable functional slice and open a draft
pull request; mark it ready only after its tests, documentation, and required CI
pass.

Before every commit, inspect the staged diff for unrelated changes and sensitive
information, then run:

1. `just quality`
2. `just hooks`

Never bypass Git hooks. If a check changes a file, stage the result and repeat the
complete sequence. See `.agents/knowledge/workflow.md` for the sensitive-data
incident procedure.
