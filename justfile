set dotenv-load := false

default:
    @just --list

# Synchronize the locked development environment.
sync:
    uv sync --locked --all-groups

# Apply Python formatting.
format:
    uv run ruff format .

# Verify formatting without changing files.
format-check:
    uv run ruff format --check .

# Run static lint rules.
lint:
    uv run ruff check .

# Run the type checker.
typecheck:
    uv run ty check

# Run the ordinary test suite.
test *args:
    uv run pytest {{args}}

# Run tests with the project coverage threshold.
test-cov:
    uv run pytest --cov=detection_mcp --cov-branch --cov-report=term-missing --cov-fail-under=90

# Validate every repository Agent Skill.
skills:
    uv run python scripts/validate_skills.py

# Validate MCP tool-specification coverage and structure.
tool-specs:
    uv run python scripts/validate_tool_specs.py

# Build and inspect wheel and source distributions.
build:
    uv run python scripts/verify_build.py

# Scan tracked and staged content for secrets and personal information.
sensitive *args:
    uv run python scripts/check_sensitive.py {{args}}

# Run the complete pre-commit quality gate.
quality:
    uv run python scripts/quality.py

# Run CI quality controls without the test suite.
quality-control: format-check lint typecheck skills tool-specs build sensitive

# Run all repository hooks against tracked files.
hooks:
    uv run pre-commit run --all-files --show-diff-on-failure

# Run every local validation layer.
check: quality hooks

# Build the production container image.
docker-build:
    docker build --tag detection-mcp:local .

# Run tests that require a container runtime.
docker-test:
    uv run pytest -m docker --run-docker

# Smoke-test an already built container image.
docker-smoke image="detection-mcp:local":
    docker run --rm {{image}} --version
