---
name: repository-delivery
description: >
  Delivers a focused repository change through GitHub Flow. Use when creating or
  reviewing a branch, commit, push, or draft pull request for this repository. Do
  not use for source-code implementation without a repository delivery action.
---

# Repository Delivery

Use this Skill only after the user authorizes the requested Git or GitHub action.
It guides delivery; it does not grant permission to commit, push, open a pull
request, or merge.

## Workflow

1. Inspect `git status`, the current branch, and the intended change. Preserve
   unrelated user changes. Use one focused branch for one issue; branch from the
   current `main` using a short `feat/`, `fix/`, `docs/`, or `chore/` name.
2. Prepare one atomic English Conventional Commit. Keep its title to 50 characters
   or fewer and omit scope unless it materially improves clarity. Stage only the
   intended change, then inspect the staged diff.
3. Before committing, review staged additions for credentials, personal
   information, private paths, and unrelated content. Run `just quality`, then
   `just hooks`. If either changes files, stage the intended result and repeat the
   complete sequence. Never bypass hooks with `--no-verify`.
4. Commit only after every required check passes and the user authorized the commit.
   If a scan finds or suggests sensitive content, stop without committing or pushing
   and use the `sensitive-data-incident` Skill.
5. Push only after the functional slice runs and the user authorized the push.
   Before opening a pull request, read `.github/pull_request_template.md` and use
   its complete section structure for the English PR body. Replace every
   instruction comment and placeholder with facts from the change; retain unchecked
   items for checks not run and explain why. Fill `Closes #<issue-number>` only when
   the linked issue is confirmed. Create the PR with the completed template body
   explicitly, not a freeform summary or an automatic-fill option. Re-read the
   created PR body and correct it if a template section, applicable checklist item,
   or safety statement is absent. Mark it ready only after tests, documentation,
   and required CI pass. Wait for human review and never merge.

Done when: the authorized delivery action is complete, all required checks passed,
and no unrelated or sensitive content was included.

## Gotchas

- A successful local test run does not authorize an external Git action.
- A hook may modify tracked files. Do not commit its result until the staged diff has
  been inspected again.
- GitHub CLI automatic-fill options do not replace the repository PR template.

## Maintenance

Update this Skill when Git branching, commit-message, validation, approval, pull
request, or merge requirements change.
