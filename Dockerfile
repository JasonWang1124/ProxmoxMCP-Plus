FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md ./
COPY src ./src
COPY main.py ./

RUN uv venv && \
    . .venv/bin/activate && \
    uv pip install --no-cache -e .

ENV PROXMOX_MCP_CONFIG=/app/proxmox-config/config.json \
    PATH="/app/.venv/bin:$PATH"

EXPOSE 8812

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS -o /dev/null -X POST -H 'Content-Type: application/json' \
        -H 'Accept: application/json, text/event-stream' \
        -d '{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"healthcheck","version":"1.0"}}}' \
        http://127.0.0.1:8812/mcp || exit 1

CMD ["python", "main.py"]
