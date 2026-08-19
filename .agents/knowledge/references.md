# Upstream References

Read this file when an implementation depends on FastMCP, MCP, AutoTrain, Agent
Skills, packaging, or devcontainer behavior that may have changed.

## Preferred Sources

| Topic | Source | Use |
|---|---|---|
| FastMCP | <https://gofastmcp.com/mcp> | Preferred documentation MCP for API, examples, and compatibility questions |
| MCP | <https://modelcontextprotocol.io/specification/> | Protocol behavior and content schemas |
| AutoTrain object detection | <https://huggingface.co/docs/autotrain/object_detection> | Export preflight and metadata format |
| Agent Skills | <https://agentskills.io/specification> | Skill layout and frontmatter |
| uv build backend | <https://docs.astral.sh/uv/configuration/build-backend/> | Package and data-file inclusion |
| Dev Containers | <https://containers.dev/implementors/json_reference/> | Development container properties |
| GitHub container publishing | <https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images> | GHCR authentication, permissions, and image publication; verified 2026-08-18 |
| GitHub OIDC | <https://docs.github.com/en/actions/concepts/security/openid-connect> | Short-lived deployment identity and job permissions; verified 2026-08-19 |
| GitHub environments | <https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments> | Deployment approvals and tag restrictions; verified 2026-08-19 |
| PyPI Trusted Publishers | <https://docs.pypi.org/trusted-publishers/using-a-publisher/> | OIDC permissions and isolated publish jobs; verified 2026-08-19 |
| PyPI pending publishers | <https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/> | First release of a new project through OIDC; verified 2026-08-19 |
| PyPI publish Action | <https://github.com/pypa/gh-action-pypi-publish> | Trusted publishing Action behavior; verified 2026-08-19 |
| Docker image metadata | <https://github.com/docker/metadata-action> | PEP 440 image tags and stable `latest` generation; verified 2026-08-19 |

Revalidate an upstream source before changing the behavior it governs. Prefer the
project FastMCP documentation server for FastMCP questions; it is read-only except
for feedback submission, which requires explicit approval.

## Project Methods

- Test-driven development: use the upstream
  [TDD skill](https://github.com/mattpocock/skills/tree/main/skills/engineering/tdd)
  for public-seam testing, vertical red-green slices, test design, and mocking
  guidance. The project-specific workflow and exceptions are defined in
  `quality.md`. Verified 2026-08-18.

## Release Automation

Read this section only when changing repository release workflows or their
permissions.

- `.github/workflows/release.yml` runs only when a GitHub Release is published. The
  tag must equal `v<project version>`. Main-branch pushes do not publish packages.
- The workflow builds wheel, source distribution, and container artifacts once. It
  installs and starts both Python distributions and tests the exact saved container
  image before either publish job runs.
- PyPI publishing uses the protected `pypi` environment and job-scoped
  `id-token: write`; it has no stored publishing credential. The pending publisher
  must name `release.yml` and the `pypi` environment exactly.
- Container publishing uses the repository `GITHUB_TOKEN` with only `contents: read`
  and `packages: write`. PEP 440 releases receive an exact version tag; only stable
  releases also receive `latest`. Third-party Actions remain pinned to full commit
  SHAs.

The project-level `.mcp.json` registers the preferred FastMCP source as
`fastmcp-docs`. Restart the agent session after changing that file so the host can
rediscover the server.

Use the FastMCP documentation MCP before general web search. Treat it as read-only:
search and retrieve public documentation, but do not submit feedback or perform any
write action without explicit user approval. If it is unavailable, use the official
FastMCP site and record the page and verification date in the pull request.

Do not copy upstream documentation into this repository. Record only project
decisions that depend on it, together with the source and the condition that should
trigger revalidation.
