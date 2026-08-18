# GitHub And Repository Workflow

Read this file before creating or changing branches, commits, issues, pull
requests, releases, or repository settings.

## GitHub Flow

- Track v1 work in a `v1.0` milestone with one issue per functional slice.
- Branch from current `main` with a short `feat/`, `fix/`, `docs/`, or `chore/`
  name. Do not commit feature work directly to `main`.
- Push when the functional slice runs and open an English draft pull request.
- Mark the pull request ready only when its acceptance tests, documentation, and
  required CI pass. Agents wait for human review and never merge.
- Prefer rebase merge so reviewed atomic commits remain linear.

## Commits

Use English Conventional Commits with a title no longer than 50 characters. Omit
scope unless it improves an established naming pattern. One commit contains one
logical change.

Before every commit:

1. Inspect `git status`, the staged diff, and its atomicity.
2. Review added lines for secrets, credentials, personal information, and private
   paths.
3. Run the complete quality gate and all repository hooks.
4. Fix failures and rerun from the start. Never use `--no-verify`.

## Sensitive-Data Incident

- Before commit: stop and report the finding. Do not commit or push it.
- In an unpushed commit: immediately move the branch back to the last safe commit
  with a mixed reset, preserve the working tree for investigation, and wait for the
  user. Do not create a corrective commit.
- In a pushed feature branch: reset to the safe commit, rewrite the remote with
  `--force-with-lease`, close the exposed pull request, and wait for credential
  rotation and platform cleanup decisions.
- In remote `main`: stop all commits, pushes, and releases; report the last safe
  commit and wait for the user. Do not rewrite the shared branch autonomously.

Never paste the leaked value into an issue, pull request, commit message, log, or
chat response.
