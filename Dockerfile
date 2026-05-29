# ── Build stage ──────────────────────────────────────────────────────────────
FROM dhi.io/python:3.13-dev AS builder

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml README.md ./
COPY src/ ./src/

# --no-editable: installs the package into .venv instead of linking back to src/,
# so only .venv needs to be copied to the runtime stage.
RUN uv sync --no-dev --no-editable


# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM dhi.io/python:3.13

WORKDIR /app

# Only .venv is needed; source is already bundled by --no-editable above.
COPY --from=builder /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"
# Override with DOCS_MCP_PROVIDER=local to use a local embedding model instead.
ENV DOCS_MCP_PROVIDER=openai

EXPOSE 8000

# config.yaml must be volume-mounted at /app/config.yaml at runtime.
# e.g. docker run -v ./config.yaml:/app/config.yaml -e OPENAI_API_KEY=sk-... <image>
ENTRYPOINT ["/app/.venv/bin/docs-mcp", "--config", "/app/config.yaml"]
