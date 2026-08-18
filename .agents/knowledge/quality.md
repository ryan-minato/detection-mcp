# Quality Gates

Read this file when changing behavior, implementation, tests, validation scripts,
hooks, CI, dependencies, or release checks.

## Test-Driven Development

Use test-driven development for features, bug fixes, and behavior changes. Work
through one vertical slice at a time instead of writing all tests or all
implementation in separate batches:

1. **Define the seam.** Identify the public interface where callers observe the
   behavior and state the behavior in caller-facing language. Use an existing
   approved interface when possible; ask the user only when the interface or seam
   is materially ambiguous.
2. **Red.** Add one focused test for that observable behavior. Run the narrowest
   relevant test command and confirm it fails for the expected missing behavior,
   not because of a syntax, fixture, or environment error.
3. **Green.** Add only the production code needed to pass that test. Run the
   focused test, then the related test group. Do not anticipate later slices or
   add speculative behavior.
4. **Review and refactor.** Refactor only after the slice is green. Preserve the
   tested behavior, improve comments and names where needed, and rerun the
   affected tests after every refactor.
5. Repeat the cycle for the next behavior, then run the complete quality gate.

For bug fixes, the red test must reproduce the reported defect before the fix is
implemented. For behavior-preserving refactors, first establish a green baseline;
add a characterization test when the behavior is not already protected.

Documentation-only, comment-only, and non-behavioral metadata changes do not need
a deliberately failing test, but they still require the relevant validation.
Exploratory code may be used to learn, but discard it before implementation and
restart from a failing test.

Record the tested seam, the expected red failure, and the commands that produced
the final green result in the work handoff or pull request. Never weaken, delete,
or skip a valid test merely to make the implementation green.

### Test Design

- Test behavior through public interfaces. Do not test private methods, assert
  internal call order, or inspect storage through a side channel when the public
  interface can demonstrate the result.
- Name tests as caller-visible specifications and use expected values from the
  requirements, a worked example, or another independent source of truth. Do not
  recompute the expected value with the same algorithm as the implementation.
- Keep each test focused on one logical behavior. Multiple assertions are
  acceptable when they describe one observable outcome.
- Prefer real project collaborators, temporary directories, and temporary SQLite
  databases. Mock only true system boundaries such as external services, time,
  randomness, or an unavoidable filesystem boundary; do not mock the project's
  own modules to verify their interactions.

## Code Comments and Docstrings

- Module-internal objects need at most a concise one-line comment or docstring
  stating their purpose when that purpose is not already clear from the name.
- Interfaces used by other modules must have docstrings that describe their
  purpose, parameters, return value, relevant notes or invariants, and raised
  errors. Include only applicable sections, but do not omit behavior callers need
  to use the interface safely.
- For long code blocks, add comments at logical phase boundaries to explain intent,
  invariants, or non-obvious constraints. Do not narrate individual statements.
- Keep comments synchronized with behavior. Remove stale, redundant, or misleading
  comments in the same change that makes them inaccurate.

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

CI separates inexpensive quality controls from tests:

- `quality.yml` runs `just quality-control` for every pushed commit on every
  branch. Pull requests from forks receive the same check through the pull request
  event.
- `tests.yml` runs only for pull requests and pushes to the default branch. Pull
  request runs use the head SHA and cancel older in-progress runs for the same PR,
  so expensive tests run only for its latest commit.
- Test CI covers supported Python versions, a clean wheel install, and the runtime
  container smoke test. Security CI scans repository history separately.

## Test Shape

- Unit tests isolate geometry, path, state, and export rules.
- Transaction tests prove all-or-nothing batch behavior.
- MCP contract tests fix tool names and input/output schemas.
- Packaging tests use built artifacts, not an editable checkout.
- Docker tests prove the dataset mount remains read-only and state survives a new
  container.

The project-wide branch coverage floor is 90 percent. Explicit high-risk scenarios
remain required even when coverage already exceeds the floor.
