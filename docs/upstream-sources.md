# Upstream Sources

Use primary sources for behavior that can change over time.

| Topic | Preferred source | Revalidate when |
|---|---|---|
| FastMCP | project MCP `fastmcp-docs` at <https://gofastmcp.com/mcp> | changing APIs, upgrading FastMCP, or interpreting Client/ToolResult/STDIO behavior |
| MCP | <https://modelcontextprotocol.io/specification/> | changing protocol content or transport behavior |
| AutoTrain | <https://huggingface.co/docs/autotrain/object_detection> | changing export preflight or JSONL fields |
| Agent Skills | <https://agentskills.io/specification> | changing bundled Skill metadata or layout |
| uv | <https://docs.astral.sh/uv/> | changing lock, build, or environment behavior |

The FastMCP docs server is read-only except for its feedback tool. Search and retrieval are authorized for project work; submitting feedback is an external write and requires explicit user approval. If the server is unavailable, use the official FastMCP site and record the consulted page and date in the pull request.
