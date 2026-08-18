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

## Project Methods

- Test-driven development: use the upstream
  [TDD skill](https://github.com/mattpocock/skills/tree/main/skills/engineering/tdd)
  for public-seam testing, vertical red-green slices, test design, and mocking
  guidance. The project-specific workflow and exceptions are defined in
  `quality.md`. Verified 2026-08-18.

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
