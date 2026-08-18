# syntax=docker/dockerfile:1

FROM python:3.12-slim-bookworm AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /build

COPY LICENSE README.md pyproject.toml ./
COPY src ./src

RUN python -m venv /opt/detection-mcp \
    && /opt/detection-mcp/bin/pip install .

FROM python:3.12-slim-bookworm AS runtime

ENV PATH="/opt/detection-mcp/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    DETECTION_MCP_DB_PATH=/state/annotations.db \
    DETECTION_MCP_ALLOWED_DATASET_ROOTS=/datasets \
    DETECTION_MCP_ALLOWED_EXPORT_ROOTS=/exports

RUN groupadd --system detection-mcp \
    && useradd --system --gid detection-mcp --home-dir /nonexistent --shell /usr/sbin/nologin detection-mcp \
    && mkdir --parents /state /exports \
    && chown detection-mcp:detection-mcp /state /exports

COPY --from=builder /opt/detection-mcp /opt/detection-mcp

USER detection-mcp
ENTRYPOINT ["detection-mcp"]
