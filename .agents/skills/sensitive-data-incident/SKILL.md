---
name: sensitive-data-incident
description: >
  Contains a suspected repository sensitive-data exposure. Use when credentials,
  personal information, private paths, or other sensitive material appear in the
  working tree, staged content, commits, logs, issues, or pull requests. Do not use
  for ordinary code-quality findings without a suspected exposure.
---

# Sensitive-Data Incident

Do not paste the suspected value into chat, commits, logs, issues, pull requests, or
commands. Stop the affected delivery operation and report only the file, state, and
safe summary needed for the owner to decide recovery.

## Workflow

1. Determine whether the material is only in the working tree or staging area, in an
   unpushed commit, in a pushed feature branch, or on remote `main`. Do not commit,
   push, publish, or create a corrective commit while the exposure is unresolved.
2. Before a commit, stop and report the finding. Remove the material only with the
   user's direction; do not create a commit that preserves it in history.
3. For an unpushed commit, identify the last safe commit and preserve the working
   tree for investigation. Explain the proposed mixed reset and wait for explicit
   authorization before running it.
4. For a pushed feature branch, identify the last safe commit. Wait for explicit
   authorization before rewriting the branch with `--force-with-lease`, closing an
   exposed pull request, or taking any other destructive action. Wait for the
   owner's credential-rotation and platform-cleanup decisions.
5. For remote `main`, stop all commits, pushes, and releases. Report the last safe
   commit and wait for a human owner; do not rewrite shared history autonomously.

Done when: the exposure state and last safe commit are reported without disclosing
the value, and all destructive or external remediation actions have explicit owner
authorization.

## Gotchas

- A follow-up commit does not remove a sensitive value from prior Git history.
- `git reset`, force-push, pull-request closure, and credential rotation affect
  external state; never infer approval for them from a request to investigate.

## Maintenance

Update this Skill when sensitive-data policy, recovery expectations, reporting
channels, or Git hosting procedures change.
