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
complete sequence. Stop and report suspected sensitive information before committing
or pushing it.

## Releases

Before the first release, create a protected GitHub environment named `pypi`. Limit
deployment to `v*` tags, require approval from `ryan-minato`, allow self-review for
the single-maintainer repository, and disable administrator bypass. Register a PyPI
pending Trusted Publisher with these values:

- PyPI project: `detection-mcp`
- GitHub owner: `ryan-minato`
- Repository: `detection-mcp`
- Workflow: `release.yml`
- Environment: `pypi`

For each release, update the project version and `uv.lock`, merge the change, and
publish a GitHub Release with the matching `v<version>` tag. Mark prereleases in
GitHub when the Python version is a prerelease. The Release workflow builds and
tests the wheel, source distribution, and container image before any upload. Approve
the `pypi` deployment after those checks pass.
