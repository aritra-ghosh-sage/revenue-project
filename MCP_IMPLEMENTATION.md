# MCP Server Implementation (summary)

Short summary of MCP implementation and how to run the servers locally.

Contents:

- `mcp_servers/api_usage_mcp.py` — MCP server exposing usage query tools and `generate_bill`
- `mcp_servers/allocation_usage_mcp.py` — Allocation MCP server (single allocation tool)
- `api/metrics.py`, `api/allocation_metrics.py`, `api/models.py` — FastAPI backends and in-memory models
- Test and verification scripts at repository root and `verification/`

Running the services:

1. Activate virtual environment and install deps (`uv sync` if using `uv`)
2. Start FastAPI servers:

```powershell
uvicorn api.metrics:app --reload
uvicorn api.allocation_metrics:app --port 8001 --reload
```

3. Start MCP servers (separate terminals):

```powershell
python -m mcp_servers.api_usage_mcp
python -m mcp_servers.allocation_usage_mcp
```

4. Run tests/verification:

```powershell
uv run python test_all_mcp_flows.py
uv run python test_bill_generation_mcp.py
pytest
```

Notes:

- MCP tools use `httpx.AsyncClient()` to call the FastAPI backends on localhost.
- The `generate_bill` tool posts to `/generate-bill` and expects valid bill records (see `mcp_servers/api_usage_mcp.py`).
- Use the `verification/` runner to validate generated PDFs and compare key fields.

Updated: 2026-03-11
